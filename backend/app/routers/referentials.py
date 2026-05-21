from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.models.countries import Country
from app.models.risk_zones import RiskZone
from app.auth.dependencies import get_current_user, require_admin

router = APIRouter()

class CountryCreate(BaseModel):
    code_iso: str
    name: str
    is_uemoa: Optional[bool] = False
    is_border: Optional[bool] = False
    is_fatf: Optional[bool] = False

class CountrySchema(BaseModel):
    id: int
    code_iso: str
    name: str
    is_uemoa: bool
    is_border: bool
    is_fatf: bool

    model_config = {"from_attributes": True}

class RiskZoneSchema(BaseModel):
    id: int
    name: str
    risk_level: str
    source: Optional[str] = None
    description: Optional[str] = None

    model_config = {"from_attributes": True}

@router.get("/countries", response_model=List[CountrySchema])
def get_countries(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Retourne la liste des pays."""
    return db.query(Country).all()

@router.post("/countries", response_model=CountrySchema, status_code=201)
def create_country(
    data: CountryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """Crée un nouveau pays."""
    existing = db.query(Country).filter(Country.code_iso == data.code_iso.upper()).first()
    if existing:
        raise HTTPException(status_code=422, detail="ISO code already exists")
    
    country = Country(
        code_iso=data.code_iso.upper(),
        name=data.name,
        is_uemoa=data.is_uemoa,
        is_border=data.is_border,
        is_fatf=data.is_fatf
    )
    db.add(country)
    db.commit()
    db.refresh(country)
    return country

@router.get("/risk-zones", response_model=List[RiskZoneSchema])
def get_risk_zones(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Retourne la liste des zones de risque."""
    return db.query(RiskZone).all()
