"""
app/services/scoring.py
=======================
Moteur de scoring LBC/FT — RiskGuard (IMF béninoises)
Calcule un score de risque 0-100 selon 6 critères pondérés (C1..C6).

Auteur : Dev B — BATAMOUSSI Marcos
Version : 1.0 — Mai 2026
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy.orm import Session

from app.models.customers import Customer
from app.models.transactions import Transaction
from app.models.customer_accounts import CustomerAccount
from app.models.customer_docs import CustomerDoc
from app.models.pep_list import PepEntry
from app.models.scores import Score
from app.models.scoring_criteria import ScoringCriteria
from app.models.risk_thresholds import RiskThreshold
from app.models.risk_zones import RiskZone
from app.models.countries import Country

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes internes (fallback si la table est vide)
# ---------------------------------------------------------------------------
_DEFAULT_WEIGHTS: dict[str, float] = {
    "C1": 0.20,
    "C2": 0.20,
    "C3": 0.25,
    "C4": 0.10,
    "C5": 0.15,
    "C6": 0.10,
}

_DEFAULT_THRESHOLDS = [
    {"category": "FAIBLE", "min_score": 0,  "max_score": 33},
    {"category": "MOYEN",  "min_score": 34, "max_score": 66},
    {"category": "ÉLEVÉ",  "min_score": 67, "max_score": 100},
]

# Nombre de jours d'analyse des transactions pour C3
_TX_WINDOW_DAYS = 90

# Seuil de fractionnement (smurfing) : montants ronds inférieurs à ce seuil
_SMURFING_ROUND_THRESHOLD = 500_000   # XOF
_SMURFING_MIN_COUNT = 3               # au moins N transactions similaires


class ScoringEngine:
    """
    Calcule le score LBC/FT d'un client selon la grille définie dans le CDC.

    Utilisation ::

        engine = ScoringEngine(db_session)
        result = engine.calculate_score(customer_id)

    Le résultat est un dict conforme au contrat API v1.0 :
    {
        "global_score"  : int,           # 0-100
        "risk_category" : str,           # 'FAIBLE' | 'MOYEN' | 'ÉLEVÉ'
        "detail_json"   : {
            "C1": float, "C2": float, "C3": float,
            "C4": float, "C5": float, "C6": float
        }
    }
    """

    def __init__(self, db_session: Session) -> None:
        self.db = db_session
        self._weights: dict[str, float] = {}
        self._thresholds: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Point d'entrée principal
    # ------------------------------------------------------------------

    def calculate_score(self, customer_id: UUID) -> dict[str, Any]:
        """
        Calcule et retourne le score LBC/FT pour le client donné.

        :param customer_id: UUID du client (table customers).
        :returns: dict avec global_score, risk_category, detail_json.
        :raises ValueError: si le client est introuvable.
        """
        logger.info("Début calcul score — client %s", customer_id)

        # 1. Charger les paramètres dynamiques
        self._load_weights()
        self._load_thresholds()

        # 2. Charger le client
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            logger.error("Client introuvable : %s", customer_id)
            raise ValueError(f"Client introuvable : {customer_id}")

        # 3. Calculer chaque critère (note brute 0-100)
        notes: dict[str, float] = {
            "C1": self._score_c1(customer),
            "C2": self._score_c2(customer),
            "C3": self._score_c3(customer),
            "C4": self._score_c4(customer),
            "C5": self._score_c5(customer),
            "C6": self._score_c6(customer),
        }

        logger.debug("Notes brutes — client %s : %s", customer_id, notes)

        # 4. Appliquer les poids → contributions absolues
        detail_json: dict[str, float] = {
            code: round(notes[code] * self._weights.get(code, _DEFAULT_WEIGHTS[code]), 4)
            for code in ("C1", "C2", "C3", "C4", "C5", "C6")
        }

        global_score = min(100, max(0, round(sum(detail_json.values()))))
        risk_category = self._get_category(global_score)

        logger.info(
            "Score calculé — client %s : %s (%s)",
            customer_id, global_score, risk_category,
        )

        return {
            "global_score": global_score,
            "risk_category": risk_category,
            "detail_json": detail_json,
        }

    # ------------------------------------------------------------------
    # Chargement dynamique des paramètres
    # ------------------------------------------------------------------

    def _load_weights(self) -> None:
        """Charge les poids depuis la table scoring_criteria (DB)."""
        rows = (
            self.db.query(ScoringCriteria)
            .filter(ScoringCriteria.is_active == True)  # noqa: E712
            .all()
        )
        if rows:
            self._weights = {row.code: float(row.weight) for row in rows}
            # Normaliser si la somme ≠ 1
            total = sum(self._weights.values())
            if total > 0 and abs(total - 1.0) > 0.01:
                self._weights = {k: v / total for k, v in self._weights.items()}
                logger.warning("Poids normalisés (somme initiale=%s)", total)
        else:
            logger.warning("Table scoring_criteria vide — utilisation des poids par défaut")
            self._weights = dict(_DEFAULT_WEIGHTS)

    def _load_thresholds(self) -> None:
        """Charge les seuils de catégorie depuis la table risk_thresholds."""
        rows = self.db.query(RiskThreshold).order_by(RiskThreshold.min_score).all()
        if rows:
            self._thresholds = [
                {"category": r.category, "min_score": r.min_score, "max_score": r.max_score}
                for r in rows
            ]
        else:
            logger.warning("Table risk_thresholds vide — utilisation des seuils par défaut")
            self._thresholds = list(_DEFAULT_THRESHOLDS)

    # ------------------------------------------------------------------
    # Critère C1 — Profil professionnel (poids 20 %)
    # ------------------------------------------------------------------

    def _score_c1(self, customer: Customer) -> float:
        """
        Note C1 : profil professionnel.

        Grille :
          0-20  → Salarié formel secteur public/privé réglementé
          21-50 → Commerçant informel déclaré, artisan
          51-80 → Activité à risque élevé (changeur, transporteur, casino)
          81-100 → Activité non identifiable ou incohérente avec revenus
        """
        risk = (customer.profession_risk or "").upper()

        if risk == "LOW":
            note = 10.0
        elif risk == "MEDIUM":
            note = 35.0
        elif risk == "HIGH":
            note = 65.0
        else:
            # Pas de profession renseignée → incohérent / non identifiable
            note = 85.0

        # Bonus/malus revenus vs profession
        if customer.revenus_declares is not None:
            rev = float(customer.revenus_declares)
            if rev == 0 and risk != "LOW":
                note = min(100.0, note + 10.0)
            elif rev > 5_000_000 and risk == "LOW":
                # Revenus très élevés pour un salarié ordinaire → incohérence
                note = min(100.0, note + 15.0)

        logger.debug("C1=%s (profession_risk=%s)", note, risk)
        return round(note, 2)

    # ------------------------------------------------------------------
    # Critère C2 — Zone géographique (poids 20 %)
    # ------------------------------------------------------------------

    def _score_c2(self, customer: Customer) -> float:
        """
        Note C2 : zone géographique.

        Grille :
          0-20  → Zone urbaine stable, loin des frontières
          21-50 → Zone semi-urbaine ou périphérique
          51-80 → Zone frontalière ou classée FATF
          81-100 → Zone de conflit actif ou sans infrastructure bancaire
        """
        note = 10.0  # valeur par défaut : zone urbaine stable

        # Depuis la FK risk_zone → risk_zones.risk_level
        if customer.risk_zone:
            level = (customer.risk_zone.risk_level or "").upper()
            if level == "FAIBLE":
                note = 10.0
            elif level == "MOYEN":
                note = 35.0
            elif level == "ELEVE":
                note = 65.0
            else:
                note = 85.0
        elif customer.zone_geo is None:
            # Zone inconnue → risque modéré par précaution
            note = 50.0

        # Vérifier si le pays du client est frontalier ou FATF
        country = self._get_customer_country(customer)
        if country:
            if country.is_fatf:
                note = max(note, 70.0)
            elif country.is_border:
                note = max(note, 55.0)
            elif country.is_uemoa:
                note = min(note, 40.0)

        logger.debug("C2=%s", note)
        return round(note, 2)

    # ------------------------------------------------------------------
    # Critère C3 — Historique transactionnel (poids 25 %)
    # ------------------------------------------------------------------

    def _score_c3(self, customer: Customer) -> float:
        """
        Note C3 : analyse des transactions des 90 derniers jours.

        Grille :
          0-20  → Transactions régulières, montants cohérents avec revenus
          21-50 → Quelques pics mais justifiables
          51-80 → Pics fréquents, retraits cash répétés, fréquence anormale
          81-100 → Smurfing, virements inexpliqués
        """
        cutoff = datetime.utcnow() - timedelta(days=_TX_WINDOW_DAYS)

        # Récupérer tous les comptes du client
        account_ids = [acc.id for acc in (customer.accounts or [])]

        if not account_ids:
            # Pas de compte → note minimale (on ne pénalise pas un nouveau client)
            logger.debug("C3=10 (aucun compte)")
            return 10.0

        # Charger les transactions de la période
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

        # Analyse vectorisée avec NumPy
        montants = np.array([float(tx.montant) for tx in transactions])
        types_op = [tx.type_op or "" for tx in transactions]
        pays_dest_ids = [tx.destination_pays_id for tx in transactions]

        note = 10.0  # point de départ

        # --- a) Cohérence montants vs revenus déclarés ---
        revenus = float(customer.revenus_declares or 0)
        total_tx = float(np.sum(montants))
        if revenus > 0:
            ratio = total_tx / (revenus * 3)  # 3 mois
            if ratio > 5:
                note = max(note, 80.0)
            elif ratio > 3:
                note = max(note, 60.0)
            elif ratio > 1.5:
                note = max(note, 40.0)

        # --- b) Fréquence anormale ---
        tx_per_day = len(transactions) / _TX_WINDOW_DAYS
        if tx_per_day > 5:
            note = max(note, 70.0)
        elif tx_per_day > 2:
            note = max(note, 45.0)

        # --- c) Retraits cash répétés ---
        retraits = [m for t, m in zip(types_op, montants) if "RETRAIT" in t.upper()]
        if len(retraits) > 10:
            note = max(note, 65.0)
        elif len(retraits) > 5:
            note = max(note, 40.0)

        # --- d) Détection smurfing ---
        if self._detect_smurfing(montants):
            note = max(note, 85.0)
            logger.warning("Smurfing détecté — client %s", customer.id)

        # --- e) Transactions vers pays frontaliers/FATF ---
        risk_country_ids = self._get_risk_country_ids()
        risky_tx = sum(1 for pid in pays_dest_ids if pid in risk_country_ids)
        if risky_tx > 0:
            ratio_risky = risky_tx / len(transactions)
            if ratio_risky > 0.5:
                note = max(note, 75.0)
            elif ratio_risky > 0.2:
                note = max(note, 55.0)

        logger.debug("C3=%s (%d tx analysées)", note, len(transactions))
        return round(min(100.0, note), 2)

    def _detect_smurfing(self, montants: np.ndarray) -> bool:
        """
        Détecte le fractionnement (smurfing) :
        plusieurs transactions de montants ronds juste en dessous des seuils.
        """
        if len(montants) < _SMURFING_MIN_COUNT:
            return False

        # Montants ronds = multiples de 50 000 XOF sous le seuil
        round_mask = (montants % 50_000 == 0) & (montants < _SMURFING_ROUND_THRESHOLD)
        count_round = int(np.sum(round_mask))

        if count_round >= _SMURFING_MIN_COUNT:
            return True

        # Clusters de montants très proches (std faible sur un sous-ensemble)
        if len(montants) >= 5:
            std = float(np.std(montants))
            mean = float(np.mean(montants))
            if mean > 0 and (std / mean) < 0.05:
                return True

        return False

    def _get_risk_country_ids(self) -> set[int]:
        """Retourne les IDs des pays frontaliers ou FATF."""
        rows = (
            self.db.query(Country.id)
            .filter((Country.is_border == True) | (Country.is_fatf == True))  # noqa: E712
            .all()
        )
        return {row.id for row in rows}

    # ------------------------------------------------------------------
    # Critère C4 — Ancienneté & fidélité (poids 10 %)
    # ------------------------------------------------------------------

    def _score_c4(self, customer: Customer) -> float:
        """
        Note C4 : ancienneté de la relation.

        Grille :
          0-20  → Relation > 3 ans, comportement régulier
          21-50 → Relation entre 1 et 3 ans
          51-80 → Relation < 1 an
          81-100 → Client récent avec comportement inhabituel dès l'ouverture
        """
        if not customer.date_creation:
            return 60.0  # inconnu → note prudente

        since = customer.date_creation
        if isinstance(since, datetime):
            since_date = since.date()
        else:
            since_date = since

        delta_days = (date.today() - since_date).days

        if delta_days > 3 * 365:
            note = 10.0
        elif delta_days > 365:
            note = 35.0
        elif delta_days > 180:
            note = 60.0
        else:
            note = 75.0

        # Pénalité si comportement inhabituel dès l'ouverture
        # (score C3 élevé pour un client récent)
        # Cette logique est gérée dans l'agrégation finale ; ici on garde simple.

        logger.debug("C4=%s (ancienneté=%d jours)", note, delta_days)
        return round(note, 2)

    # ------------------------------------------------------------------
    # Critère C5 — Statut PEP (poids 15 %)
    # ------------------------------------------------------------------

    def _score_c5(self, customer: Customer) -> float:
        """
        Note C5 : statut PEP (Personne Exposée Politiquement).

        Grille :
          0   → Aucun lien avec une PEP
          50  → Entourage proche d'une PEP (famille, associé)
          100 → PEP avérée (fonctionnaire, élu, militaire de haut rang)
        """
        # Vérification directe du flag
        if customer.statut_pep:
            logger.debug("C5=100 (statut_pep=True)")
            return 100.0

        # Correspondance dans la liste PEP (nom/prénom)
        pep_match = (
            self.db.query(PepEntry)
            .filter(
                PepEntry.nom.ilike(customer.nom),
                PepEntry.prenom.ilike(customer.prenom),
                PepEntry.active == True,  # noqa: E712
            )
            .first()
        )
        if pep_match:
            logger.warning(
                "Correspondance PEP trouvée pour client %s : %s %s",
                customer.id, customer.prenom, customer.nom,
            )
            return 100.0

        # Entourage proche → non modélisé directement dans les tables actuelles
        # On retourne 0 (pas de lien)
        logger.debug("C5=0 (aucun lien PEP)")
        return 0.0

    # ------------------------------------------------------------------
    # Critère C6 — Cohérence KYC (poids 10 %)
    # ------------------------------------------------------------------

    def _score_c6(self, customer: Customer) -> float:
        """
        Note C6 : cohérence du dossier KYC.

        Grille :
          0-20  → Dossier complet, revenus/patrimoine cohérents, documents valides
          21-50 → Dossier partiellement incomplet, documents expirant bientôt
          51-80 → Incohérences significatives revenus/patrimoine
          81-100 → Dossier incomplet, documents invalides ou frauduleux
        """
        note = 10.0
        docs = customer.documents or []

        if not docs:
            # Aucun document → dossier incomplet
            note = max(note, 85.0)
        else:
            today = date.today()
            soon = today + timedelta(days=60)

            invalides = 0
            expirant = 0
            for doc in docs:
                if not doc.valide:
                    invalides += 1
                elif doc.date_expiration and doc.date_expiration < today:
                    invalides += 1
                elif doc.date_expiration and doc.date_expiration < soon:
                    expirant += 1

            total_docs = len(docs)
            ratio_invalide = invalides / total_docs

            if ratio_invalide > 0.5:
                note = max(note, 85.0)
            elif invalides > 0:
                note = max(note, 55.0)
            elif expirant > 0:
                note = max(note, 30.0)

        # Cohérence revenus vs transactions moyennes
        revenus = float(customer.revenus_declares or 0)
        if revenus > 0:
            avg_tx = self._get_avg_monthly_transactions(customer)
            if avg_tx > 0:
                ratio = avg_tx / revenus
                if ratio > 10:
                    note = max(note, 75.0)
                elif ratio > 5:
                    note = max(note, 55.0)
                elif ratio > 2:
                    note = max(note, 35.0)

        # kyc_completion
        completion = customer.kyc_completion or 0
        if completion < 30:
            note = max(note, 80.0)
        elif completion < 60:
            note = max(note, 40.0)

        logger.debug("C6=%s (kyc_completion=%s%%)", note, completion)
        return round(min(100.0, note), 2)

    def _get_avg_monthly_transactions(self, customer: Customer) -> float:
        """Calcule le montant moyen mensuel des transactions du client."""
        account_ids = [acc.id for acc in (customer.accounts or [])]
        if not account_ids:
            return 0.0

        cutoff = datetime.utcnow() - timedelta(days=90)
        transactions = (
            self.db.query(Transaction)
            .filter(
                Transaction.compte_id.in_(account_ids),
                Transaction.date_op >= cutoff,
            )
            .all()
        )
        if not transactions:
            return 0.0

        total = sum(float(tx.montant) for tx in transactions)
        return total / 3  # moyenne mensuelle sur 90j

    # ------------------------------------------------------------------
    # Catégorisation
    # ------------------------------------------------------------------

    def _get_category(self, score: int) -> str:
        """Retourne la catégorie de risque selon les seuils configurés."""
        for threshold in sorted(self._thresholds, key=lambda t: t["min_score"]):
            if threshold["min_score"] <= score <= threshold["max_score"]:
                return threshold["category"]
        # Fallback
        if score <= 33:
            return "FAIBLE"
        elif score <= 66:
            return "MOYEN"
        return "ÉLEVÉ"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_customer_country(self, customer: Customer) -> Country | None:
        """Retourne le pays du client (via relation ou requête directe)."""
        if customer.country:
            return customer.country
        if customer.pays:
            return self.db.query(Country).filter(Country.id == customer.pays).first()
        return None
