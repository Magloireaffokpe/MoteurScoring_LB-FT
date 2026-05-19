from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.models.transactions import Transaction
from app.models.customer_accounts import CustomerAccount
from app.schemas.transaction import TransactionResponse, TransactionCreate
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("/customers/{customer_id}/transactions",
            response_model=PaginatedResponse[TransactionResponse])
def get_customer_transactions(
    customer_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    days: int = Query(90, ge=1, le=365),  # fenêtre temporelle
    type_op: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Transactions d'un client sur une fenêtre temporelle.
    Par défaut : 90 derniers jours (utilisé par ScoringEngine C3).
    """
    since = datetime.utcnow() - timedelta(days=days)

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


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Détail d'une transaction."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.post("/customers/{customer_id}/transactions", response_model=TransactionResponse)
def create_customer_transaction(
    customer_id: UUID,
    transaction_in: TransactionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Crée une nouvelle transaction pour un client et déclenche le recalcul du score.
    """
    # Vérifie que le compte appartient bien au client
    compte = db.query(CustomerAccount).filter(
        CustomerAccount.id == transaction_in.compte_id,
        CustomerAccount.client_id == customer_id
    ).first()
    if not compte:
        raise HTTPException(
            status_code=404,
            detail="Account not found or does not belong to this customer"
        )

    # Crée la transaction
    db_tx = Transaction(
        compte_id=transaction_in.compte_id,
        montant=transaction_in.montant,
        devise=transaction_in.devise,
        type_op=transaction_in.type_op,
        canal=transaction_in.canal,
        origine=transaction_in.origine,
        destination=transaction_in.destination,
        origine_pays_id=transaction_in.origine_pays_id,
        destination_pays_id=transaction_in.destination_pays_id,
    )
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)

    # Recalculer le score LBC/FT du client suite à la nouvelle transaction
    try:
        from app.services.scoring import ScoringEngine
        from app.routers.scoring import _mark_previous_scores_as_not_current
        from app.models.score import Score
        from app.services import alert_service

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer_id)

        # Archiver l'ancien score courant
        _mark_previous_scores_as_not_current(db, customer_id)

        # Persister le nouveau score
        new_score = Score(
            client_id=customer_id,
            score_global=result["global_score"],
            detail_json=result["detail_json"],
            categorie=result["risk_category"],
            is_current=True,
            calcule_par="AUTOMATED",
        )
        db.add(new_score)
        db.commit()

        # Alerte automatique si score élevé
        alert_service.create_score_alert_if_needed(
            db=db,
            customer_id=customer_id,
            global_score=result["global_score"],
            skip_if_open=True,
        )
        db.commit()
    except Exception:
        # En cas d'erreur de scoring, on ne bloque pas la transaction elle-même
        pass

    return db_tx