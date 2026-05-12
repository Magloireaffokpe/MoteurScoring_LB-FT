"""
app/routers/scoring.py
=======================
Endpoints REST pour le module Scoring LBC/FT — RiskGuard.

Routes :
  POST /api/scoring            → calcul initial
  POST /api/scoring/rescore    → recalcul manuel
  GET  /api/scores/{score_id}  → détails d'un score
  GET  /api/customers/{customer_id}/scores → historique

Contrat API v1.0 — mai 2026
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.models.users import User
from app.models.scores import Score
from app.models.customers import Customer
from app.schemas.score import (
    ScoringRequest,
    ScoreResponse,
    ScoreSummary,
    ScoreListResponse,
    DetailJson,
)
from app.services.scoring import ScoringEngine
from app.services import alert_service, audit_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Scoring"])


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _mark_previous_scores_as_not_current(db: Session, customer_id: UUID) -> None:
    """Marque tous les anciens scores du client comme non courants."""
    db.query(Score).filter(
        Score.client_id == customer_id,
        Score.is_current == True,  # noqa: E712
    ).update({"is_current": False}, synchronize_session=False)


def _build_score_response(score: Score) -> ScoreResponse:
    """Construit un ScoreResponse à partir d'un objet Score ORM."""
    raw_detail = score.detail_json or {}
    return ScoreResponse(
        id=score.id,
        customer_id=score.client_id,
        global_score=score.score_global,
        risk_category=score.categorie,
        detail_json=DetailJson(
            C1=raw_detail.get("C1", 0.0),
            C2=raw_detail.get("C2", 0.0),
            C3=raw_detail.get("C3", 0.0),
            C4=raw_detail.get("C4", 0.0),
            C5=raw_detail.get("C5", 0.0),
            C6=raw_detail.get("C6", 0.0),
        ),
        is_current=score.is_current,
        scored_by=score.calcule_par or "AUTOMATED",
        scored_at=score.date_calcul,
    )


def _run_scoring(
    request: ScoringRequest,
    db: Session,
    current_user: User,
    action: str,
    skip_alert_if_open: bool = False,
    http_request: Request | None = None,
) -> ScoreResponse:
    """
    Logique commune pour /api/scoring et /api/scoring/rescore.

    :param request: Corps de la requête contenant customer_id.
    :param db: Session DB.
    :param current_user: Utilisateur authentifié.
    :param action: Code action pour l'audit ('SCORING_CALCULATE' | 'SCORING_RESCORE').
    :param skip_alert_if_open: Si True, ne recréé pas une alerte SCORE_ELEVE déjà ouverte.
    :param http_request: Objet Request FastAPI (pour récupérer l'IP).
    :returns: ScoreResponse conforme au contrat.
    :raises HTTPException 404: Client introuvable.
    :raises HTTPException 422: Erreur de calcul.
    """
    customer_id = request.customer_id

    # --- 1. Vérifier l'existence du client ---
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        logger.warning("Scoring — client introuvable : %s", customer_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client introuvable : {customer_id}",
        )

    # --- 2. Calculer le score ---
    try:
        engine = ScoringEngine(db)
        result = engine.calculate_score(customer_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.exception("Erreur calcul score pour client %s", customer_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erreur lors du calcul du score : {exc}",
        )

    # --- 3. Archiver l'ancien score courant ---
    _mark_previous_scores_as_not_current(db, customer_id)

    # --- 4. Persister le nouveau score ---
    new_score = Score(
        client_id=customer_id,
        score_global=result["global_score"],
        detail_json=result["detail_json"],
        categorie=result["risk_category"],
        is_current=True,
        calcule_par="AUTOMATED",
    )
    db.add(new_score)
    db.flush()  # Obtenir l'UUID sans commit total

    # --- 5. Créer une alerte si score ≥ 67 ---
    alert_service.create_score_alert_if_needed(
        db=db,
        customer_id=customer_id,
        global_score=result["global_score"],
        skip_if_open=skip_alert_if_open,
    )

    # --- 6. Journaliser ---
    ip = None
    if http_request:
        ip = http_request.client.host if http_request.client else None

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action=action,
        resource_type=audit_service.RESOURCE_CUSTOMER,
        resource_id=str(customer_id),
        ip_address=ip,
    )

    # --- 7. Commit global ---
    db.commit()
    db.refresh(new_score)

    logger.info(
        "%s — client=%s score=%s catégorie=%s",
        action, customer_id, result["global_score"], result["risk_category"],
    )

    return _build_score_response(new_score)


