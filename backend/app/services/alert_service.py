"""
app/services/alert_service.py
==============================
Service de gestion des alertes LBC/FT — RiskGuard.

Crée, met à jour et consulte les alertes associées aux clients.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.alerts import Alert

logger = logging.getLogger(__name__)

# Types d'alertes standardisés
ALERT_TYPE_SCORE_ELEVE = "SCORE_ELEVE"
ALERT_TYPE_KYC_INCOMPLET = "KYC_INCOMPLET"
ALERT_TYPE_SMURFING = "SMURFING"

RISK_LEVEL_HIGH = "HIGH"
RISK_LEVEL_MEDIUM = "MEDIUM"
RISK_LEVEL_LOW = "LOW"

STATUS_OPEN = "OPEN"
STATUS_UNDER_REVIEW = "UNDER_REVIEW"
STATUS_CLOSED = "CLOSED"


def create_alert(
    db: Session,
    customer_id: UUID,
    alert_type: str,
    risk_level: str,
    description: str,
    created_by: Optional[UUID] = None,
) -> Alert:
    """
    Crée une nouvelle alerte pour un client.

    :param db: Session SQLAlchemy.
    :param customer_id: UUID du client concerné.
    :param alert_type: Type d'alerte (ex: 'SCORE_ELEVE').
    :param risk_level: Niveau de risque ('HIGH', 'MEDIUM', 'LOW').
    :param description: Description textuelle de l'alerte.
    :param created_by: UUID de l'utilisateur déclencheur (None = AUTOMATED).
    :returns: Instance Alert créée et commitée.
    """
    alert = Alert(
        customer_id=customer_id,
        alert_type=alert_type,
        risk_level=risk_level,
        description=description,
        status=STATUS_OPEN,
        created_at=datetime.utcnow(),
    )
    db.add(alert)
    db.flush()  # Obtenir l'ID sans commit total (le router commite)
    logger.info(
        "Alerte créée — type=%s, client=%s, niveau=%s",
        alert_type, customer_id, risk_level,
    )
    return alert


def has_open_alert(db: Session, customer_id: UUID, alert_type: str) -> bool:
    """
    Vérifie s'il existe déjà une alerte ouverte du même type pour ce client.

    :param db: Session SQLAlchemy.
    :param customer_id: UUID du client.
    :param alert_type: Type d'alerte à vérifier.
    :returns: True si une alerte ouverte existe déjà.
    """
    existing = (
        db.query(Alert)
        .filter(
            Alert.customer_id == customer_id,
            Alert.alert_type == alert_type,
            Alert.status == STATUS_OPEN,
        )
        .first()
    )
    return existing is not None


def create_score_alert_if_needed(
    db: Session,
    customer_id: UUID,
    global_score: int,
    skip_if_open: bool = False,
) -> Optional[Alert]:
    """
    Crée automatiquement une alerte SCORE_ELEVE si le score ≥ 67.

    :param db: Session SQLAlchemy.
    :param customer_id: UUID du client.
    :param global_score: Score calculé.
    :param skip_if_open: Si True, ne crée pas d'alerte si une existe déjà.
    :returns: Alert créée ou None.
    """
    if global_score < 67:
        return None

    if skip_if_open and has_open_alert(db, customer_id, ALERT_TYPE_SCORE_ELEVE):
        logger.info(
            "Alerte SCORE_ELEVE déjà ouverte pour client %s — pas de doublon", customer_id
        )
        return None

    return create_alert(
        db=db,
        customer_id=customer_id,
        alert_type=ALERT_TYPE_SCORE_ELEVE,
        risk_level=RISK_LEVEL_HIGH,
        description=f"Score de risque élevé ({global_score}/100) — seuil ÉLEVÉ atteint (≥67)",
    )
