from sqlalchemy.orm import Session
from app.models.audit_logs import AuditLog
import uuid


def log_action(
    db: Session,
    user_id: str,
    action: str,
    client_id: str = None,
    ip: str = "0.0.0.0"
):
    """
    Journalise chaque action sensible dans audit_logs.
    Appelé après chaque opération critique (login, rescore, export, etc.)
    """
    log = AuditLog(
        id=uuid.uuid4(),
        user_id=user_id,
        action=action,
        client_id=client_id,
        ip_address=ip
    )
    db.add(log)
    db.commit()