# ---------------------------------------------------------------------------
# POST /api/scoring — calcul initial
# ---------------------------------------------------------------------------

@router.post(
    "/api/scoring",
    response_model=ScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Calcul du score LBC/FT initial",
    description=(
        "Lance le calcul du score LBC/FT pour un client. "
        "Crée automatiquement une alerte SCORE_ELEVE si global_score ≥ 67. "
        "Rôles autorisés : admin, compliance_officer."
    ),
)
async def create_scoring(
    request: ScoringRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScoreResponse:
    """
    Calcule le score LBC/FT initial d'un client.

    - **customer_id** : UUID du client à scorer.
    """
    return _run_scoring(
        request=request,
        db=db,
        current_user=current_user,
        action=audit_service.ACTION_SCORING_CALCULATE,
        skip_alert_if_open=False,
        http_request=http_request,
    )


# ---------------------------------------------------------------------------
# POST /api/scoring/rescore — recalcul manuel
# ---------------------------------------------------------------------------

@router.post(
    "/api/scoring/rescore",
    response_model=ScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Recalcul manuel du score LBC/FT",
    description=(
        "Recalcule le score LBC/FT pour un client. "
        "N'ouvre pas de nouvelle alerte SCORE_ELEVE si une est déjà ouverte. "
        "Rôles autorisés : admin, compliance_officer."
    ),
)
async def rescore_customer(
    request: ScoringRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScoreResponse:
    """
    Recalcule le score LBC/FT d'un client (appel manuel).

    - **customer_id** : UUID du client à rescorer.
    """
    return _run_scoring(
        request=request,
        db=db,
        current_user=current_user,
        action=audit_service.ACTION_SCORING_RESCORE,
        skip_alert_if_open=True,   # Pas de doublon d'alerte
        http_request=http_request,
    )


# ---------------------------------------------------------------------------
# GET /api/scores/{score_id} — détails d'un score
# ---------------------------------------------------------------------------

@router.get(
    "/api/scores/{score_id}",
    response_model=ScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Détails d'un score particulier",
)
async def get_score(
    score_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScoreResponse:
    """
    Retourne le détail d'un score identifié par son UUID.

    - **score_id** : UUID du score.
    """
    score = db.query(Score).filter(Score.id == score_id).first()
    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Score introuvable : {score_id}",
        )
    return _build_score_response(score)


# ---------------------------------------------------------------------------
# GET /api/customers/{customer_id}/scores — historique
# ---------------------------------------------------------------------------

@router.get(
    "/api/customers/{customer_id}/scores",
    response_model=ScoreListResponse,
    status_code=status.HTTP_200_OK,
    summary="Historique des scores d'un client",
)
async def get_customer_scores(
    customer_id: UUID,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScoreListResponse:
    """
    Retourne l'historique paginé des scores d'un client.

    - **customer_id** : UUID du client.
    - **skip** : Offset de pagination (défaut 0).
    - **limit** : Nombre maximum d'items (défaut 10).
    """
    # Vérifier l'existence du client
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client introuvable : {customer_id}",
        )

    query = (
        db.query(Score)
        .filter(Score.client_id == customer_id)
        .order_by(Score.date_calcul.desc())
    )
    total = query.count()
    scores = query.offset(skip).limit(limit).all()

    items = [
        ScoreSummary(
            id=s.id,
            global_score=s.score_global,
            risk_category=s.categorie,
            is_current=s.is_current,
            scored_at=s.date_calcul,
        )
        for s in scores
    ]

    return ScoreListResponse(items=items, total=total)
