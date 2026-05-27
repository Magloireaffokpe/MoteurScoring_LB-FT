import uuid
from sqlalchemy import Column, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    clos_par = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    type_alerte = Column(String(50), nullable=False)   # 'SCORE_ELEVE', 'KYC_INCOMPLET', 'PEP_DETECTE', 'SMURFING_DETECTE', 'SEUIL_DEPASSE', 'BENEFICIAIRE_GROUPEMENT'
    statut = Column(String(20), nullable=False, default="OPEN", server_default="OPEN",index=True)        # 'OPEN', 'UNDER_REVIEW', 'CLOSED'
    decision = Column(Text, nullable=True)
    sar_declare = Column(Boolean, nullable=False, default=False, server_default="false")
    date_creation = Column(DateTime, server_default=func.now())
    date_cloture = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="alerts")
    closed_by = relationship("User", foreign_keys=[clos_par])

    def __repr__(self):
        return f"<Alert {self.type_alerte} — {self.statut}>"