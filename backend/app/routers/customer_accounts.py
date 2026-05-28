from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin, require_compliance_or_admin
from app.models.customer_accounts import CustomerAccount
from app.schemas.customer import AccountSchema, AccountCreate
from app.services.audit_service import log_action


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





@router.post("/customers/{customer_id}/accounts",
             response_model=AccountSchema, status_code=201)
def create_account(
    customer_id: UUID,
    data: AccountCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_compliance_or_admin)
):
    """Crée un compte bancaire pour un client."""
    # Vérifie que le client existe
    from app.models.customers import Customer
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    account = CustomerAccount(
        client_id=customer_id,
        **data.model_dump(exclude={"solde_moyen"}),
        solde_moyen=0,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    log_action(db, str(current_user.id), "CREATE_ACCOUNT",
               client_id=str(customer_id))
    return account   