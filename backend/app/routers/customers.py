from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import Optional
from uuid import UUID
import logging

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin, require_compliance_or_admin
from app.models.customers import Customer
from app.schemas.customer import (
    CustomerCreate, CustomerUpdate,
    CustomerSummary, CustomerDetail
)
from app.schemas.common import PaginatedResponse
from app.services.audit_service import log_action
from app.services.customer_service import compute_kyc_completion, determine_kyc_level
from app.services.alert_service import create_kyc_alert_if_needed


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/clients", response_model=PaginatedResponse[CustomerSummary])
def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=1000),
    search: Optional[str] = None,
    status: Optional[str] = None,
    kyc_level: Optional[str] = None,
    statut_pep: Optional[bool] = None,
    zone_geo: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Liste paginée et filtrable des clients.
    Critère d'acceptance : filtres cumulables, résultats < 1s.
    """
    query = db.query(Customer)

    if search:
        query = query.filter(
            or_(
                Customer.nom.ilike(f"%{search}%"),
                Customer.prenom.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
            )
        )
    if status:
        query = query.filter(Customer.status == status)
    if kyc_level:
        query = query.filter(Customer.kyc_level == kyc_level)
    if statut_pep is not None:
        query = query.filter(Customer.statut_pep == statut_pep)
    if zone_geo:
        query = query.filter(Customer.zone_geo == zone_geo)

    total = query.count()
    items = query.order_by(Customer.date_creation.desc())\
                 .offset(skip).limit(limit).all()

    log_action(db, str(current_user.id), "LIST_CLIENTS")

    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/clients/{customer_id}", response_model=CustomerDetail)
def get_client(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Détail complet d'un client.
    CRITIQUE : consommé par le ScoringEngine de Magloire.
    Retourne KYC + documents + comptes + zone géographique.
    """
    customer = db.query(Customer)\
        .options(
            joinedload(Customer.documents),
            joinedload(Customer.accounts),
            joinedload(Customer.risk_zone),
            joinedload(Customer.country),
            joinedload(Customer.scores),
            joinedload(Customer.alerts),
        )\
        .filter(Customer.id == customer_id)\
        .first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    log_action(db, str(current_user.id), "VIEW_CUSTOMER", client_id=str(customer_id))

    return customer


@router.post("/clients", response_model=CustomerSummary, status_code=201)
def create_client(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_compliance_or_admin)
):
    """
    Crée un nouveau client.
    Déclenche le scoring initial via ScoringEngine après création.
    """
    # Vérification doublon phone
    if data.phone:
        existing = db.query(Customer).filter(Customer.phone == data.phone).first()
        if existing:
            raise HTTPException(status_code=422, detail="Phone already exists")

    # Vérification doublon email
    if data.email:
        existing = db.query(Customer).filter(Customer.email == data.email).first()
        if existing:
            raise HTTPException(status_code=422, detail="Email already exists")

    customer = Customer(**data.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)

    completion = compute_kyc_completion(customer)
    customer.kyc_completion = completion
    customer.kyc_level = determine_kyc_level(completion)
    db.commit()
    db.refresh(customer)

    create_kyc_alert_if_needed(db, customer.id, completion)

    # Déclenche le scoring initial (module de Magloire)
    try:
        from app.services.scoring import ScoringEngine
        engine = ScoringEngine(db)
        engine.calculate_score(str(customer.id), scored_by="AUTOMATED")
    except Exception as e:
        # Log l'erreur mais ne bloque pas la création
        logger.warning("Scoring error for %s: %s", customer.id, e)

    log_action(db, str(current_user.id), "CREATE_CUSTOMER", client_id=str(customer.id))

    return customer


@router.put("/clients/{customer_id}", response_model=CustomerSummary)
def update_client(
    customer_id: UUID,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_compliance_or_admin)
):
    """Met à jour les informations d'un client."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    fields = data.model_dump(exclude_unset=True)

    # Vérification unicité email
    if "email" in fields and fields["email"]:
        existing = db.query(Customer).filter(
            Customer.email == fields["email"],
            Customer.id != customer_id
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Un autre client utilise déjà cet email")

    # Vérification unicité téléphone
    if "phone" in fields and fields["phone"]:
        existing = db.query(Customer).filter(
            Customer.phone == fields["phone"],
            Customer.id != customer_id
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Un autre client utilise déjà ce numéro de téléphone")

    for field, value in fields.items():
        setattr(customer, field, value)

    # Recalcule le % KYC si documents modifiés
    completion = compute_kyc_completion(customer)
    customer.kyc_completion = completion
    customer.kyc_level = determine_kyc_level(completion)

    db.commit()
    db.refresh(customer)

    create_kyc_alert_if_needed(db, customer.id, completion)

    log_action(db, str(current_user.id), "UPDATE_CUSTOMER", client_id=str(customer_id))

    return customer
