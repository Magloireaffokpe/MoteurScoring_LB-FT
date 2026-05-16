from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.models.customer_accounts import CustomerAccount
from app.schemas.customer import AccountSchema


router = APIRouter()


@router.get("/customers/{customer_id}/accounts")
def get_customer_accounts(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Comptes bancaires d'un client."""
    accounts = db.query(CustomerAccount)\
        .filter(CustomerAccount.client_id == customer_id).all()

    return {
        "items": accounts,
        "total": len(accounts)
    }


@router.get("/accounts/{account_id}", response_model=AccountSchema)
def get_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Détail d'un compte."""
    account = db.query(CustomerAccount)\
        .filter(CustomerAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account