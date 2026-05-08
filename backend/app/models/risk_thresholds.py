# app/models/risk_thresholds.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

#les seuils de risque pour catégoriser les clients en FAIBLE, MOYEN, ÉLEVÉ
class RiskThreshold(Base):
   
    __tablename__ = "risk_thresholds"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(10), unique=True, nullable=False)  # 'FAIBLE', 'MOYEN', 'ELEVE'
    score_min = Column(Integer, nullable=False)
    score_max = Column(Integer, nullable=False)
    action = Column(Text)  # Action requise (vigilance standard, renforcée, maximale)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<RiskThreshold {self.category}: {self.score_min}-{self.score_max}>"