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

class CountryUpdate(BaseModel):
    name: Optional[str] = None
    is_uemoa: Optional[bool] = None
    is_border: Optional[bool] = None
    is_fatf: Optional[bool] = None

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

@router.put("/countries/{country_id}", response_model=CountrySchema)
def update_country(
    country_id: int,
    data: CountryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """Met à jour un pays (flags is_border, is_fatf, is_uemoa, etc.)."""
    country = db.query(Country).filter(Country.id == country_id).first()
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    if data.name is not None:
        country.name = data.name
    if data.is_uemoa is not None:
        country.is_uemoa = data.is_uemoa
    if data.is_border is not None:
        country.is_border = data.is_border
    if data.is_fatf is not None:
        country.is_fatf = data.is_fatf

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
