"""
app/services/scoring.py
=======================
Moteur de scoring LBC/FT — RiskGuard (IMF béninoises)
Calcule un score de risque 0-100 selon 6 critères pondérés (C1..C6).

Compatibilité seed_db.py (Marcos) :
  - ScoringCriteria.weight  : valeur entière (20, 25…) → divisée par la somme totale
  - RiskThreshold           : champs score_min / score_max
  - RiskZone.risk_level     : 'FAIBLE' | 'MOYEN' | 'ELEVE' | 'TRES_ELEVE'

Auteur  : Dev A — AFFOKPE Magloire
Version : 1.3 — Mai 2026

Changelog v1.3 :
  [Fix 7] _score_c5        : ancienne PEP (active=False) → note 50 au lieu de 0
                             (recommandation GAFI R.12 — vigilance 5 ans post-mandat)
  [Fix 8] _score_c3        : card testing — détection micro-transactions carte répétées
                             (comportemental uniquement ; validité technique gérée ailleurs)
  [Fix 9] _score_c3        : near-threshold smurfing — montants entre 80 % et 100 %
                             du seuil FATF (495 000, 498 000 XOF…) ajoutés aux suspects
  [Fix 10] _detect_duplicates : nouvelle méthode — transactions identiques (même montant
                             arrondi + même destination) dans une fenêtre de 24 h
  [Fix 11] calculate_score : result dict étendu avec smurfing_detected, card_testing_count
                             et c5_score pour que le router puisse créer les alertes fines
                             sans re-interroger la base

Changelog v1.2 (inchangé) :
  [Fix 1] _load_weights      : suppression du filtre is_active (champ inexistant)
  [Fix 2] _get_category      : normalisation 'ELEVE' → 'ÉLEVÉ' (contrat API)
  [Fix 3] _detect_smurfing   : anti faux-positifs — concentration temporelle +
                               ratio revenus (reçoit transactions + revenus)
  [Fix 4] datetime.utcnow()  : remplacé par datetime.now(timezone.utc)
  [Fix 5] Sécurités null     : or [] sur accounts et documents partout
  [Fix 6] Timezone naive     : Transaction.date_op est un Column(DateTime) sans
                               timezone en base — le cutoff est désormais strippé
                               (.replace(tzinfo=None)) avant la requête SQL pour
                               éviter la DataError PostgreSQL (aware vs naive).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy.orm import Session

from app.models.countries import Country
from app.models.customer_docs import CustomerDoc
from app.models.customers import Customer
from app.models.pep_list import PepEntry
from app.models.risk_thresholds import RiskThreshold
from app.models.risk_zones import RiskZone
from app.models.scoring_criteria import ScoringCriteria
from app.models.transactions import Transaction

logger = logging.getLogger(__name__)

# ── Fallback si les tables de référence sont vides ────────────────────────
_DEFAULT_WEIGHTS: dict[str, float] = {
    "C1": 0.20,
    "C2": 0.20,
    "C3": 0.25,
    "C4": 0.10,
    "C5": 0.15,
    "C6": 0.10,
}

_DEFAULT_THRESHOLDS = [
    {"category": "FAIBLE", "min_score": 0, "max_score": 33},
    {"category": "MOYEN", "min_score": 34, "max_score": 66},
    {"category": "ÉLEVÉ", "min_score": 67, "max_score": 100},
]

# ── Paramètres C3 ─────────────────────────────────────────────────────────
_TX_WINDOW_DAYS = 90  # fenêtre d'analyse des transactions

# Smurfing — détection du fractionnement
_SMURFING_THRESHOLD = 500_000  # XOF : seuil déclaratif FATF
_SMURFING_ROUND_STEP = 10_000  # montants suspects : multiples de 10k
_SMURFING_MIN_COUNT = 3  # nb minimum de tx suspects pour déclencher
_SMURFING_WINDOW_DAYS = 7  # fenêtre de concentration temporelle [Fix 3]
_SMURFING_REVENUE_MULT = 3.0  # ratio min total_suspect / revenu_mensuel [Fix 3]
_SMURFING_NEAR_LOW_PCT = 0.80  # borne basse near-threshold : 80 % du seuil [Fix 9]

# Card testing — micro-transactions carte [Fix 8]
_CARD_TESTING_MAX_AMOUNT = 1_000  # XOF : seuil micro-transaction
_CARD_TESTING_ALERT_COUNT = 5  # nb min pour alerte forte
_CARD_TESTING_WARN_COUNT = 2  # nb min pour alerte modérée

# Transactions dupliquées [Fix 10]
_DUPLICATE_WINDOW_SECONDS = 86_400  # 24 h
_DUPLICATE_ROUND_TO = -2  # arrondir à la centaine pour tolérer les frais


def _naive_utc_now() -> datetime:
    """
    Retourne l'heure UTC actuelle en datetime NAÏF (sans tzinfo).

    Transaction.date_op est un Column(DateTime) sans timezone en base PostgreSQL.
    Comparer un datetime aware avec une colonne naive provoque une DataError.
    On strip systématiquement tzinfo avant toute requête SQL.  [Fix 6]
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _strip_tz(d: datetime | None) -> datetime | None:
    """Normalise un datetime en naive UTC (cohérence [Fix 6])."""
    if d is not None and hasattr(d, "tzinfo") and d.tzinfo is not None:
        return d.replace(tzinfo=None)
    return d


