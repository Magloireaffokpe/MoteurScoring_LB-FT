import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Score(Base):
    __tablename__ = "scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)

    score_global = Column(Integer, nullable=False)            # 0–100
    detail_json = Column(JSONB, nullable=False)               # {"C1": 9.0, ..., "C6": 4.0}
    categorie = Column(String(10), nullable=False)            # 'FAIBLE', 'MOYEN', 'ELEVE'
    is_current = Column(Boolean, default=True, server_default="true")                 # seul le dernier = True
    date_calcul = Column(DateTime, server_default=func.now())
    calcule_par = Column(String(50), default="AUTOMATED")     # 'AUTOMATED' ou UUID user

    customer = relationship("Customer", back_populates="scores")
    alerts = relationship("Alert", foreign_keys="Alert.score_id", back_populates="score")

    def __repr__(self):
        return f"<Score {self.score_global} ({self.categorie}) — client {self.client_id}>"