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
Version : 1.3 — Mai 2026

Changelog v1.3 :
  [Int-1] _run_scoring        : intégration des alertes fines issues
                                des champs étendus retournés par ScoringEngine v1.3 :
                                  • create_pep_alert_if_needed    (c5_score)
                                  • create_smurfing_alert_if_needed (smurfing_detected)
  [Int-2] rescore_all_customers : même intégration pour le rescoring global
  [Int-3] Imports alert_service : ajout des fonctions d'alerte fine (imports additifs,
                                  rien de supprimé — non-breaking)

Changelog v1.2 (inchangé) :
  [Fix 4] datetime.utcnow() → datetime.now(timezone.utc)
  [Rob-1] _build_score_response : normalisation 'ELEVE' → 'ÉLEVÉ' en sortie
  [Rob-2] _run_scoring : gestion explicite de l'IP client (client peut être None)
  [Rob-3] Historique : tri décroissant garanti, limit clampé à 100 max
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_compliance_or_admin
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
    RescoreAllResponse,
    _normalize_risk_category,
)
from app.services import audit_service
from app.services.alert_service import (
    create_score_alert_if_needed,
    create_pep_alert_if_needed,
    create_smurfing_alert_if_needed,
)
from app.services.scoring import ScoringEngine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Scoring"])



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
    try:
        return _normalize_risk_category(raw)
    except ValueError:
        return raw


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
        logger.debug("%d score(s) archivé(s) pour client %s", updated, customer_id)


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
        risk_category=_normalize_category(score.categorie),  # [Rob-1]
        detail_json=DetailJson(
            C1=float(raw_detail.get("C1", 0.0)),
            C1_raw=float(raw_detail.get("C1_raw", 0.0)),
            C2=float(raw_detail.get("C2", 0.0)),
            C2_raw=float(raw_detail.get("C2_raw", 0.0)),
            C3=float(raw_detail.get("C3", 0.0)),
            C3_raw=float(raw_detail.get("C3_raw", 0.0)),
            C4=float(raw_detail.get("C4", 0.0)),
            C4_raw=float(raw_detail.get("C4_raw", 0.0)),
            C5=float(raw_detail.get("C5", 0.0)),
            C5_raw=float(raw_detail.get("C5_raw", 0.0)),
            C6=float(raw_detail.get("C6", 0.0)),
            C6_raw=float(raw_detail.get("C6_raw", 0.0)),
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


def _create_fine_alerts(
    db: Session,
    customer_id: UUID,
    result: dict,
    skip_if_open: bool,
) -> None:
    """
    Crée les alertes fines issues des champs étendus retournés par ScoringEngine v1.3.
    [Int-1, Int-2]

    Appelé systématiquement après create_score_alert_if_needed dans tous les
    points de scoring (scoring initial, rescore unitaire, rescore global).

    Alertes créées :
      • PEP_DETECTE  — selon la note brute C5 (0 | 50 | 100)
      • SMURFING                 — si smurfing_detected == True

    :param db:            Session SQLAlchemy active.
    :param customer_id:   UUID du client scoré.
    :param result:        Dict retourné par ScoringEngine.calculate_score().
    :param skip_if_open:  Passer True pour éviter les doublons (rescore),
                          False pour scoring initial.
    """
    # Alerte PEP — différencie actif (100) et ancien (50)
    create_pep_alert_if_needed(
        db=db,
        customer_id=customer_id,
        c5_score=result["c5_score"],
        skip_if_open=skip_if_open,
    )

    # Alerte smurfing dédiée — filtrable indépendamment de SCORE_ELEVE
    if result["smurfing_detected"]:
        create_smurfing_alert_if_needed(
            db=db,
            customer_id=customer_id,
            skip_if_open=skip_if_open,
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
    Logique commune aux endpoints POST /scoring et POST /scoring/rescore.

    Enchaîne :
      1. Vérification de l'existence du client (→ 404 si absent)
      2. Calcul du score via ScoringEngine (→ 422 si erreur interne)
      3. Archivage de l'ancien score courant (is_current → False)
      4. Persistance du nouveau score en base
      5. Création éventuelle d'une alerte SCORE_ELEVE (si global_score ≥ 67)
      6. Création des alertes fines PEP / smurfing / card testing [Int-1]
      7. Journalisation dans audit_logs
      8. Commit et retour du ScoreResponse

    :param request:             Corps de la requête (customer_id).
    :param db:                  Session SQLAlchemy.
    :param current_user:        Utilisateur JWT authentifié.
    :param action:              Code audit ('SCORING_CALCULATE' | 'SCORING_RESCORE').
    :param skip_alert_if_open:  True → ne crée pas de doublon d'alertes.
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
        categorie=result["risk_category"],  # déjà normalisé par ScoringEngine
        is_current=True,
        calcule_par="AUTOMATED",
    )
    db.add(new_score)
    db.flush()  # obtenir l'UUID sans commit global

    # ── 5. Alerte générique SCORE_ELEVE ───────────────────────────────────
    create_score_alert_if_needed(
        db=db,
        customer_id=customer_id,
        global_score=result["global_score"],
        skip_if_open=skip_alert_if_open,
    )

    # ── 6. Alertes fines PEP / smurfing / card testing [Int-1] ───────────
    _create_fine_alerts(
        db=db,
        customer_id=customer_id,
        result=result,
        skip_if_open=skip_alert_if_open,
    )

    # ── 7. Journalisation audit ───────────────────────────────────────────
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action=action,
        resource_type=audit_service.RESOURCE_CUSTOMER,
        resource_id=str(customer_id),
        ip_address=_get_client_ip(http_request),  # [Rob-2]
    )

    # ── 8. Commit global et rafraîchissement ──────────────────────────────
    db.commit()
    db.refresh(new_score)

    logger.info(
        "%s — client=%s  score=%d  catégorie=%s  smurfing=%s  c5=%.0f",
        action,
        customer_id,
        result["global_score"],
        result["risk_category"],
        result["smurfing_detected"],
        result["c5_score"],
    )

    return _build_score_response(new_score)


