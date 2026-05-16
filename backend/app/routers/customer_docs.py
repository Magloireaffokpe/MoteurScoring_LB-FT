from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.models.customer_docs import CustomerDoc
from app.schemas.customer import DocumentSchema

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
        "items": docs,
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