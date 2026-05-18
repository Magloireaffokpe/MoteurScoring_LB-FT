"""
app/routers/scoring.py
=======================
Endpoints REST pour le module Scoring LBC/FT — RiskGuard.

Routes :
  POST /scoring                        → calcul du score initial
  POST /scoring/rescore                → recalcul manuel (compliance officer)
  GET  /scores/{score_id}              → détails d'un score particulier
  GET  /customers/{customer_id}/scores → historique paginé des scores

Contrat API v1.0 — mai 2026

Auteur  : Dev A — AFFOKPE Magloire
Version : 1.2 — Mai 2026

Changelog v1.2 :
  [Fix 4] datetime.utcnow() → datetime.now(timezone.utc)
  [Rob-1] _build_score_response : normalisation 'ELEVE' → 'ÉLEVÉ' en sortie
           (double sécurité si une valeur brute est lue directement depuis Score.categorie)
  [Rob-2] _run_scoring : gestion explicite de l'IP client (client peut être None)
  [Rob-3] Historique : tri décroissant garanti, limit clampé à 100 max
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.customers import Customer
from app.models.scores import Score
from app.models.users import User
from app.schemas.score import (
    DetailJson,
    ScoreListResponse,
    ScoreResponse,
    ScoreSummary,
    ScoringRequest,
)
from app.services import alert_service, audit_service
from app.services.scoring import ScoringEngine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Scoring"])

# Mapping de normalisation catégorie DB → contrat API
# Protège contre toute valeur stockée sans accent en base
_CATEGORY_NORMALIZE: dict[str, str] = {
    "ELEVE":  "ÉLEVÉ",
    "ÉLEVÉ":  "ÉLEVÉ",
    "MOYEN":  "MOYEN",
    "FAIBLE": "FAIBLE",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers privés
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_category(raw: str | None) -> str:
    """
    Normalise la catégorie de risque pour garantir la conformité au contrat API.
    Gère le cas 'ELEVE' (sans accent, stocké en base par seed_db.py de Marcos)
    qui doit être retourné 'ÉLEVÉ' côté API.  [Rob-1]

    :param raw: valeur brute lue depuis Score.categorie.
    :returns: 'FAIBLE' | 'MOYEN' | 'ÉLEVÉ'
    """
    if not raw:
        return "FAIBLE"
    return _CATEGORY_NORMALIZE.get(raw.upper(), raw)


def _mark_previous_scores_as_not_current(db: Session, customer_id: UUID) -> None:
    """
    Marque tous les scores existants du client comme non courants
    avant d'insérer le nouveau score calculé.

    :param db: Session SQLAlchemy active.
    :param customer_id: UUID du client concerné.
    """
    updated = (
        db.query(Score)
        .filter(
            Score.client_id == customer_id,
            Score.is_current == True,  # noqa: E712
        )
        .update({"is_current": False}, synchronize_session=False)
    )
    if updated:
        logger.debug(
            "%d score(s) archivé(s) pour client %s", updated, customer_id
        )


def _build_score_response(score: Score) -> ScoreResponse:
    """
    Construit un ScoreResponse Pydantic à partir d'un objet Score ORM.

    Applique la normalisation de catégorie [Rob-1] pour garantir
    que 'ELEVE' (base) devient 'ÉLEVÉ' (API) même pour les scores
    anciens déjà persistés.

    :param score: instance Score ORM.
    :returns: ScoreResponse conforme au contrat API v1.0.
    """
    raw_detail = score.detail_json or {}

    return ScoreResponse(
        id=score.id,
        customer_id=score.client_id,
        global_score=score.score_global,
        risk_category=_normalize_category(score.categorie),   # [Rob-1]
        detail_json=DetailJson(
            C1=float(raw_detail.get("C1", 0.0)),
            C2=float(raw_detail.get("C2", 0.0)),
            C3=float(raw_detail.get("C3", 0.0)),
            C4=float(raw_detail.get("C4", 0.0)),
            C5=float(raw_detail.get("C5", 0.0)),
            C6=float(raw_detail.get("C6", 0.0)),
        ),
        is_current=score.is_current,
        scored_by=score.calcule_par or "AUTOMATED",
        scored_at=score.date_calcul,
    )


def _get_client_ip(http_request: Request | None) -> str | None:
    """
    Extrait l'IP du client depuis la requête FastAPI.
    Robuste si http_request ou request.client est None.  [Rob-2]

    :returns: adresse IP sous forme de string, ou None.
    """
    if http_request is None:
        return None
    if http_request.client is None:
        return None
    return http_request.client.host


def _run_scoring(
    request: ScoringRequest,
    db: Session,
    current_user: User,
    action: str,
    skip_alert_if_open: bool = False,
    http_request: Request | None = None,
) -> ScoreResponse:
    """
    Logique commune aux endpoints POST /scoring et POST /scoring/rescore.

    Enchaîne :
      1. Vérification de l'existence du client (→ 404 si absent)
      2. Calcul du score via ScoringEngine (→ 422 si erreur interne)
      3. Archivage de l'ancien score courant (is_current → False)
      4. Persistance du nouveau score en base
      5. Création éventuelle d'une alerte SCORE_ELEVE (si global_score ≥ 67)
      6. Journalisation dans audit_logs
      7. Commit et retour du ScoreResponse

    :param request:             Corps de la requête (customer_id).
    :param db:                  Session SQLAlchemy.
    :param current_user:        Utilisateur JWT authentifié.
    :param action:              Code audit ('SCORING_CALCULATE' | 'SCORING_RESCORE').
    :param skip_alert_if_open:  True → ne crée pas de doublon d'alerte SCORE_ELEVE.
    :param http_request:        Requête HTTP FastAPI (pour extraction de l'IP).
    :returns:                   ScoreResponse conforme au contrat API v1.0.
    :raises HTTPException 404:  Client introuvable.
    :raises HTTPException 422:  Erreur interne du moteur de scoring.
    """
    customer_id = request.customer_id

    # ── 1. Vérification existence client ─────────────────────────────────
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        logger.warning("Scoring — client introuvable : %s", customer_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client introuvable : {customer_id}",
        )

    # ── 2. Calcul du score ────────────────────────────────────────────────
    try:
        engine = ScoringEngine(db)
        result = engine.calculate_score(customer_id)
    except ValueError as exc:
        # Levée par ScoringEngine quand le client n'existe pas (double sécurité)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception(
            "Erreur inattendue lors du calcul du score — client %s", customer_id
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erreur lors du calcul du score : {exc}",
        )

    # ── 3. Archiver l'ancien score courant ────────────────────────────────
    _mark_previous_scores_as_not_current(db, customer_id)

    # ── 4. Persister le nouveau score ─────────────────────────────────────
    new_score = Score(
        client_id=customer_id,
        score_global=result["global_score"],
        detail_json=result["detail_json"],
        categorie=result["risk_category"],   # déjà normalisé par ScoringEngine
        is_current=True,
        calcule_par="AUTOMATED",
    )
    db.add(new_score)
    db.flush()   # obtenir l'UUID sans commit global

    # ── 5. Alerte automatique si score ÉLEVÉ ─────────────────────────────
    alert_service.create_score_alert_if_needed(
        db=db,
        customer_id=customer_id,
        global_score=result["global_score"],
        skip_if_open=skip_alert_if_open,
    )

    # ── 6. Journalisation audit ───────────────────────────────────────────
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action=action,
        resource_type=audit_service.RESOURCE_CUSTOMER,
        resource_id=str(customer_id),
        ip_address=_get_client_ip(http_request),   # [Rob-2]
    )

    # ── 7. Commit global et rafraîchissement ──────────────────────────────
    db.commit()
    db.refresh(new_score)

    logger.info(
        "%s — client=%s  score=%d  catégorie=%s",
        action,
        customer_id,
        result["global_score"],
        result["risk_category"],
    )

    return _build_score_response(new_score)


# ─────────────────────────────────────────────────────────────────────────────
# POST /scoring — calcul initial
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/scoring",
    response_model=ScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Calcul du score LBC/FT initial",
    description=(
        "Calcule le score LBC/FT d'un client selon les 6 critères pondérés (C1–C6). "
        "Crée automatiquement une alerte **SCORE_ELEVE** si `global_score ≥ 67`. "
        "Marque l'ancien score `is_current=False`. "
        "Action journalisée dans `audit_logs`. "
        "\n\nRôles autorisés : **admin**, **compliance_officer**."
    ),
    responses={
        200: {"description": "Score calculé avec succès"},
        404: {"description": "Client introuvable"},
        422: {"description": "Erreur interne du moteur de scoring"},
    },
)
async def create_scoring(
    request: ScoringRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScoreResponse:
    """
    Calcule le score LBC/FT **initial** d'un client.

    Appelé automatiquement après la création d'un client ou manuellement
    par un agent compliance.

    - **customer_id** : UUID du client à scorer (obligatoire).
    """
    return _run_scoring(
        request=request,
        db=db,
        current_user=current_user,
        action=audit_service.ACTION_SCORING_CALCULATE,
        skip_alert_if_open=False,   # scoring initial → toujours créer l'alerte
        http_request=http_request,
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /scoring/rescore — recalcul manuel
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/scoring/rescore",
    response_model=ScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Recalcul manuel du score LBC/FT",
    description=(
        "Recalcule le score LBC/FT d'un client. "
        "Ne crée **pas** de doublon d'alerte `SCORE_ELEVE` si une est déjà ouverte. "
        "Action journalisée dans `audit_logs`. "
        "\n\nRôles autorisés : **admin**, **compliance_officer**."
    ),
    responses={
        200: {"description": "Score recalculé avec succès"},
        404: {"description": "Client introuvable"},
        422: {"description": "Erreur interne du moteur de scoring"},
    },
)
async def rescore_customer(
    request: ScoringRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScoreResponse:
    """
    Recalcule le score LBC/FT d'un client à la demande d'un **compliance officer**.

    Identique à `POST /scoring` sauf que si une alerte `SCORE_ELEVE` est
    déjà ouverte pour ce client, aucun doublon n'est créé.

    - **customer_id** : UUID du client à rescorer (obligatoire).
    """
    return _run_scoring(
        request=request,
        db=db,
        current_user=current_user,
        action=audit_service.ACTION_SCORING_RESCORE,
        skip_alert_if_open=True,   # rescore → pas de doublon d'alerte
        http_request=http_request,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /scores/{score_id} — détails d'un score
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/scores/{score_id}",
    response_model=ScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Détails d'un score particulier",
    description="Retourne les détails complets d'un score identifié par son UUID.",
    responses={
        200: {"description": "Score trouvé"},
        404: {"description": "Score introuvable"},
    },
)
async def get_score(
    score_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScoreResponse:
    """
    Retourne le détail d'un score particulier avec le `detail_json` complet (C1–C6).

    - **score_id** : UUID du score à consulter.
    """
    score = db.query(Score).filter(Score.id == score_id).first()
    if not score:
        logger.debug("Score introuvable : %s", score_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Score introuvable : {score_id}",
        )
    return _build_score_response(score)


# ─────────────────────────────────────────────────────────────────────────────
# GET /customers/{customer_id}/scores — historique paginé
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/customers/{customer_id}/scores",
    response_model=ScoreListResponse,
    status_code=status.HTTP_200_OK,
    summary="Historique des scores d'un client",
    description=(
        "Retourne l'historique paginé des scores d'un client, "
        "trié du plus récent au plus ancien. "
        "Le score courant (`is_current=True`) apparaît en premier."
    ),
    responses={
        200: {"description": "Liste des scores"},
        404: {"description": "Client introuvable"},
    },
)
async def get_customer_scores(
    customer_id: UUID,
    skip: int = Query(default=0,  ge=0,   description="Offset de pagination"),
    limit: int = Query(default=10, ge=1, le=100, description="Nombre d'items (max 100)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScoreListResponse:
    """
    Retourne l'historique paginé des scores d'un client.

    - **customer_id** : UUID du client.
    - **skip**        : offset de pagination (défaut 0).
    - **limit**       : nombre d'items par page (défaut 10, max 100).  [Rob-3]
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
        .order_by(Score.date_calcul.desc())   # [Rob-3] tri décroissant garanti
    )
    total  = query.count()
    scores = query.offset(skip).limit(limit).all()

    items = [
        ScoreSummary(
            id=s.id,
            global_score=s.score_global,
            risk_category=_normalize_category(s.categorie),   # [Rob-1] normalisation
            is_current=s.is_current,
            scored_at=s.date_calcul,
        )
        for s in scores
    ]

    return ScoreListResponse(items=items, total=total)