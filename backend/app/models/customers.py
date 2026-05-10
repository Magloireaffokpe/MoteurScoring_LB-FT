import uuid
from sqlalchemy import Column, String, Boolean, Integer, Numeric, Date, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import sqlalchemy as sa


class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identité
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    date_naissance = Column(Date, nullable=True)
    phone = Column(String(20), unique=True, nullable=True)
    email = Column(String(150), unique=True, nullable=True)

    # Profession
    profession_code = Column(String(50), nullable=True)   # 'COMMER_TRANSFR', 'AGRI_MARAICH'
    profession_name = Column(String(150), nullable=True)
    profession_risk = Column(String(10), nullable=True)   # 'LOW', 'MEDIUM', 'HIGH'
    revenus_declares = Column(Numeric(15, 2), nullable=True)

    # Localisation
    city = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    zone_geo = Column(Integer, ForeignKey("risk_zones.id"), nullable=True)
    pays = Column(Integer, ForeignKey("countries.id"), nullable=True)

    # LBC/FT
    statut_pep = Column(Boolean, default=False,server_default=sa.text("false"),index=True)
    pep_verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    kyc_level = Column(String(10), default="LOW",server_default="LOW", index=True)         # 'LOW', 'MEDIUM', 'HIGH'
    kyc_completion = Column(Integer, default=0,server_default=sa.text('0'))           # % 0-100
    status = Column(String(20), default="ACTIVE",server_default="ACTIVE",index=True)         # 'ACTIVE', 'INACTIVE', 'SUSPENDED'

    date_creation = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relations
    risk_zone = relationship("RiskZone", back_populates="customers")
    country = relationship("Country", back_populates="customers")
    documents = relationship("CustomerDoc", back_populates="customer", cascade="all, delete-orphan")
    accounts = relationship("CustomerAccount", back_populates="customer", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="customer")
    scores = relationship("Score", back_populates="customer")

    def __repr__(self):
        return f"<Customer {self.prenom} {self.nom}>"