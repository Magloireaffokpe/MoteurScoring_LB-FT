"""
app/services/alert_service.py
==============================
Service de création et gestion des alertes LBC/FT — RiskGuard.

Types d'alertes officiels :
  SCORE_ELEVE, PEP_DETECTE, SEUIL_DEPASSE,
  BENEFICIAIRE_GROUPEMENT, KYC_INCOMPLET, SMURFING_DETECTE
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.alerts import Alert

logger = logging.getLogger(__name__)

# ── Types d'alertes standardisés ─────────────────────────────────────────
ALERT_TYPE_SCORE_ELEVE = "SCORE_ELEVE"
ALERT_TYPE_KYC_INCOMPLET = "KYC_INCOMPLET"
ALERT_TYPE_SMURFING_DETECTE = "SMURFING_DETECTE"
ALERT_TYPE_PEP_DETECTE = "PEP_DETECTE"
ALERT_TYPE_SEUIL_DEPASSE = "SEUIL_DEPASSE"
ALERT_TYPE_BENEFICIAIRE_GROUPEMENT = "BENEFICIAIRE_GROUPEMENT"

# ── Statuts ───────────────────────────────────────────────────────────────
STATUS_OPEN = "OPEN"
STATUS_UNDER_REVIEW = "UNDER_REVIEW"
STATUS_CLOSED = "CLOSED"


# ═══════════════════════════════════════════════════════════════════════════
# Fonctions de base
# ═══════════════════════════════════════════════════════════════════════════


def create_alert(
    db: Session,
    customer_id: UUID,
    alert_type: str,
    decision: Optional[str] = None,
) -> Alert:
    """
    Crée une nouvelle alerte pour un client.
    Utilise les noms de colonnes réels du modèle Alert.

    :param db:          Session SQLAlchemy active.
    :param customer_id: UUID du client concerné.
    :param alert_type:  Type d'alerte (constantes ALERT_TYPE_*).
    :param decision:    Texte libre décrivant la raison de l'alerte.
    :returns:           Instance Alert flushée (pas encore commitée).
    """
    alert = Alert(
        client_id=customer_id,  # ← client_id (pas customer_id)
        type_alerte=alert_type,  # ← type_alerte (pas alert_type)
        statut=STATUS_OPEN,  # ← statut (pas status)
        decision=decision,
        sar_declare=False,
    )
    db.add(alert)
    db.flush()
    logger.info("Alerte créée — type=%s client=%s", alert_type, customer_id)
    return alert


def has_open_alert(db: Session, customer_id: UUID, alert_type: str) -> bool:
    """
    Vérifie s'il existe déjà une alerte ouverte du même type pour ce client.

    :param db:          Session SQLAlchemy active.
    :param customer_id: UUID du client.
    :param alert_type:  Type d'alerte à vérifier.
    :returns:           True si une alerte OPEN du même type existe déjà.
    """
    return (
        db.query(Alert)
        .filter(
            Alert.client_id == customer_id,  # ← client_id
            Alert.type_alerte == alert_type,  # ← type_alerte
            Alert.statut == STATUS_OPEN,  # ← statut
        )
        .first()
    ) is not None


# ═══════════════════════════════════════════════════════════════════════════
# Fonction générique anti-doublon
# ═══════════════════════════════════════════════════════════════════════════


def create_if_not_open(
    db: Session,
    client_id: UUID,
    type_alerte: str,
    decision: Optional[str] = None,
) -> Optional[Alert]:
    """
    Crée une alerte du type donné uniquement si aucune alerte
    de ce type n'est déjà OPEN ou UNDER_REVIEW pour ce client.

    Évite les doublons d'alertes sur des événements récurrents
    (ex: cumul seuil dépassé plusieurs fois dans le même mois).

    :param db:          Session SQLAlchemy active.
    :param client_id:   UUID du client concerné.
    :param type_alerte: Type d'alerte (constantes ALERT_TYPE_*).
    :param decision:    Texte libre décrivant la raison.
    :returns:           Instance Alert flushée, ou None si déjà ouverte.
    """
    existing = (
        db.query(Alert)
        .filter(
            Alert.client_id == client_id,
            Alert.type_alerte == type_alerte,
            Alert.statut.in_([STATUS_OPEN, STATUS_UNDER_REVIEW]),
        )
        .first()
    )
    if existing:
        logger.info(
            "Alerte %s déjà ouverte pour client %s — pas de doublon",
            type_alerte, client_id,
        )
        return None

    alert = Alert(
        client_id=client_id,
        type_alerte=type_alerte,
        statut=STATUS_OPEN,
        decision=decision,
        sar_declare=False,
    )
    db.add(alert)
    db.flush()
    logger.info("Alerte créée — type=%s client=%s", type_alerte, client_id)
    return alert


# ═══════════════════════════════════════════════════════════════════════════
# Fonctions d'alertes conditionnelles
# ═══════════════════════════════════════════════════════════════════════════


def create_score_alert_if_needed(
    db: Session,
    customer_id: UUID,
    global_score: int,
    skip_if_open: bool = False,
) -> Optional[Alert]:
    """
    Crée automatiquement une alerte SCORE_ELEVE si le score global ≥ 67.
    Ne crée pas de doublon si skip_if_open=True et alerte déjà ouverte.

    :param db:           Session SQLAlchemy active.
    :param customer_id:  UUID du client.
    :param global_score: Score global calculé par ScoringEngine (0-100).
    :param skip_if_open: Si True, ne crée pas de doublon.
    :returns:            Instance Alert créée, ou None.
    """
    if global_score < 67:
        return None

    if skip_if_open and has_open_alert(db, customer_id, ALERT_TYPE_SCORE_ELEVE):
        logger.info(
            "Alerte SCORE_ELEVE déjà ouverte pour client %s — pas de doublon",
            customer_id,
        )
        return None

    return create_alert(
        db=db,
        customer_id=customer_id,
        alert_type=ALERT_TYPE_SCORE_ELEVE,
        decision=(
            f"Score de risque élevé ({global_score}/100) — "
            f"seuil ÉLEVÉ atteint (≥67)"
        ),
    )


def create_pep_alert_if_needed(
    db: Session,
    customer_id: UUID,
    c5_score: float,
    skip_if_open: bool = True,
) -> Optional[Alert]:
    """
    Crée l'alerte PEP_DETECTE si le client correspond à une Personne
    Politiquement Exposée (active ou ancienne).

    Logique :
      c5_score >= 50 → PEP_DETECTE (alerte unique pour tout niveau PEP)
      autre          → aucune alerte

    :param db:           Session SQLAlchemy active.
    :param customer_id:  UUID du client.
    :param c5_score:     Note brute C5 retournée par ScoringEngine (0 | 50 | 100).
    :param skip_if_open: Si True, ne crée pas de doublon.
    :returns:            Instance Alert créée, ou None.
    """
    if c5_score < 50.0:
        return None

    base_intro = "PEP active" if c5_score == 100.0 else "Ancienne PEP"

    if skip_if_open and has_open_alert(db, customer_id, ALERT_TYPE_PEP_DETECTE):
        logger.info(
            "Alerte PEP_DETECTE déjà ouverte pour client %s — pas de doublon",
            customer_id,
        )
        return None

    return create_alert(
        db=db,
        customer_id=customer_id,
        alert_type=ALERT_TYPE_PEP_DETECTE,
        decision=(
            f"{base_intro} identifiée — vigilance renforcée obligatoire (GAFI R.12). "
            f"Vérifier la source des fonds et justifier la relation commerciale."
        ),
    )


def create_smurfing_alert_if_needed(
    db: Session,
    customer_id: UUID,
    skip_if_open: bool = True,
) -> Optional[Alert]:
    """
    Crée une alerte SMURFING_DETECTE quand le moteur de scoring a détecté
    un fractionnement probable.

    :param db:           Session SQLAlchemy active.
    :param customer_id:  UUID du client.
    :param skip_if_open: Si True, ne crée pas de doublon.
    :returns:            Instance Alert créée, ou None.
    """
    if skip_if_open and has_open_alert(db, customer_id, ALERT_TYPE_SMURFING_DETECTE):
        logger.info(
            "Alerte SMURFING_DETECTE déjà ouverte pour client %s — pas de doublon",
            customer_id,
        )
        return None

    return create_alert(
        db=db,
        customer_id=customer_id,
        alert_type=ALERT_TYPE_SMURFING_DETECTE,
        decision=(
            "Fractionnement probable détecté : transactions à montants ronds ou "
            "near-threshold (< 500 000 XOF) concentrées sur une courte période. "
            "Vérifier la cohérence avec les revenus déclarés."
        ),
    )


def create_kyc_alert_if_needed(
    db: Session,
    customer_id: UUID,
    kyc_completion: int,
    skip_if_open: bool = True,
) -> Optional[Alert]:
    """
    Crée une alerte KYC_INCOMPLET si le taux de complétion est insuffisant.

    Seuil : kyc_completion < 40 % (niveau LOW selon determine_kyc_level).

    :param db:              Session SQLAlchemy active.
    :param customer_id:     UUID du client.
    :param kyc_completion:  Taux de complétion KYC (0-100, calculé par customer_service).
    :param skip_if_open:    Si True, ne crée pas de doublon.
    :returns:               Instance Alert créée, ou None.
    """
    if kyc_completion >= 40:
        return None

    if skip_if_open and has_open_alert(db, customer_id, ALERT_TYPE_KYC_INCOMPLET):
        logger.info(
            "Alerte KYC_INCOMPLET déjà ouverte pour client %s — pas de doublon",
            customer_id,
        )
        return None

    return create_alert(
        db=db,
        customer_id=customer_id,
        alert_type=ALERT_TYPE_KYC_INCOMPLET,
        decision=(
            f"Dossier KYC incomplet — taux de complétion : {kyc_completion}% "
            f"(seuil minimum : 40%). Relancer le client pour compléter le dossier."
        ),
    )
