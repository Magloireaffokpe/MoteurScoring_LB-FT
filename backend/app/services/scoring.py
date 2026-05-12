"""
app/services/scoring.py
=======================
Moteur de scoring LBC/FT — RiskGuard (IMF béninoises)
Calcule un score de risque 0-100 selon 6 critères pondérés (C1..C6).

Compatibilité seed_db.py :
  - ScoringCriteria.weight  : valeur entière (20, 25, 10...) → divisée par 100
  - RiskThreshold           : champs score_min / score_max (pas min_score/max_score)
  - RiskZone.risk_level     : 'FAIBLE' | 'MOYEN' | 'ELEVE' | 'TRES_ELEVE'

Auteur : Dev B — BATAMOUSSI Marcos
Version : 1.1 — Mai 2026
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy.orm import Session

from app.models.countries import Country
from app.models.customer_accounts import CustomerAccount
from app.models.customer_docs import CustomerDoc
from app.models.customers import Customer
from app.models.pep_list import PepEntry
from app.models.risk_thresholds import RiskThreshold
from app.models.risk_zones import RiskZone
from app.models.scores import Score
from app.models.scoring_criteria import ScoringCriteria
from app.models.transactions import Transaction

logger = logging.getLogger(__name__)

# ── Fallback si les tables sont vides ─────────────────────────────────────
_DEFAULT_WEIGHTS: dict[str, float] = {
    "C1": 0.20, "C2": 0.20, "C3": 0.25,
    "C4": 0.10, "C5": 0.15, "C6": 0.10,
}

_DEFAULT_THRESHOLDS = [
    {"category": "FAIBLE", "min_score": 0,  "max_score": 33},
    {"category": "MOYEN",  "min_score": 34, "max_score": 66},
    {"category": "ÉLEVÉ",  "min_score": 67, "max_score": 100},
]

# Analyse C3 sur 90 jours
_TX_WINDOW_DAYS = 90

# Smurfing : montants ronds sous ce seuil
_SMURFING_THRESHOLD  = 500_000   # XOF
_SMURFING_ROUND_STEP = 10_000    # multiple de 10k
_SMURFING_MIN_COUNT  = 3         # au moins N transactions similaires


class ScoringEngine:
    """
    Calcule le score LBC/FT d'un client selon la grille définie dans le CDC.

    ::

        engine = ScoringEngine(db_session)
        result = engine.calculate_score(customer_id)

    Retourne ::

        {
            "global_score"  : int,         # 0-100
            "risk_category" : str,         # 'FAIBLE' | 'MOYEN' | 'ÉLEVÉ'
            "detail_json"   : {
                "C1": float,               # contribution = note_brute × poids
                "C2": float,
                "C3": float,
                "C4": float,
                "C5": float,
                "C6": float
            }
        }
    """

    def __init__(self, db_session: Session) -> None:
        self.db = db_session
        self._weights: dict[str, float] = {}
        self._thresholds: list[dict[str, Any]] = []

    # ──────────────────────────────────────────────────────────────────────
    # Point d'entrée public
    # ──────────────────────────────────────────────────────────────────────

    def calculate_score(self, customer_id: UUID) -> dict[str, Any]:
        """
        Calcule et retourne le score LBC/FT pour un client.

        :raises ValueError: si le client est introuvable.
        """
        logger.info("Début calcul score — client %s", customer_id)

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

        logger.debug("Notes brutes — %s : %s", customer_id, notes)

        detail_json: dict[str, float] = {
            code: round(notes[code] * self._weights.get(code, _DEFAULT_WEIGHTS[code]), 4)
            for code in ("C1", "C2", "C3", "C4", "C5", "C6")
        }

        global_score   = min(100, max(0, round(sum(detail_json.values()))))
        risk_category  = self._get_category(global_score)

        logger.info("Score — client %s : %s (%s)", customer_id, global_score, risk_category)

        return {
            "global_score": global_score,
            "risk_category": risk_category,
            "detail_json": detail_json,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Chargement dynamique des paramètres
    # ──────────────────────────────────────────────────────────────────────

    def _load_weights(self) -> None:
        """
        Charge les poids depuis scoring_criteria.
        Le champ weight est stocké en pourcentage entier (20, 25…)
        → on divise par 100 pour obtenir une fraction décimale.
        """
        rows = (
            self.db.query(ScoringCriteria)
            .filter(ScoringCriteria.is_active == True)  # noqa: E712
            .all()
        )
        if rows:
            raw = {r.code: float(r.weight) for r in rows}
            total = sum(raw.values())
            # Normalisation (robuste à toute somme)
            if total > 0:
                self._weights = {k: v / total for k, v in raw.items()}
            else:
                self._weights = dict(_DEFAULT_WEIGHTS)
        else:
            logger.warning("scoring_criteria vide — poids par défaut utilisés")
            self._weights = dict(_DEFAULT_WEIGHTS)

    def _load_thresholds(self) -> None:
        """
        Charge les seuils depuis risk_thresholds.
        Colonnes : score_min / score_max (conformes au seed_db.py réel).
        """
        rows = self.db.query(RiskThreshold).order_by(RiskThreshold.score_min).all()
        if rows:
            self._thresholds = [
                {
                    "category":  r.category,
                    "min_score": r.score_min,
                    "max_score": r.score_max,
                }
                for r in rows
            ]
        else:
            logger.warning("risk_thresholds vide — seuils par défaut utilisés")
            self._thresholds = list(_DEFAULT_THRESHOLDS)

    # ──────────────────────────────────────────────────────────────────────
    # C1 — Profil professionnel (poids 20 %)
    # ──────────────────────────────────────────────────────────────────────

    def _score_c1(self, customer: Customer) -> float:
        """
        Grille :
          0-20  → Salarié formel secteur public/privé réglementé
          21-50 → Commerçant informel déclaré, artisan
          51-80 → Activité à risque élevé (changeur, transporteur, casino)
          81-100 → Activité non identifiable ou incohérente avec revenus
        """
        risk = (customer.profession_risk or "").upper()

        note = {
            "LOW":    10.0,
            "MEDIUM": 35.0,
            "HIGH":   65.0,
        }.get(risk, 85.0)   # inconnu → non identifiable

        # Incohérence revenus/profession
        rev = float(customer.revenus_declares or 0)
        if rev == 0 and risk not in ("HIGH", ""):
            note = min(100.0, note + 10.0)
        elif rev > 5_000_000 and risk == "LOW":
            note = min(100.0, note + 15.0)

        logger.debug("C1=%.1f (risk=%s)", note, risk)
        return round(note, 2)

    # ──────────────────────────────────────────────────────────────────────
    # C2 — Zone géographique (poids 20 %)
    # ──────────────────────────────────────────────────────────────────────

    def _score_c2(self, customer: Customer) -> float:
        """
        Grille :
          0-20  → Zone urbaine stable, loin des frontières
          21-50 → Zone semi-urbaine ou périphérique
          51-80 → Zone frontalière ou classée FATF
          81-100 → Zone de conflit actif ou sans infrastructure bancaire

        risk_level seed : 'FAIBLE' | 'MOYEN' | 'ELEVE' | 'TRES_ELEVE'
        """
        note = 50.0  # inconnu par défaut → prudence

        zone = self._get_zone(customer)
        if zone:
            level = (zone.risk_level or "").upper()
            note = {
                "FAIBLE":     10.0,
                "MOYEN":      35.0,
                "ELEVE":      65.0,
                "TRES_ELEVE": 88.0,
            }.get(level, 50.0)

        # Surcharge pays
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

    def _get_zone(self, customer: Customer) -> RiskZone | None:
        if customer.risk_zone:
            return customer.risk_zone
        if customer.zone_geo:
            return self.db.query(RiskZone).filter(RiskZone.id == customer.zone_geo).first()
        return None

    def _get_country(self, customer: Customer) -> Country | None:
        if customer.country:
            return customer.country
        if customer.pays:
            return self.db.query(Country).filter(Country.id == customer.pays).first()
        return None

    # ──────────────────────────────────────────────────────────────────────
    # C3 — Historique transactionnel (poids 25 %)
    # ──────────────────────────────────────────────────────────────────────

    def _score_c3(self, customer: Customer) -> float:
        """
        Grille :
          0-20  → Transactions régulières, montants cohérents avec revenus
          21-50 → Quelques pics mais justifiables
          51-80 → Pics fréquents, retraits cash répétés, fréquence anormale
          81-100 → Smurfing, virements inexpliqués vers pays à risque
        """
        cutoff      = datetime.utcnow() - timedelta(days=_TX_WINDOW_DAYS)
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

        montants    = np.array([float(tx.montant) for tx in transactions])
        types_op    = [tx.type_op or "" for tx in transactions]
        pays_dest   = [tx.destination_pays_id for tx in transactions]

        note = 10.0

        # a) Ratio montant total / revenus déclarés
        rev = float(customer.revenus_declares or 0)
        if rev > 0:
            ratio = float(np.sum(montants)) / (rev * 3)
            if   ratio > 5:   note = max(note, 80.0)
            elif ratio > 3:   note = max(note, 60.0)
            elif ratio > 1.5: note = max(note, 40.0)

        # b) Fréquence anormale
        tx_per_day = len(transactions) / _TX_WINDOW_DAYS
        if   tx_per_day > 5: note = max(note, 70.0)
        elif tx_per_day > 2: note = max(note, 45.0)

        # c) Retraits cash répétés
        retraits = sum(1 for t in types_op if "RETRAIT" in t.upper())
        if   retraits > 10: note = max(note, 65.0)
        elif retraits > 5:  note = max(note, 40.0)

        # d) Détection smurfing
        if self._detect_smurfing(montants):
            note = max(note, 85.0)
            logger.warning("⚠ Smurfing détecté — client %s", customer.id)

        # e) Destinations vers pays à risque
        risk_ids = self._get_risk_country_ids()
        risky    = sum(1 for pid in pays_dest if pid in risk_ids)
        if risky > 0:
            ratio_risky = risky / len(transactions)
            if   ratio_risky > 0.5: note = max(note, 75.0)
            elif ratio_risky > 0.2: note = max(note, 55.0)

        logger.debug("C3=%.1f (%d tx)", note, len(transactions))
        return round(min(100.0, note), 2)

    def _detect_smurfing(self, montants: np.ndarray) -> bool:
        """
        Détecte le fractionnement :
        ≥ N transactions de montants ronds < seuil FATF.
        """
        if len(montants) < _SMURFING_MIN_COUNT:
            return False

        # Montants ronds (multiples de 10 000 XOF) sous le seuil
        round_mask  = (montants % _SMURFING_ROUND_STEP == 0) & (montants < _SMURFING_THRESHOLD)
        if int(np.sum(round_mask)) >= _SMURFING_MIN_COUNT:
            return True

        # Cluster très homogène sur un ensemble de montants élevés
        if len(montants) >= 5:
            mean = float(np.mean(montants))
            std  = float(np.std(montants))
            if mean > 0 and (std / mean) < 0.05 and mean > 100_000:
                return True

        return False

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
        Grille :
          0-20  → Relation > 3 ans, comportement régulier
          21-50 → Relation 1-3 ans
          51-80 → Relation < 1 an
          81-100 → Client récent avec comportement inhabituel dès l'ouverture
        """
        if not customer.date_creation:
            return 60.0   # inconnu → prudence

        since = customer.date_creation
        if isinstance(since, datetime):
            since = since.date()

        delta = (date.today() - since).days

        if   delta > 3 * 365: note = 10.0
        elif delta > 365:     note = 35.0
        elif delta > 180:     note = 60.0
        else:                 note = 75.0

        logger.debug("C4=%.1f (%d jours)", note, delta)
        return round(note, 2)

    # ──────────────────────────────────────────────────────────────────────
    # C5 — Statut PEP (poids 15 %)
    # ──────────────────────────────────────────────────────────────────────

    def _score_c5(self, customer: Customer) -> float:
        """
        Grille :
          0   → Aucun lien PEP
          50  → Entourage proche (famille, associé)
          100 → PEP avérée (fonctionnaire, élu, militaire de haut rang)
        """
        # Flag direct
        if customer.statut_pep:
            logger.debug("C5=100 (statut_pep=True)")
            return 100.0

        # Correspondance dans la liste PEP (insensible à la casse)
        match = (
            self.db.query(PepEntry)
            .filter(
                PepEntry.nom.ilike(customer.nom),
                PepEntry.prenom.ilike(customer.prenom),
                PepEntry.active == True,  # noqa: E712
            )
            .first()
        )
        if match:
            logger.warning("⚠ Correspondance PEP — client %s : %s %s",
                           customer.id, customer.prenom, customer.nom)
            return 100.0

        logger.debug("C5=0 (non PEP)")
        return 0.0

    # ──────────────────────────────────────────────────────────────────────
    # C6 — Cohérence KYC (poids 10 %)
    # ──────────────────────────────────────────────────────────────────────

    def _score_c6(self, customer: Customer) -> float:
        """
        Grille :
          0-20  → Dossier complet, revenus/patrimoine cohérents, docs valides
          21-50 → Dossier partiel, documents expirant bientôt
          51-80 → Incohérences significatives revenus/transactions
          81-100 → Dossier incomplet, documents invalides ou frauduleux
        """
        note = 10.0
        docs = customer.documents or []

        if not docs:
            note = max(note, 85.0)
        else:
            today = date.today()
            bientot = today + timedelta(days=60)

            invalides = sum(
                1 for d in docs
                if not d.valide or (d.date_expiration and d.date_expiration < today)
            )
            expirant = sum(
                1 for d in docs
                if d.valide and d.date_expiration and today <= d.date_expiration < bientot
            )
            total = len(docs)

            ratio_inv = invalides / total
            if   ratio_inv > 0.5:  note = max(note, 85.0)
            elif invalides > 0:    note = max(note, 55.0)
            elif expirant  > 0:    note = max(note, 30.0)

        # Cohérence revenus vs transactions moyennes mensuelles
        rev = float(customer.revenus_declares or 0)
        if rev > 0:
            avg_tx = self._avg_monthly_tx(customer)
            if avg_tx > 0:
                ratio = avg_tx / rev
                if   ratio > 10: note = max(note, 75.0)
                elif ratio > 5:  note = max(note, 55.0)
                elif ratio > 2:  note = max(note, 35.0)

        # Taux de complétion KYC
        completion = customer.kyc_completion or 0
        if   completion < 30: note = max(note, 80.0)
        elif completion < 60: note = max(note, 40.0)

        logger.debug("C6=%.1f (kyc_completion=%d%%)", note, completion)
        return round(min(100.0, note), 2)

    def _avg_monthly_tx(self, customer: Customer) -> float:
        """Montant moyen mensuel des transactions (fenêtre 90 jours)."""
        account_ids = [acc.id for acc in (customer.accounts or [])]
        if not account_ids:
            return 0.0

        cutoff = datetime.utcnow() - timedelta(days=90)
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
        return sum(float(tx.montant) for tx in txs) / 3   # moyenne sur 3 mois

    # ──────────────────────────────────────────────────────────────────────
    # Catégorisation
    # ──────────────────────────────────────────────────────────────────────

    def _get_category(self, score: int) -> str:
        """Retourne la catégorie de risque selon les seuils en base."""
        for t in sorted(self._thresholds, key=lambda x: x["min_score"]):
            if t["min_score"] <= score <= t["max_score"]:
                return t["category"]
        # Fallback absolu
        if   score <= 33:  return "FAIBLE"
        elif score <= 66:  return "MOYEN"
        return "ÉLEVÉ"
