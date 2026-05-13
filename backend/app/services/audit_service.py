from sqlalchemy.orm import Session
from app.models.audit_logs import AuditLog
import uuid
import logging

logger = logging.getLogger(__name__)

# Constantes actions standardisées
ACTION_LOGIN = "LOGIN"
ACTION_LIST_CLIENTS = "LIST_CLIENTS"
ACTION_VIEW_CUSTOMER = "VIEW_CUSTOMER"
ACTION_CREATE_CUSTOMER = "CREATE_CUSTOMER"
ACTION_UPDATE_CUSTOMER = "UPDATE_CUSTOMER"
ACTION_LIST_ALERTS = "LIST_ALERTS"
ACTION_VIEW_ALERT = "VIEW_ALERT"
ACTION_CREATE_ALERT = "CREATE_ALERT"
ACTION_UPDATE_ALERT = "UPDATE_ALERT"
ACTION_SCORING_CALCULATE = "SCORING_CALCULATE"
ACTION_SCORING_RESCORE = "SCORING_RESCORE"
ACTION_EXPORT_PDF = "EXPORT_PDF"
ACTION_EXPORT_CSV = "EXPORT_CSV"
ACTION_IMPORT_PEP = "IMPORT_PEP_LIST"
ACTION_UPDATE_SCORING_CRITERIA = "UPDATE_SCORING_CRITERIA"


def log_action(
    db: Session,
    user_id: str,
    action: str,
    client_id: str = None,
    ip: str = "0.0.0.0"
):
    """
    Journalise chaque action sensible dans audit_logs.
    Le try/except garantit que l'audit ne fait jamais échouer
    l'opération principale.
    """
    try:
        log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=action,
            client_id=client_id,
            ip_address=ip
        )
        db.add(log)
        db.commit()
        logger.debug("Audit — user=%s action=%s client=%s", user_id, action, client_id)
    except Exception as exc:
        logger.error("Erreur journalisation audit : %s", exc)