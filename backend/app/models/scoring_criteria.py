# app/models/scoring_criteria.py
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base

#Les 6 critères de scoring (C1-C6) avec leur poids
class ScoringCriteria(Base):
    
    __tablename__ = "scoring_criteria"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(5), unique=True, nullable=False)  # 'C1', 'C2', ... 'C6'
    weight = Column(Numeric(5, 2), nullable=False)  # En % → 20.00, 25.00, etc.
    name = Column(String(100), nullable=False)  # 'Profil professionnel', etc.
    description = Column(Text)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ScoringCriteria {self.code}: {self.weight}%>"