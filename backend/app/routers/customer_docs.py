from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin, require_compliance_or_admin
from app.models.customer_docs import CustomerDoc
from app.schemas.customer import DocumentSchema, DocumentCreate
from app.services.audit_service import log_action

router = APIRouter()


@router.get("/customers/{customer_id}/documents")
def get_customer_documents(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Documents KYC d'un client."""
    docs = db.query(CustomerDoc)\
        .filter(CustomerDoc.client_id == customer_id).all()

    return {
        "items": [DocumentSchema.model_validate(d).model_dump() for d in docs],
        "total": len(docs)
    }


@router.get("/documents/{doc_id}", response_model=DocumentSchema)
def get_document(
    doc_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Détail d'un document."""
    doc = db.query(CustomerDoc).filter(CustomerDoc.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.post("/customers/{customer_id}/documents",
             response_model=DocumentSchema, status_code=201)
def create_document(
    customer_id: UUID,
    data: DocumentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_compliance_or_admin)
):
    """Ajoute un document KYC à un client."""
    from app.models.customers import Customer
    from app.services.customer_service import compute_kyc_completion, determine_kyc_level

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    doc = CustomerDoc(client_id=customer_id, **data.model_dump())
    db.add(doc)
    db.flush()

    # Recalcule le KYC après ajout du document
    completion = compute_kyc_completion(customer)
    customer.kyc_completion = completion
    customer.kyc_level = determine_kyc_level(completion)

    db.commit()
    db.refresh(doc)

    log_action(db, str(current_user.id), "CREATE_DOCUMENT",
               client_id=str(customer_id))
    return doc