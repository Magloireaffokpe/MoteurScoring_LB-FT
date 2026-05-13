from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.models.transactions import Transaction
from app.models.customer_accounts import CustomerAccount
from app.schemas.transaction import TransactionResponse
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("/customers/{customer_id}/transactions",
            response_model=PaginatedResponse[TransactionResponse])
def get_customer_transactions(
    customer_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    days: int = Query(90, ge=1, le=365),  # fenêtre temporelle
    type_op: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Transactions d'un client sur une fenêtre temporelle.
    Par défaut : 90 derniers jours (utilisé par ScoringEngine C3).
    """
    since = datetime.utcnow() - timedelta(days=days)

    query = db.query(Transaction)\
        .join(Transaction.account)\
        .filter(CustomerAccount.client_id == customer_id)\
        .filter(Transaction.date_op >= since)

    if type_op:
        query = query.filter(Transaction.type_op == type_op)

    total = query.count()
    items = query.order_by(Transaction.date_op.desc())\
                 .offset(skip).limit(limit).all()

    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Détail d'une transaction."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx