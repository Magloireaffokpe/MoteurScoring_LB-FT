from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID


# ─── Sous-schemas ────────────────────────────────────────

class DocumentSchema(BaseModel):
    id: UUID
    type_doc: str
    numero: Optional[str]
    date_expiration: Optional[date]
    valide: bool

    model_config = {"from_attributes": True}


class DocumentCreate(BaseModel):
    type_doc: str
    numero: Optional[str] = None
    date_expiration: Optional[date] = None


class AccountSchema(BaseModel):
    id: UUID
    type_compte: Optional[str]
    solde_moyen: Optional[float]
    date_ouverture: Optional[date]
    status: Optional[str]

    model_config = {"from_attributes": True}


class AccountCreate(BaseModel):
    type_compte: Optional[str] = None
    date_ouverture: Optional[date] = None
    status: Optional[str] = None


class TransactionSchema(BaseModel):
    id: UUID
    montant: float
    devise: Optional[str]
    type_op: Optional[str]
    date_op: Optional[datetime]
    canal: Optional[str]
    origine: Optional[str]
    destination: Optional[str]
    origine_pays_id: Optional[int]
    destination_pays_id: Optional[int]

    model_config = {"from_attributes": True}


# ─── Customer Create ──────────────────────────────────────

class CustomerCreate(BaseModel):
    nom: str
    prenom: str
    date_naissance: Optional[date] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    profession_code: Optional[str] = None
    profession_name: Optional[str] = None
    profession_risk: Optional[str] = None
    revenus_declares: Optional[float] = None

    city: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    zone_geo: Optional[int] = None
    pays: Optional[int] = None

# ─── Customer Update ──────────────────────────────────────

class CustomerUpdate(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None

    profession_code: Optional[str] = None
    profession_name: Optional[str] = None
    profession_risk: Optional[str] = None
    revenus_declares: Optional[float] = None

    city: Optional[str] = None
    region: Optional[str] = None
    zone_geo: Optional[int] = None
    pays: Optional[int] = None

    kyc_level: Optional[str] = None
    kyc_completion: Optional[int] = None
    status: Optional[str] = None


# ─── Customer Summary (liste paginée) ─────────────────────

class CustomerSummary(BaseModel):
    id: UUID
    nom: str
    prenom: str
    phone: Optional[str]
    email: Optional[str]
    profession_code: Optional[str]
    profession_name: Optional[str]
    city: Optional[str] = None
    region: Optional[str] = None
    zone_geo: Optional[int]
    kyc_level: Optional[str]
    kyc_completion: Optional[int]
    statut_pep: bool
    status: Optional[str]
    date_creation: Optional[datetime]

    model_config = {"from_attributes": True}
# ─── Customer Detail (fiche complète + scoring) ───────────
# Consommé par GET /api/clients/{id}
# CRITIQUE : ce format est lu par le ScoringEngine de Magloire

class CustomerDetail(BaseModel):
    id: UUID
    nom: str
    prenom: str
    date_naissance: Optional[date]
    phone: Optional[str]
    email: Optional[str]

    profession_code: Optional[str]
    profession_name: Optional[str]
    profession_risk: Optional[str]
    revenus_declares: Optional[float]

    city: Optional[str]
    region: Optional[str]
    latitude: Optional[str]
    longitude: Optional[str]
    zone_geo: Optional[int]
    pays: Optional[int]

    statut_pep: bool
    kyc_level: Optional[str]
    kyc_completion: Optional[int]
    status: Optional[str]
    date_creation: Optional[datetime]
    updated_at: Optional[datetime]
    prochaine_revision_kyc: Optional[date] = None

    # Relations — nécessaires au ScoringEngine
    documents: List[DocumentSchema] = []
    accounts: List[AccountSchema] = []

    model_config = {"from_attributes": True}
