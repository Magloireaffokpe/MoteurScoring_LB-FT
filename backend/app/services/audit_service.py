"""
app/services/audit_service.py
==============================
Service de journalisation des actions — RiskGuard.

Enregistre toutes les actions sensibles dans la table audit_logs.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_logs import AuditLog

logger = logging.getLogger(__name__)

# Actions standardisées
ACTION_SCORING_CALCULATE = "SCORING_CALCULATE"
ACTION_SCORING_RESCORE = "SCORING_RESCORE"
ACTION_VIEW_CUSTOMER = "VIEW_CUSTOMER"
ACTION_CREATE_CUSTOMER = "CREATE_CUSTOMER"
ACTION_UPDATE_ALERT = "UPDATE_ALERT"

RESOURCE_CUSTOMER = "customer"
RESOURCE_SCORE = "score"
RESOURCE_ALERT = "alert"


def log_action(
    db: Session,
    user_id: Optional[UUID],
    action: str,
    resource_type: str,
    resource_id: str,
    ip_address: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """
    Journalise une action dans audit_logs.

    :param db: Session SQLAlchemy.
    :param user_id: UUID de l'utilisateur ayant effectué l'action.
    :param action: Code de l'action (ex: 'SCORING_CALCULATE').
    :param resource_type: Type de ressource concernée ('customer', 'score', etc.).
    :param resource_id: ID de la ressource (UUID ou int sous forme de string).
    :param ip_address: Adresse IP de la requête (optionnel).
    :param extra: Données supplémentaires (optionnel).
    """
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            timestamp=datetime.utcnow(),
            ip_address=ip_address,
        )
        db.add(entry)
        db.flush()
        logger.debug(
            "Audit — user=%s action=%s resource=%s/%s",
            user_id, action, resource_type, resource_id,
        )
    except Exception as exc:  # pragma: no cover
        # L'audit ne doit jamais faire échouer l'opération principale
        logger.error("Erreur journalisation audit : %s", exc)
