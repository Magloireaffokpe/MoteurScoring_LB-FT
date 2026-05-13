from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.models.customers import Customer
from app.models.alerts import Alert
from app.models.transactions import Transaction
from app.models.scores import Score


router = APIRouter()


@router.get("/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    KPIs globaux pour le dashboard.
    Chargement < 2s requis.
    """
    total_clients = db.query(Customer).count()

    # Répartition par catégorie de risque (score courant)
    clients_by_risk = db.query(
        Score.categorie,
        func.count(Score.id)
    ).filter(Score.is_current)\
     .group_by(Score.categorie).all()

    # Répartition par kyc_level
    clients_by_kyc = db.query(
        Customer.kyc_level,
        func.count(Customer.id)
    ).group_by(Customer.kyc_level).all()

    # Alertes ouvertes
    open_alerts = db.query(Alert)\
        .filter(Alert.statut == "OPEN").count()

    # Transactions 30 derniers jours
    since_30d = datetime.utcnow() - timedelta(days=30)
    tx_count = db.query(Transaction)\
        .filter(Transaction.date_op >= since_30d).count()
    tx_total = db.query(func.sum(Transaction.montant))\
        .filter(Transaction.date_op >= since_30d).scalar() or 0

    return {
        "total_clients": total_clients,
        "clients_by_risk_category": dict(clients_by_risk),
        "clients_by_kyc_level": dict(clients_by_kyc),
        "open_alerts_count": open_alerts,
        "transactions_last_30d": {
            "count": tx_count,
            "total_amount": float(tx_total)
        }
    }


@router.get("/dashboard/alerts")
def get_dashboard_alerts(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """5 dernières alertes ouvertes — widget dashboard."""
    alerts = db.query(Alert)\
        .filter(Alert.statut == "OPEN")\
        .order_by(Alert.date_creation.desc())\
        .limit(5).all()

    return {
        "items": [
            {
                "id": str(a.id),
                "client_id": str(a.client_id),
                "type_alerte": a.type_alerte,
                "statut": a.statut,
                "sar_declare": a.sar_declare,
                "date_creation": a.date_creation,
            }
            for a in alerts
        ]
    }


@router.get("/dashboard/pep")
def get_pep_clients(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Clients actuellement marqués PEP."""
    clients = db.query(Customer)\
        .filter(Customer.statut_pep).all()

    return {
        "items": [
            {
                "id": str(c.id),
                "nom": c.nom,
                "prenom": c.prenom,
                "statut_pep": c.statut_pep,
                "kyc_level": c.kyc_level,
                "status": c.status,
            }
            for c in clients
        ],
        "total": len(clients)
    }