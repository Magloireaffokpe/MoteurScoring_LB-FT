import uuid
from datetime import date
from sqlalchemy import Column,String,Date,DateTime,ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class CustomerDoc(Base):
    __tablename__ = "customers_docs"

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    client_id= Column(UUID(as_uuid=True),ForeignKey("customers.id",ondelete="CASCADE"),nullable=False,index=True)

    type_doc = Column(String(50),nullable=False)  #CNI,passeport
    numero = Column(String(100),nullable=True)
    date_expiration = Column(Date,nullable=True)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,index=True)
    created_at=Column(DateTime, server_default=func.now())

    customer = relationship("Customer",back_populates="documents")

    @property
    def valide(self) -> bool:
        if self.date_expiration is None:
            return True
        return self.date_expiration >= date.today()

    def __repr__(self):
        return f"<CustomerDoc {self.type_doc} — client {self.client_id}>"