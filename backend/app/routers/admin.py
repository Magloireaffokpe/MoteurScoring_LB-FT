from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import csv
import io

from app.db.session import get_db
from app.auth.dependencies import require_admin
from app.models.scoring_criteria import ScoringCriteria
from app.models.risk_thresholds import RiskThreshold
from app.models.users import User
from app.models.audit_logs import AuditLog
from app.models.pep_list import PepEntry
from app.models.countries import Country
from app.schemas.common import MessageResponse
from app.services.audit_service import log_action
from app.auth.security import hash_password
from pydantic import BaseModel as PydanticBase

router = APIRouter()


#  Scoring Criteria 

@router.get("/scoring-criteria")
def get_scoring_criteria(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """Liste des 6 critères avec leurs poids."""
    items = db.query(ScoringCriteria).order_by(ScoringCriteria.code).all()
    return {"items": [
        {
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "weight": float(c.weight),
            "description": c.description,
        }
        for c in items
    ]}


@router.put("/scoring-criteria/{criteria_id}", response_model=MessageResponse)
def update_scoring_criteria(
    criteria_id: int,
    weight: float,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """
    Modifie le poids d'un critère.
    Vérifie que la somme des poids reste 100% après modification.
    """
    criteria = db.query(ScoringCriteria).filter(ScoringCriteria.id == criteria_id).first()
    if not criteria:
        raise HTTPException(status_code=404, detail="Criteria not found")

    if weight < 0 or weight > 100:
        raise HTTPException(status_code=422, detail="Weight must be between 0 and 100")

    # Vérifie que la somme des poids = 100%
    other_weights = db.query(ScoringCriteria)\
        .filter(ScoringCriteria.id != criteria_id).all()
    total = sum(float(c.weight) for c in other_weights) + weight

    if round(total, 2) != 100.00:
        raise HTTPException(
            status_code=422,
            detail=f"Sum of weights must equal 100%. Current total would be {total}%"
        )

    criteria.weight = weight
    criteria.updated_by = current_user.id
    db.commit()

    log_action(db, str(current_user.id), "UPDATE_SCORING_CRITERIA")

    return MessageResponse(message=f"Criteria {criteria.code} updated to {weight}%")


# Risk Thresholds

@router.get("/risk-thresholds")
def get_risk_thresholds(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """Liste des 3 seuils de risque."""
    items = db.query(RiskThreshold).order_by(RiskThreshold.score_min).all()
    return {"items": [
        {
            "id": t.id,
            "category": t.category,
            "score_min": t.score_min,
            "score_max": t.score_max,
            "action": t.action,
        }
        for t in items
    ]}


#  Users 

@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """Liste tous les utilisateurs."""
    users = db.query(User).all()
    return {"items": [
        {
            "id": str(u.id),
            "login": u.login,
            "role": u.role.name,
            "is_active": u.is_active,
            "last_login": u.last_login,
        }
        for u in users
    ]}


@router.put("/users/{user_id}/toggle-active", response_model=MessageResponse)
def toggle_user_active(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """Active ou désactive un utilisateur."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if str(user.id) == str(current_user.id):
        raise HTTPException(status_code=422, detail="Cannot deactivate your own account")

    user.is_active = not user.is_active
    db.commit()

    status = "activated" if user.is_active else "deactivated"
    log_action(db, str(current_user.id), f"USER_{status.upper()}")

    return MessageResponse(message=f"User {user.login} {status}")


# PEP Import 

@router.post("/pep-list/import", response_model=MessageResponse)
async def import_pep_list(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """
    Import CSV de la liste PEP.
    Format attendu : nom,prenom,fonction,pays_code,date_debut,date_fin,source
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=422, detail="File must be a CSV")

    content = await file.read()
    decoded = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))

    imported = 0
    skipped = 0

    for row in reader:
        # Vérifie doublon nom+prenom
        existing = db.query(PepEntry).filter(
            PepEntry.nom == row.get("nom", "").strip(),
            PepEntry.prenom == row.get("prenom", "").strip()
        ).first()

        if existing:
            skipped += 1
            continue

        # Résout le pays depuis code_iso
        pays_id = None
        if row.get("pays_code"):
            country = db.query(Country).filter(
                Country.code_iso == row["pays_code"].strip().upper()
            ).first()
            if country:
                pays_id = country.id

        entry = PepEntry(
            nom=row.get("nom", "").strip(),
            prenom=row.get("prenom", "").strip(),
            fonction=row.get("fonction", "").strip() or None,
            pays=pays_id,
            source=row.get("source", "").strip() or None,
        )
        db.add(entry)
        imported += 1

    db.commit()
    log_action(db, str(current_user.id), "IMPORT_PEP_LIST")

    return MessageResponse(
        message=f"Import completed: {imported} inserted, {skipped} skipped"
    )


#  Audit Logs 

@router.get("/audit-logs")
def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """Journaux d'audit filtrables."""
    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)

    total = query.count()
    items = query.order_by(AuditLog.timestamp.desc())\
                 .offset(skip).limit(limit).all()

    return {
        "items": [
            {
                "id": str(l.id),
                "user_id": str(l.user_id),
                "action": l.action,
                "client_id": str(l.client_id) if l.client_id else None,
                "timestamp": l.timestamp,
                "ip_address": l.ip_address,
            }
            for l in items
        ],
        "total": total
    }



class UserCreate(PydanticBase):
    login: str
    password: str
    role_name: str = "compliance_officer"  # 'admin' ou 'compliance_officer'

@router.post("/users", status_code=201)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """Crée un nouveau compte agent."""
    # Vérifie doublon login
    existing = db.query(User).filter(User.login == data.login).first()
    if existing:
        raise HTTPException(status_code=422, detail="Login already exists")

    # Récupère le rôle
    from app.models.user_roles import UserRole
    role = db.query(UserRole).filter(UserRole.name == data.role_name).first()
    if not role:
        raise HTTPException(status_code=422, detail=f"Role '{data.role_name}' not found")

    user = User(
        login=data.login,
        password_hash=hash_password(data.password),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(db, str(current_user.id), "CREATE_USER")

    return {
        "id": str(user.id),
        "login": user.login,
        "role": role.name,
        "is_active": user.is_active,
    }