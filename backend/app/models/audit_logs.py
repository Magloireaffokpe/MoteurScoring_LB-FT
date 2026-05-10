import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True,index=True)

    action = Column(String(100), nullable=False)  # 'VIEW_CUSTOMER', 'RESCORE', 'EXPORT_PDF'
    timestamp = Column(DateTime, server_default=func.now())
    ip_address = Column(String(45), nullable=True)

    user = relationship("User", back_populates="audit_logs")
    customer = relationship("Customer", foreign_keys=[client_id])

    def __repr__(self):
        return f"<AuditLog {self.action} — {self.timestamp}>"