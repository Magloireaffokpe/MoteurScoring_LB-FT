import logging
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_compliance_or_admin
from app.models.transactions import Transaction
from app.models.customer_accounts import CustomerAccount
from app.models.scores import Score
from app.schemas.transaction import TransactionCreateResponse, TransactionCreate
from app.schemas.common import PaginatedResponse
from app.schemas.score import _normalize_risk_category
from app.services.audit_service import log_action, ACTION_SCORING_RESCORE
from app.services.scoring import ScoringEngine, _naive_utc_now
from app.services.alert_service import (
    create_score_alert_if_needed,
    create_pep_alert_if_needed,
    create_smurfing_alert_if_needed,
    create_kyc_alert_if_needed,
    create_if_not_open,
    ALERT_TYPE_SEUIL_DEPASSE,
)
from app.services.beneficiaire_service import check_and_alert
from app.models.customers import Customer
from app.models.settings import AppSetting

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_setting(db: Session, key: str, default: float) -> float:
    """Lit un paramètre depuis la DB AppSetting, ou retourne la valeur par défaut."""
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        return float(row.value)
    return default


@router.get("/customers/{customer_id}/transactions",
            response_model=PaginatedResponse[TransactionCreateResponse])
def get_customer_transactions(
    customer_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    days: int = Query(90, ge=1, le=365),
    type_op: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

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


@router.get("/transactions/{transaction_id}", response_model=TransactionCreateResponse)
def get_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.post("/customers/{customer_id}/transactions",
             response_model=TransactionCreateResponse, status_code=201)
def create_transaction(
    customer_id: UUID,
    data: TransactionCreate,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_compliance_or_admin)
):
    account = db.query(CustomerAccount).filter(
        CustomerAccount.id == data.compte_id,
        CustomerAccount.client_id == customer_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found for this customer")

    tx = Transaction(**data.model_dump())
    db.add(tx)
    db.flush()

    # ── Mise à jour automatique du solde courant ─────────────────────────
    montant = Decimal(str(data.montant)) if data.montant else Decimal("0")
    current = account.solde_moyen or Decimal("0")
    account.solde_moyen = (
        current + montant if data.type_op == "DEPOT" else current - montant
    )

    log_action(db, str(current_user.id), "CREATE_TRANSACTION",
               client_id=str(customer_id))

    # ── Auto-rescore ──────────────────────────────────────────────────────
    new_score_global = None
    new_score_category = None
    try:
        engine = ScoringEngine(db)
        result = engine.calculate_score(customer_id)

        db.query(Score).filter(
            Score.client_id == customer_id,
            Score.is_current == True,
        ).update({"is_current": False}, synchronize_session=False)

        score = Score(
            client_id=customer_id,
            score_global=result["global_score"],
            detail_json=result["detail_json"],
            categorie=result["risk_category"],
            is_current=True,
            calcule_par=str(current_user.id),
        )
        db.add(score)
        db.flush()

        new_score_global = result["global_score"]
        new_score_category = _normalize_risk_category(result["risk_category"])

        create_score_alert_if_needed(db, customer_id, result["global_score"], skip_if_open=True, score_id=score.id)
        create_pep_alert_if_needed(db, customer_id, result["c5_score"], skip_if_open=True, score_id=score.id)
        if result["smurfing_detected"]:
            create_smurfing_alert_if_needed(db, customer_id, skip_if_open=True, tx_ids=[tx.id])
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if customer:
            create_kyc_alert_if_needed(db, customer_id, customer.kyc_completion or 0, skip_if_open=True)

        log_action(db, str(current_user.id), ACTION_SCORING_RESCORE,
                   resource_type="customer", resource_id=str(customer_id),
                   ip_address=http_request.client.host if http_request.client else None)
    except Exception as exc:
        logger.error("Auto-rescore failed after transaction: %s", exc)

    # ── Détection seuil monétaire (toutes opérations) ────────────────────
    fenetre = int(_get_setting(db, "FENETRE_CUMUL_JOURS", 30))
    seuil_global = _get_setting(db, "SEUIL_MONETAIRE", 10_000_000)
    seuil_especes = _get_setting(db, "SEUIL_ESPECES", 3_000_000)

    cutoff_30d = _naive_utc_now() - timedelta(days=fenetre)

    cumul_global = (
        db.query(func.coalesce(func.sum(Transaction.montant), 0))
        .join(CustomerAccount, Transaction.compte_id == CustomerAccount.id)
        .filter(
            CustomerAccount.client_id == customer_id,
            Transaction.date_op >= cutoff_30d,
        )
        .scalar() or 0
    )

    if float(cumul_global) >= seuil_global:
        create_if_not_open(
            db=db,
            client_id=customer_id,
            type_alerte=ALERT_TYPE_SEUIL_DEPASSE,
            decision=f"Cumul 30j toutes opérations : {float(cumul_global):,.0f} XOF (seuil {seuil_global:,.0f} XOF)",
        )

    # ── Seuil espèces (DEPOT via GUICHET ou ATM) ─────────────────────────
    cumul_especes = (
        db.query(func.coalesce(func.sum(Transaction.montant), 0))
        .join(CustomerAccount, Transaction.compte_id == CustomerAccount.id)
        .filter(
            CustomerAccount.client_id == customer_id,
            Transaction.date_op >= cutoff_30d,
            Transaction.type_op == "DEPOT",
            Transaction.canal.in_(["GUICHET", "ATM"]),
        )
        .scalar() or 0
    )

    if float(cumul_especes) >= seuil_especes:
        create_if_not_open(
            db=db,
            client_id=customer_id,
            type_alerte=ALERT_TYPE_SEUIL_DEPASSE,
            decision=f"Cumul 30j espèces (GUICHET/ATM) : {float(cumul_especes):,.0f} XOF (seuil {seuil_especes:,.0f} XOF)",
        )

    # ── Détection bénéficiaire groupé (VIREMENT / PAIEMENT) ──────────────
    if tx.type_op in ("VIREMENT", "PAIEMENT") and tx.destination:
        check_and_alert(tx, db)

    db.commit()
    db.refresh(tx)

    resp = TransactionCreateResponse.model_validate(tx)
    resp.new_score_global = new_score_global
    resp.new_score_category = new_score_category
    return resp