# ─────────────────────────────────────────────────────────────────────────────
# POST /scoring — calcul initial
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/scoring",
    response_model=ScoreResponse,
    response_model_by_alias=False,
    status_code=status.HTTP_200_OK,
    summary="Calcul du score LBC/FT initial",
    description=(
        "Calcule le score LBC/FT d'un client selon les 6 critères pondérés (C1–C6). "
        "Crée automatiquement une alerte **SCORE_ELEVE** si `global_score ≥ 67`. "
         "Crée également des alertes fines : **PEP_DETECTE**, **SMURFING_DETECTE** "
        "selon les signaux détectés. "
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
    current_user: User = Depends(require_compliance_or_admin),
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
        skip_alert_if_open=False,  # scoring initial → toujours créer les alertes
        http_request=http_request,
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /scoring/rescore — recalcul manuel
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/scoring/rescore",
    response_model=ScoreResponse,
    response_model_by_alias=False,
    status_code=status.HTTP_200_OK,
    summary="Recalcul manuel du score LBC/FT",
    description=(
        "Recalcule le score LBC/FT d'un client. "
        "Ne crée **pas** de doublon d'alerte si une alerte du même type est déjà ouverte. "
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
    current_user: User = Depends(require_compliance_or_admin),
) -> ScoreResponse:
    """
    Recalcule le score LBC/FT d'un client à la demande d'un **compliance officer**.

    Identique à `POST /scoring` sauf qu'aucun doublon d'alerte n'est créé
    si une alerte du même type est déjà ouverte pour ce client.

    - **customer_id** : UUID du client à rescorer (obligatoire).
    """
    return _run_scoring(
        request=request,
        db=db,
        current_user=current_user,
        action=audit_service.ACTION_SCORING_RESCORE,
        skip_alert_if_open=True,  # rescore → pas de doublon d'alertes
        http_request=http_request,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /scores/{score_id} — détails d'un score
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/scores/{score_id}",
    response_model=ScoreResponse,
    response_model_by_alias=False,
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
    response_model_by_alias=False,
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
    skip: int = Query(default=0, ge=0, description="Offset de pagination"),
    limit: int = Query(
        default=10, ge=1, le=1000, description="Nombre d'items (max 1000)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScoreListResponse:
    """
    Retourne l'historique paginé des scores d'un client.

    - **customer_id** : UUID du client.
    - **skip**        : offset de pagination (défaut 0).
    - **limit**       : nombre d'items par page (défaut 10, max 1000).  [Rob-3]
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
        .order_by(Score.date_calcul.desc())  # [Rob-3] tri décroissant garanti
    )
    total = query.count()
    scores = query.offset(skip).limit(limit).all()

    items = [
        ScoreSummary(
            id=s.id,
            global_score=s.score_global,
            risk_category=_normalize_category(s.categorie),  # [Rob-1] normalisation
            is_current=s.is_current,
            scored_at=s.date_calcul,
        )
        for s in scores
    ]

    return ScoreListResponse(items=items, total=total)


# ─────────────────────────────────────────────────────────────────────────────
# POST /scoring/rescore-all — rescoring global du portefeuille
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/scoring/rescore-all",
    response_model=RescoreAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Recalcul global de tous les scores LBC/FT",
    description=(
        "Recalcule le score LBC/FT de tous les clients du portefeuille. "
        "Ne crée pas de doublons d'alertes pour les clients déjà en cours d'examen. "
        "Les erreurs individuelles sont journalisées sans interrompre le traitement global."
    ),
)
async def rescore_all_customers(
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_compliance_or_admin),
) -> RescoreAllResponse:
    BATCH_SIZE = 20
    total = db.query(func.count(Customer.id)).scalar() or 0
    rescored_count = 0
    critical_count = 0

    # Engine partagé : _load_weights / _load_thresholds appelés 1 seule fois
    shared_engine = ScoringEngine(db)

    offset = 0
    while offset < total:
        batch = (
            db.query(Customer)
            .order_by(Customer.id)
            .offset(offset)
            .limit(BATCH_SIZE)
            .all()
        )
        if not batch:
            break

        for customer in batch:
            try:
                with db.begin_nested():
                    result = shared_engine.calculate_score(customer.id)

                    _mark_previous_scores_as_not_current(db, customer.id)

                    new_score = Score(
                        client_id=customer.id,
                        score_global=result["global_score"],
                        detail_json=result["detail_json"],
                        categorie=result["risk_category"],
                        is_current=True,
                        calcule_par="AUTOMATED",
                    )
                    db.add(new_score)
                    db.flush()

                    create_score_alert_if_needed(
                        db=db,
                        customer_id=customer.id,
                        global_score=result["global_score"],
                        skip_if_open=True,
                    )

                    _create_fine_alerts(
                        db=db,
                        customer_id=customer.id,
                        result=result,
                        skip_if_open=True,
                    )

                    rescored_count += 1
                    if result["global_score"] >= 67:
                        critical_count += 1

            except Exception as exc:
                logger.error("Erreur rescore global — client %s : %s", customer.id, exc)
                db.expire_all()
                continue

        # Commit intermédiaire : libère la transaction tous les N clients
        db.commit()

        logger.info(
            "Rescore partiel — %d/%d clients traités (%d critiques)",
            min(offset + BATCH_SIZE, total),
            total,
            critical_count,
        )

        offset += BATCH_SIZE

    # Journalisation globale de l'opération
    audit_service.log_action(
        db=db,
        user_id=str(current_user.id),
        action=audit_service.ACTION_SCORING_RESCORE_ALL,
        ip_address=_get_client_ip(http_request),
    )

    # Dernier commit pour les logs d'audit
    db.commit()

    logger.info(
        "Rescore global terminé — %d clients scorés, %d score(s) critique(s)",
        rescored_count,
        critical_count,
    )

    return RescoreAllResponse(rescored=rescored_count, critical=critical_count)
