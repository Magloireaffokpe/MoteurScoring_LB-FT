import uuid
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    compte_id = Column(UUID(as_uuid=True), ForeignKey("customer_accounts.id", ondelete="CASCADE"), nullable=False,index=True)

    montant = Column(Numeric(15, 2), nullable=False)
    devise = Column(String(5), default="XOF",server_default="XOF") # 'XOF', 'USD', 'EUR', etc.
    type_op = Column(String(50), nullable=True)       # 'DEPOT', 'RETRAIT', 'VIREMENT', 'PAIEMENT'
    date_op = Column(DateTime, server_default=func.now(),index=True)
    canal = Column(String(50), nullable=True)         # 'MOBILE', 'GUICHET', 'INTERNET', 'ATM'

    # Texte libre — nom institution, compte, ville
    origine = Column(Text, nullable=True)
    destination = Column(Text, nullable=True)

    # FK pays — pour détection zones à risque (C3 scoring)
    origine_pays_id = Column(Integer, ForeignKey("countries.id"), nullable=True, index=True)
    destination_pays_id = Column(Integer, ForeignKey("countries.id"), nullable=True, index=True)

    # Relations
    account = relationship("CustomerAccount", back_populates="transactions")
    origine_pays = relationship("Country", foreign_keys=[origine_pays_id])
    destination_pays = relationship("Country", foreign_keys=[destination_pays_id])

    def __repr__(self):
        return f"<Transaction {self.type_op} {self.montant} {self.devise}>"