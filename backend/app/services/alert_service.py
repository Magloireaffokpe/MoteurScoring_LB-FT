from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.alerts import Alert

logger = logging.getLogger(__name__)

# Types d'alertes standardisés
ALERT_TYPE_SCORE_ELEVE  = "SCORE_ELEVE"
ALERT_TYPE_KYC_INCOMPLET = "KYC_INCOMPLET"
ALERT_TYPE_SMURFING     = "SMURFING"
ALERT_TYPE_PEP_DETECTE  = "PEP_DETECTE"

STATUS_OPEN         = "OPEN"
STATUS_UNDER_REVIEW = "UNDER_REVIEW"
STATUS_CLOSED       = "CLOSED"


def create_alert(
    db: Session,
    customer_id: UUID,
    alert_type: str,
    decision: Optional[str] = None,
) -> Alert:
    """
    Crée une nouvelle alerte pour un client.
    Utilise les noms de colonnes réels du modèle Alert.
    """
    alert = Alert(
        client_id=customer_id,       # ← client_id (pas customer_id)
        type_alerte=alert_type,      # ← type_alerte (pas alert_type)
        statut=STATUS_OPEN,          # ← statut (pas status)
        decision=decision,
        sar_declare=False,
    )
    db.add(alert)
    db.flush()
    logger.info("Alerte créée — type=%s client=%s", alert_type, customer_id)
    return alert


def has_open_alert(db: Session, customer_id: UUID, alert_type: str) -> bool:
    """Vérifie s'il existe déjà une alerte ouverte du même type pour ce client."""
    return db.query(Alert).filter(
        Alert.client_id == customer_id,       # ← client_id
        Alert.type_alerte == alert_type,      # ← type_alerte
        Alert.statut == STATUS_OPEN,          # ← statut
    ).first() is not None


def create_score_alert_if_needed(
    db: Session,
    customer_id: UUID,
    global_score: int,
    skip_if_open: bool = False,
) -> Optional[Alert]:
    """
    Crée automatiquement une alerte SCORE_ELEVE si le score ≥ 67.
    Ne crée pas de doublon si skip_if_open=True et alerte déjà ouverte.
    """
    if global_score < 67:
        return None

    if skip_if_open and has_open_alert(db, customer_id, ALERT_TYPE_SCORE_ELEVE):
        logger.info("Alerte SCORE_ELEVE déjà ouverte pour client %s — pas de doublon", customer_id)
        return None

    return create_alert(
        db=db,
        customer_id=customer_id,
        alert_type=ALERT_TYPE_SCORE_ELEVE,
        decision=f"Score de risque élevé ({global_score}/100) — seuil ÉLEVÉ atteint (≥67)",
    )