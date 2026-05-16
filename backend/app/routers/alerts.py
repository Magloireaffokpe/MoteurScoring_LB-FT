from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.models.alerts import Alert
from app.schemas.alert import AlertCreate, AlertUpdate, AlertResponse
from app.schemas.common import PaginatedResponse
from app.services.audit_service import log_action

router = APIRouter()


@router.get("/alerts", response_model=PaginatedResponse[AlertResponse])
def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    statut: Optional[str] = None,        # 'OPEN', 'UNDER_REVIEW', 'CLOSED'
    type_alerte: Optional[str] = None,   # 'SCORE_ELEVE', 'KYC_INCOMPLET', 'PEP_DETECTE'
    sar_declare: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Liste paginée et filtrable des alertes."""
    query = db.query(Alert)

    if statut:
        query = query.filter(Alert.statut == statut)
    if type_alerte:
        query = query.filter(Alert.type_alerte == type_alerte)
    if sar_declare is not None:
        query = query.filter(Alert.sar_declare == sar_declare)

    total = query.count()
    items = query.order_by(Alert.date_creation.desc())\
                 .offset(skip).limit(limit).all()

    log_action(db, str(current_user.id), "LIST_ALERTS")

    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Détail d'une alerte."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    log_action(db, str(current_user.id), "VIEW_ALERT", client_id=str(alert.client_id))

    return alert


@router.get("/customers/{customer_id}/alerts", response_model=PaginatedResponse[AlertResponse])
def get_customer_alerts(
    customer_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Toutes les alertes d'un client spécifique."""
    query = db.query(Alert).filter(Alert.client_id == customer_id)
    total = query.count()
    items = query.order_by(Alert.date_creation.desc())\
                 .offset(skip).limit(limit).all()

    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("/alerts", response_model=AlertResponse, status_code=201)
def create_alert(
    data: AlertCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Crée une alerte manuelle."""
    alert = Alert(**data.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)

    log_action(db, str(current_user.id), "CREATE_ALERT", client_id=str(data.client_id))

    return alert


@router.put("/alerts/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: UUID,
    data: AlertUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Met à jour une alerte — statut, décision, SAR.
    Si statut = CLOSED, enregistre qui a clôturé.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(alert, field, value)

    # Si clôture — enregistre l'agent
    if data.statut == "CLOSED":
        from datetime import datetime
        alert.clos_par = current_user.id
        alert.date_cloture = datetime.utcnow()

    db.commit()
    db.refresh(alert)

    log_action(db, str(current_user.id), "UPDATE_ALERT", client_id=str(alert.client_id))

    return alert