import uuid
from sqlalchemy import Column, Date, DateTime, Numeric,String,ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base

class CustomerAccount(Base):
    __tablename__= "customer_accounts"

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    client_id= Column(UUID(as_uuid=True),ForeignKey("customers.id",ondelete="CASCADE"),nullable=False, index=True)
    type_compte= Column(String(50),nullable=True) #epargne , courant
    solde_moyen = Column(Numeric(15,2),default=0)
    date_ouverture = Column(Date,nullable=True)
    status = Column(String(50), default="ACTIF",server_default="ACTIF")  #Actif, Bloqué
    created_at= Column(DateTime, server_default=func.now())

    customer = relationship("Customer", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CustomerAccount {self.type_compte} — client {self.client_id}>"
