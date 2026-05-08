# app/models/risk_zones.py
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base



#table des zones à risque de blanchiment de capitaux
class RiskZone(Base):

    __tablename__ = "risk_zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 'CAPITALE', 'FRONTIERE'
    risk_level = Column(String(20), nullable=False)  # 'FAIBLE', 'MOYEN', 'ELEVE'
    source = Column(Text)  # 'GIABA', 'FATF', 'BCEAO'
    description = Column(Text)

    # Relation inverse
    customers = relationship("Customer", back_populates="risk_zone")

    def __repr__(self):
        return f"<RiskZone {self.name} ({self.risk_level})>"