# ═══════════════════════════════════════════════════════════════════════════
class ScoringEngine:
    """
    Calcule le score LBC/FT d'un client selon la grille du CDC (pages 6-7).

    Utilisation ::

        engine = ScoringEngine(db_session)
        result = engine.calculate_score(customer_id)

    Résultat conforme au contrat API v1.0 (champs supplémentaires non-breaking) ::

        {
            "global_score"       : int,    # 0-100
            "risk_category"      : str,    # 'FAIBLE' | 'MOYEN' | 'ÉLEVÉ'
            "detail_json"        : {
                "C1": float,               # contribution absolue = note_brute × poids
                "C2": float,
                "C3": float,
                "C4": float,
                "C5": float,
                "C6": float,
            },
            # Champs étendus v1.3 — utilisés par le router pour les alertes fines
            "c5_score"           : float,  # 0 | 50 | 100
            "smurfing_detected"  : bool,
            "card_testing_count" : int,    # nb de micro-tx carte détectées
        }
    """

    def __init__(self, db_session: Session) -> None:
        self.db = db_session
        self._weights: dict[str, float] = {}
        self._thresholds: list[dict[str, Any]] = []
        # Flags internes réinitialisés à chaque appel de calculate_score [Fix 11]
        self._smurfing_detected: bool = False
        self._card_testing_count: int = 0

    # ──────────────────────────────────────────────────────────────────────
    # Point d'entrée public
    # ──────────────────────────────────────────────────────────────────────

    def calculate_score(self, customer_id: UUID) -> dict[str, Any]:
        """
        Calcule et retourne le score LBC/FT pour le client donné.

        :param customer_id: UUID du client (table customers).
        :returns: dict avec global_score, risk_category, detail_json, et
                  champs étendus (c5_score, smurfing_detected, card_testing_count).
        :raises ValueError: si le client est introuvable en base.
        """
        logger.info("Début calcul score — client %s", customer_id)

        # Réinitialisation des flags internes [Fix 11]
        self._smurfing_detected = False
        self._card_testing_count = 0

        self._load_weights()
        self._load_thresholds()

        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise ValueError(f"Client introuvable : {customer_id}")

        notes: dict[str, float] = {
            "C1": self._score_c1(customer),
            "C2": self._score_c2(customer),
            "C3": self._score_c3(customer),
            "C4": self._score_c4(customer),
            "C5": self._score_c5(customer),
            "C6": self._score_c6(customer),
        }

        logger.debug("Notes brutes — client %s : %s", customer_id, notes)

        # Contributions absolues : note_brute × poids → leur somme = global_score
        detail_json: dict[str, float] = {
            code: round(
                notes[code] * self._weights.get(code, _DEFAULT_WEIGHTS[code]), 4
            )
            for code in ("C1", "C2", "C3", "C4", "C5", "C6")
        }

        global_score = min(100, max(0, round(sum(detail_json.values()))))
        risk_category = self._get_category(global_score)

        logger.info(
            "Score calculé — client %s : %s (%s)",
            customer_id,
            global_score,
            risk_category,
        )

        return {
            "global_score": global_score,
            "risk_category": risk_category,
            "detail_json": detail_json,
            # Champs étendus — non-breaking vis-à-vis du schéma API existant [Fix 11]
            "c5_score": notes["C5"],
            "smurfing_detected": self._smurfing_detected,
            "card_testing_count": self._card_testing_count,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Chargement dynamique des paramètres de scoring
    # ──────────────────────────────────────────────────────────────────────

    def _load_weights(self) -> None:
        """
        Charge les poids depuis la table scoring_criteria (sans filtre is_active —
        le champ n'existe pas dans le schéma réel de Marcos).  [Fix 1]

        Le champ weight est stocké en pourcentage entier (20, 25, 10…).
        On normalise par la somme totale pour obtenir des fractions décimales
        robustes même si un critère est ajouté ou modifié en base.
        """
        rows = self.db.query(
            ScoringCriteria
        ).all()  # [Fix 1] : plus de filtre is_active

        if rows:
            raw = {r.code: float(r.weight) for r in rows}
            total = sum(raw.values())
            if total > 0:
                self._weights = {k: v / total for k, v in raw.items()}
            else:
                logger.warning("Somme des poids = 0 — poids par défaut utilisés")
                self._weights = dict(_DEFAULT_WEIGHTS)
        else:
            logger.warning("Table scoring_criteria vide — poids par défaut utilisés")
            self._weights = dict(_DEFAULT_WEIGHTS)

    def _load_thresholds(self) -> None:
        """
        Charge les seuils de catégorie depuis risk_thresholds.
        Colonnes : score_min / score_max (schéma Marcos — seed_db.py).
        """
        rows = self.db.query(RiskThreshold).order_by(RiskThreshold.score_min).all()
        if rows:
            self._thresholds = [
                {
                    "category": r.category,
                    "min_score": r.score_min,
                    "max_score": r.score_max,
                }
                for r in rows
            ]
        else:
            logger.warning("Table risk_thresholds vide — seuils par défaut utilisés")
            self._thresholds = list(_DEFAULT_THRESHOLDS)

    # ──────────────────────────────────────────────────────────────────────
    # C1 — Profil professionnel (poids 20 %)
    # ──────────────────────────────────────────────────────────────────────

    def _score_c1(self, customer: Customer) -> float:
        """
        Note brute C1 selon le niveau de risque professionnel déclaré.

        Grille CDC :
          0-20  → Salarié formel secteur public / privé réglementé
          21-50 → Commerçant informel déclaré, artisan
          51-80 → Activité à risque élevé (changeur, transporteur, casino)
          81-100 → Activité non identifiable ou incohérente avec revenus
        """
        risk = (customer.profession_risk or "").upper()

        note = {
            "LOW": 10.0,
            "MEDIUM": 35.0,
            "HIGH": 65.0,
        }.get(
            risk, 85.0
        )  # absent / non renseigné → activité non identifiable

        # Incohérence revenus déclarés / niveau de risque
        rev = float(customer.revenus_declares or 0)
        if rev == 0 and risk not in ("HIGH", ""):
            note = min(100.0, note + 10.0)
        elif rev > 5_000_000 and risk == "LOW":
            note = min(100.0, note + 15.0)

        logger.debug("C1=%.1f (profession_risk=%s)", note, risk)
        return round(note, 2)

    # ──────────────────────────────────────────────────────────────────────
    # C2 — Zone géographique (poids 20 %)
    # ──────────────────────────────────────────────────────────────────────

    def _score_c2(self, customer: Customer) -> float:
        """
        Note brute C2 selon la zone géographique du client.

        Grille CDC :
          0-20  → Zone urbaine stable, loin des frontières
          21-50 → Zone semi-urbaine ou périphérique
          51-80 → Zone frontalière (Nigéria, Togo, Burkina) ou classée FATF
          81-100 → Zone de conflit actif ou sans infrastructure bancaire

        risk_level en base (seed Marcos) : 'FAIBLE' | 'MOYEN' | 'ELEVE' | 'TRES_ELEVE'
        """
        note = 50.0  # zone inconnue → prudence intermédiaire

        zone = self._get_zone(customer)
        if zone:
            level = (zone.risk_level or "").upper()
            note = {
                "FAIBLE": 10.0,
                "MOYEN": 35.0,
                "ELEVE": 65.0,
                "TRES_ELEVE": 88.0,
            }.get(level, 50.0)

        # Surcharge selon les attributs du pays
        country = self._get_country(customer)
        if country:
            if country.is_fatf:
                note = max(note, 70.0)
            elif country.is_border:
                note = max(note, 55.0)
            elif country.is_uemoa:
                note = min(note, 40.0)

        logger.debug("C2=%.1f", note)
        return round(note, 2)

    # ──────────────────────────────────────────────────────────────────────
    # C3 — Historique transactionnel (poids 25 %)
    # ──────────────────────────────────────────────────────────────────────

    def _score_c3(self, customer: Customer) -> float:
        """
        Note brute C3 basée sur l'analyse des transactions des 90 derniers jours.

        Grille CDC :
          0-20  → Transactions régulières, montants cohérents avec revenus
          21-50 → Quelques pics mais justifiables
          51-80 → Pics fréquents, retraits cash répétés, fréquence anormale
          81-100 → Smurfing, virements inexpliqués vers pays à risque

        Détections couvertes (v1.3) :
          a) Ratio montant total / revenus déclarés sur 3 mois
          b) Fréquence anormale de transactions
          c) Retraits cash répétés
          d) Smurfing (montants ronds + near-threshold) [Fix 3, Fix 9]
          e) Destinations vers pays à risque
          f) Card testing — micro-tx carte répétées [Fix 8]
          g) Transactions dupliquées / replay [Fix 10]
        """
        # [Fix 6] cutoff naïf pour compatibilité PostgreSQL Column(DateTime) sans tz
        cutoff = _naive_utc_now() - timedelta(days=_TX_WINDOW_DAYS)
        # [Fix 5] or [] — sécurité si accounts est None
        account_ids = [acc.id for acc in (customer.accounts or [])]

        if not account_ids:
            logger.debug("C3=10 (aucun compte)")
            return 10.0

        transactions = (
            self.db.query(Transaction)
            .filter(
                Transaction.compte_id.in_(account_ids),
                Transaction.date_op >= cutoff,
            )
            .all()
        )

        if not transactions:
            logger.debug("C3=10 (aucune transaction sur 90j)")
            return 10.0

        montants = np.array([float(tx.montant) for tx in transactions])
        types_op = [tx.type_op or "" for tx in transactions]
        pays_dest = [tx.destination_pays_id for tx in transactions]
        rev = float(customer.revenus_declares or 0)

        note = 10.0

        # ── a) Ratio montant total / revenus déclarés sur 3 mois ──────────
        if rev > 0:
            ratio = float(np.sum(montants)) / (rev * 3)
            if ratio > 5:
                note = max(note, 80.0)
            elif ratio > 3:
                note = max(note, 60.0)
            elif ratio > 1.5:
                note = max(note, 40.0)

        # ── b) Fréquence anormale ──────────────────────────────────────────
        tx_per_day = len(transactions) / _TX_WINDOW_DAYS
        if tx_per_day > 5:
            note = max(note, 70.0)
        elif tx_per_day > 2:
            note = max(note, 45.0)

        # ── c) Retraits cash répétés ───────────────────────────────────────
        retraits = sum(1 for t in types_op if "RETRAIT" in t.upper())
        if retraits > 10:
            note = max(note, 65.0)
        elif retraits > 5:
            note = max(note, 40.0)

        # ── d) Détection smurfing [Fix 3, Fix 9] ─────────────────────────
        # On passe les objets Transaction complets + les revenus mensuels.
        # _detect_smurfing positionne aussi self._smurfing_detected [Fix 11].
        if self._detect_smurfing(transactions, revenus_mensuel=rev):
            note = max(note, 85.0)
            self._smurfing_detected = True  # [Fix 11] exposé dans le résultat
            logger.warning("⚠ Smurfing détecté — client %s", customer.id)

        # ── e) Destinations vers pays à risque ────────────────────────────
        risk_ids = self._get_risk_country_ids()
        risky = sum(1 for pid in pays_dest if pid in risk_ids)
        if risky > 0:
            ratio_risky = risky / len(transactions)
            if ratio_risky > 0.5:
                note = max(note, 75.0)
            elif ratio_risky > 0.2:
                note = max(note, 55.0)

        # ── f) Card testing — micro-transactions carte répétées [Fix 8] ───
        # La validité technique de la carte est gérée par le service dédié.
        # Ici on détecte le pattern comportemental : petits montants répétés
        # sur carte pour valider une carte volée avant une fraude de grande ampleur.
        card_micro_tx = [
            tx
            for tx in transactions
            if (
                tx.canal and "CARTE" in tx.canal.upper()
                and 0 < float(tx.montant) <= _CARD_TESTING_MAX_AMOUNT
            )
        ]
        self._card_testing_count = len(card_micro_tx)  # [Fix 11]
        if len(card_micro_tx) >= _CARD_TESTING_ALERT_COUNT:
            note = max(note, 75.0)
            logger.warning(
                "⚠ Card testing probable — client %s : %d micro-tx carte (≤%d XOF)",
                customer.id,
                len(card_micro_tx),
                _CARD_TESTING_MAX_AMOUNT,
            )
        elif len(card_micro_tx) >= _CARD_TESTING_WARN_COUNT:
            note = max(note, 45.0)
            logger.debug(
                "Card testing possible — client %s : %d micro-tx carte",
                customer.id,
                len(card_micro_tx),
            )

        # ── g) Transactions dupliquées / replay [Fix 10] ──────────────────
        dupes = self._detect_duplicates(transactions)
        if dupes >= 3:
            note = max(note, 60.0)
        elif dupes >= 1:
            note = max(note, 40.0)
        if dupes > 0:
            logger.warning(
                "⚠ %d groupe(s) de tx dupliquées détecté(s) — client %s",
                dupes,
                customer.id,
            )

        logger.debug("C3=%.1f (%d tx analysées)", note, len(transactions))
        return round(min(100.0, note), 2)

    # ── Smurfing ──────────────────────────────────────────────────────────

    def _detect_smurfing(
        self,
        transactions: list[Transaction],
        revenus_mensuel: float,
    ) -> bool:
        """
        Détecte le fractionnement (smurfing) avec trois garde-fous pour
        éliminer les faux positifs.  [Fix 3, Fix 9]

        Deux familles de transactions suspectes (logique OR) :
          • Montant rond multiple de 10 000 XOF, < 500 000 XOF
          • Near-threshold : entre 80 % et 100 % du seuil FATF [Fix 9]
            (495 000, 498 000 XOF… — forme de fraude la plus courante au Bénin)

        Trois conditions CUMULATIVES pour déclencher :
          1. Au moins _SMURFING_MIN_COUNT transactions suspectes.
          2. Ces transactions concentrées sur ≤ _SMURFING_WINDOW_DAYS (7 j).
          3. Total suspects ≥ _SMURFING_REVENUE_MULT × revenus mensuels (si renseignés).

        :param transactions: liste d'objets Transaction de la fenêtre 90j.
        :param revenus_mensuel: revenus déclarés en XOF (0 = non renseigné).
        :returns: True si smurfing probable.
        """
        if len(transactions) < _SMURFING_MIN_COUNT:
            return False

        near_low = _SMURFING_THRESHOLD * _SMURFING_NEAR_LOW_PCT

        # ── Étape 1 : filtrer les transactions suspectes (round OU near-threshold) ─
        suspects = [
            tx
            for tx in transactions
            if float(tx.montant) > 0
            and (
                # Montant rond classique
                (
                    float(tx.montant) % _SMURFING_ROUND_STEP == 0
                    and float(tx.montant) < _SMURFING_THRESHOLD
                )
                or
                # Near-threshold [Fix 9]
                (near_low <= float(tx.montant) < _SMURFING_THRESHOLD)
            )
        ]

        if len(suspects) < _SMURFING_MIN_COUNT:
            return False

        # ── Étape 2 : concentration temporelle ────────────────────────────
        dates = [_strip_tz(tx.date_op) for tx in suspects]
        dates = [d for d in dates if d is not None]

        if len(dates) < _SMURFING_MIN_COUNT:
            return False

        date_min = min(dates)
        date_max = max(dates)
        span_days = (date_max - date_min).days

        if span_days > _SMURFING_WINDOW_DAYS:
            logger.debug(
                "Smurfing écarté : %d tx suspectes sur %d jours (> %d j)",
                len(suspects),
                span_days,
                _SMURFING_WINDOW_DAYS,
            )
            return False

        # ── Étape 3 : ratio total suspects / revenus mensuels ─────────────
        if revenus_mensuel > 0:
            total_suspects = sum(float(tx.montant) for tx in suspects)
            if total_suspects < revenus_mensuel * _SMURFING_REVENUE_MULT:
                logger.debug(
                    "Smurfing écarté : total suspects=%.0f < %.0f (3× revenus)",
                    total_suspects,
                    revenus_mensuel * _SMURFING_REVENUE_MULT,
                )
                return False

        logger.debug(
            "Smurfing confirmé : %d tx, span=%d j",
            len(suspects),
            span_days,
        )
        return True

    # ── Transactions dupliquées ───────────────────────────────────────────

    def _detect_duplicates(self, transactions: list[Transaction]) -> int:
        """
        Détecte les groupes de transactions potentiellement dupliquées ou
        rejouées (même montant arrondi + même destination dans une fenêtre 24 h).

        Retourne le nombre de groupes suspects (0 = rien d'anormal).  [Fix 10]

        Arrondi à la centaine (_DUPLICATE_ROUND_TO=-2) pour tolérer les petites
        variations dues aux frais de service.
        """
        groups: dict[tuple, list[datetime]] = defaultdict(list)

        for tx in transactions:
            if tx.destination_pays_id is None:
                continue
            d = _strip_tz(tx.date_op)
            if d is None:
                continue
            key = (
                round(float(tx.montant), _DUPLICATE_ROUND_TO),
                tx.destination_pays_id,
                tx.compte_id,
            )
            groups[key].append(d)

        duplicate_groups = 0
        for dates in groups.values():
            if len(dates) < 2:
                continue
            dates_sorted = sorted(dates)
            for i in range(1, len(dates_sorted)):
                delta = (dates_sorted[i] - dates_sorted[i - 1]).total_seconds()
                if delta < _DUPLICATE_WINDOW_SECONDS:
                    duplicate_groups += 1
                    break  # un seul comptage par groupe

        return duplicate_groups

    def _get_risk_country_ids(self) -> set[int]:
        """Retourne les IDs des pays frontaliers ou listés FATF."""
        rows = (
            self.db.query(Country.id)
            .filter(
                (Country.is_border == True) | (Country.is_fatf == True)  # noqa: E712
            )
            .all()
        )
        return {r.id for r in rows}

    # ──────────────────────────────────────────────────────────────────────
    # C4 — Ancienneté & fidélité (poids 10 %)
    # ──────────────────────────────────────────────────────────────────────

    def _score_c4(self, customer: Customer) -> float:
        """
        Note brute C4 selon la durée de la relation avec l'IMF.

        Grille CDC :
          0-20  → Relation > 3 ans, comportement régulier
          21-50 → Relation entre 1 et 3 ans
          51-80 → Relation < 1 an
          81-100 → Client récent avec comportement inhabituel dès l'ouverture
        """
        if not customer.date_creation:
            return 60.0

        since = customer.date_creation
        if isinstance(since, datetime):
            since = since.date()

        delta = (date.today() - since).days

        if delta > 3 * 365:
            note = 10.0
        elif delta > 365:
            note = 35.0
        elif delta > 180:
            note = 60.0
        else:
            note = 75.0

        logger.debug("C4=%.1f (ancienneté=%d jours)", note, delta)
        return round(note, 2)

    # ──────────────────────────────────────────────────────────────────────
    # C5 — Statut PEP (poids 15 %)
    # ──────────────────────────────────────────────────────────────────────

    def _score_c5(self, customer: Customer) -> float:
        """
        Note brute C5 — Statut de Personne Exposée Politiquement.  [Fix 7]

        Grille révisée (alignée GAFI recommandation 12) :
          100 → PEP active  (statut_pep=True OU trouvée dans pep_list avec active=True)
           50 → Ancienne PEP (active=False — vigilance renforcée 5 ans post-mandat)
            0 → Aucune correspondance PEP connue

        Changement vs v1.2 :
          Avant : requête filtrée sur active=True → ancienne PEP invisible → note 0
          Après : pas de filtre active → ancienne PEP détectée → note 50  [Fix 7]

        Note : la gestion des proches de PEP est hors scope (table pep_relationships
        non présente dans le schéma actuel — roadmap V2).
        """
        # 1. Flag dur positionné manuellement par le compliance officer
        if customer.statut_pep:
            logger.debug("C5=100 (statut_pep=True)")
            return 100.0

        # 2. Recherche dans pep_list SANS filtre active — [Fix 7]
        #    order_by active.desc() : si doublon de nom, la PEP active est retournée en tête.
        match: PepEntry | None = (
            self.db.query(PepEntry)
            .filter(
                PepEntry.nom.ilike(customer.nom),
                PepEntry.prenom.ilike(customer.prenom),
            )
            .order_by(PepEntry.active.desc())
            .first()
        )

        if not match:
            logger.debug("C5=0 (aucune correspondance PEP)")
            return 0.0

        if match.active:
            logger.warning(
                "⚠ PEP ACTIVE — client %s : %s %s (fonction=%s)",
                customer.id,
                customer.prenom,
                customer.nom,
                match.fonction,
            )
            return 100.0

        # PEP inactive — vigilance résiduelle GAFI 5 ans
        logger.warning(
            "⚠ ANCIENNE PEP — client %s : %s %s (date_fin=%s, vigilance renforcée)",
            customer.id,
            customer.prenom,
            customer.nom,
            match.date_fin,
        )
        return 50.0

    # ──────────────────────────────────────────────────────────────────────
    # C6 — Cohérence KYC (poids 10 %)
    # ──────────────────────────────────────────────────────────────────────

    def _score_c6(self, customer: Customer) -> float:
        """
        Note brute C6 selon la complétude et la cohérence du dossier KYC.

        Grille CDC :
          0-20  → Dossier complet, revenus/patrimoine cohérents, docs valides
          21-50 → Dossier partiellement incomplet, documents expirant bientôt
          51-80 → Incohérences significatives revenus/patrimoine
          81-100 → Dossier incomplet, documents invalides ou frauduleux

        Note : kyc_completion est recalculé par compute_kyc_completion() à chaque
        ajout/modification de document (customer_service + router customer_docs).
        C6 fait confiance à cette valeur et concentre sa logique propre sur l'analyse
        fine des documents (expiration, invalides) et la cohérence revenus/flux.
        """
        note = 10.0
        # [Fix 5] or [] — sécurité si la relation documents est None
        docs = customer.documents or []

        if not docs:
            note = max(note, 85.0)
        else:
            today = date.today()
            bientot = today + timedelta(days=60)

            invalides = sum(
                1
                for d in docs
                if not d.valide or (d.date_expiration and d.date_expiration < today)
            )
            expirant = sum(
                1
                for d in docs
                if d.valide
                and d.date_expiration
                and today <= d.date_expiration < bientot
            )
            total = len(docs)
            ratio_inv = invalides / total

            if ratio_inv > 0.5:
                note = max(note, 85.0)
            elif invalides > 0:
                note = max(note, 55.0)
            elif expirant > 0:
                note = max(note, 30.0)

        # Cohérence revenus déclarés vs flux transactionnels moyens
        rev = float(customer.revenus_declares or 0)
        if rev > 0:
            avg_tx = self._avg_monthly_tx(customer)
            if avg_tx > 0:
                ratio = avg_tx / rev
                if ratio > 10:
                    note = max(note, 75.0)
                elif ratio > 5:
                    note = max(note, 55.0)
                elif ratio > 2:
                    note = max(note, 35.0)

        # Taux de complétion KYC déclaré (mis à jour par customer_service)
        completion = customer.kyc_completion or 0
        if completion < 30:
            note = max(note, 80.0)
        elif completion < 60:
            note = max(note, 40.0)

        logger.debug("C6=%.1f (kyc_completion=%d%%)", note, completion)
        return round(min(100.0, note), 2)

    def _avg_monthly_tx(self, customer: Customer) -> float:
        """
        Calcule le montant moyen mensuel des transactions du client
        sur la fenêtre des 90 derniers jours.

        :returns: montant moyen mensuel en XOF (0 si aucune transaction).
        """
        # [Fix 5] or [] — sécurité si accounts est None
        account_ids = [acc.id for acc in (customer.accounts or [])]
        if not account_ids:
            return 0.0

        # [Fix 6] _naive_utc_now() : même raison que dans _score_c3
        cutoff = _naive_utc_now() - timedelta(days=90)
        txs = (
            self.db.query(Transaction)
            .filter(
                Transaction.compte_id.in_(account_ids),
                Transaction.date_op >= cutoff,
            )
            .all()
        )
        if not txs:
            return 0.0

        return sum(float(tx.montant) for tx in txs) / 3

    # ──────────────────────────────────────────────────────────────────────
    # Catégorisation du score global
    # ──────────────────────────────────────────────────────────────────────

    def _get_category(self, score: int) -> str:
        """
        Retourne la catégorie de risque normalisée selon les seuils en base.

        Normalisation 'ELEVE' → 'ÉLEVÉ' [Fix 2] :
          La table risk_thresholds stocke 'ELEVE' (sans accent, seed Marcos),
          mais le contrat API v1.0 exige 'ÉLEVÉ' (avec accent). On normalise ici.
        """
        _NORMALIZE = {
            "ELEVE": "ÉLEVÉ",
            "ÉLEVÉ": "ÉLEVÉ",
            "MOYEN": "MOYEN",
            "FAIBLE": "FAIBLE",
        }

        for t in sorted(self._thresholds, key=lambda x: x["min_score"]):
            if t["min_score"] <= score <= t["max_score"]:
                raw = t["category"]
                return _NORMALIZE.get(raw.upper(), raw)  # [Fix 2]

        # Fallback absolu si aucun seuil ne couvre le score
        if score <= 33:
            return "FAIBLE"
        elif score <= 66:
            return "MOYEN"
        return "ÉLEVÉ"

    # ──────────────────────────────────────────────────────────────────────
    # Helpers : accès aux relations ORM avec fallback DB
    # ──────────────────────────────────────────────────────────────────────

    def _get_zone(self, customer: Customer) -> RiskZone | None:
        """Retourne la RiskZone du client (relation lazy ou FK directe)."""
        if customer.risk_zone:
            return customer.risk_zone
        if customer.zone_geo:
            return (
                self.db.query(RiskZone).filter(RiskZone.id == customer.zone_geo).first()
            )
        return None

    def _get_country(self, customer: Customer) -> Country | None:
        """Retourne le Country du client (relation lazy ou FK directe)."""
        if customer.country:
            return customer.country
        if customer.pays:
            return self.db.query(Country).filter(Country.id == customer.pays).first()
        return None
