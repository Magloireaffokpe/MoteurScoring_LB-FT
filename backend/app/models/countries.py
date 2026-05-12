# app/models/countries.py
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base
import sqlalchemy as sa

#table des pays reférentiels + code ISO
class Country(Base):

    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, index=True)
    code_iso = Column(String(3), unique=True, nullable=False)  # 'BJ', 'NG'
    name = Column(String(100), nullable=False)  # 'Bénin', 'Nigeria'
    is_uemoa = Column(Boolean, default=False,server_default=sa.text('false'))  # Union Économique
    is_border = Column(Boolean, default=False,server_default=sa.text('false'))  # À risque (frontalier)
    is_fatf = Column(Boolean, default=False,server_default=sa.text('false'))   # Listé FATF

    # Relation inverse
    customers = relationship("Customer", back_populates="country")

    def __repr__(self):
        return f"<Country {self.code_iso}: {self.name}>"