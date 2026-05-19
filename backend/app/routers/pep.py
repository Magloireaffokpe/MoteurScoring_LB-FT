from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.models.pep_list import PepEntry


router = APIRouter()


@router.get("/pep")
def list_pep(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Liste des PEP — filtrables par nom et statut (actif/inactif)."""
    query = db.query(PepEntry)

    if active is not None:
        query = query.filter(PepEntry.active == active)
    if search:
        query = query.filter(
            PepEntry.nom.ilike(f"%{search}%") |
            PepEntry.prenom.ilike(f"%{search}%")
        )

    total = query.count()
    items = query.order_by(PepEntry.nom).offset(skip).limit(limit).all()

    return {
        "items": [
            {
                "id": str(p.id),
                "nom": p.nom,
                "prenom": p.prenom,
                "fonction": p.fonction,
                "pays": p.pays,
                "source": p.source,
                "active": p.active,
            }
            for p in items
        ],
        "total": total
    }