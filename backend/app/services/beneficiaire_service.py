"""
services/beneficiaire_service.py
=================================
Détection des transferts de groupe vers un bénéficiaire commun.
Appelé uniquement depuis routers/transactions.py à la création
d'un VIREMENT ou PAIEMENT avec destination renseignée.

LIMITE DOCUMENTÉE :
  La normalisation du nom de bénéficiaire (minuscule, strip)
  ne couvre pas les homonymes ni les variantes orthographiques
  (ex: "OUEDRAOGO Fatima" ≠ "F. OUEDRAOGO").
  En production AML réelle, un algorithme de similarité textuelle
  (Levenshtein, Soundex) ou une liste de bénéficiaires enregistrés
  serait nécessaire. Cette limitation est intentionnelle pour le
  périmètre de la soutenance.
"""

from __future__ import annotations

import logging
import unicodedata
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import (
    BENEFICIAIRE_MIN_CLIENTS,
    BENEFICIAIRE_MIN_TRANSACTIONS,
    BENEFICIAIRE_MIN_MONTANT,
    FENETRE_CUMUL_JOURS,
)
from app.models.customer_accounts import CustomerAccount
from app.models.transactions import Transaction
from app.services.alert_service import (
    ALERT_TYPE_BENEFICIAIRE_GROUPEMENT,
    create_if_not_open,
)
from app.services.scoring import _naive_utc_now

logger = logging.getLogger(__name__)


import re

def _normalize(text: str) -> str:
    """Normalise un nom : majuscule, sans accents, sans espaces multiples, strip."""
    text = text.strip().upper()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


def check_and_alert(transaction: Transaction, db: Session) -> None:
    """
    Vérifie si le bénéficiaire de ce virement est commun à plusieurs clients.
    Crée une alerte BENEFICIAIRE_GROUPEMENT si les seuils sont dépassés.
    """
    if not transaction.destination:
        return

    dest_normalized = _normalize(transaction.destination)
    if not dest_normalized:
        return

    cutoff = _naive_utc_now() - timedelta(days=FENETRE_CUMUL_JOURS)

    base_filter = [
        Transaction.destination.ilike(f"%{dest_normalized}%"),
        Transaction.date_op >= cutoff,
        Transaction.type_op.in_(["VIREMENT", "PAIEMENT"]),
    ]

    nb_transactions = (
        db.query(func.count(Transaction.id))
        .join(CustomerAccount, Transaction.compte_id == CustomerAccount.id)
        .filter(*base_filter)
        .scalar() or 0
    )

    nb_clients = (
        db.query(func.count(CustomerAccount.client_id.distinct()))
        .join(Transaction, Transaction.compte_id == CustomerAccount.id)
        .filter(*base_filter)
        .scalar() or 0
    )

    total_montant = float(
        db.query(func.coalesce(func.sum(Transaction.montant), 0))
        .join(CustomerAccount, Transaction.compte_id == CustomerAccount.id)
        .filter(*base_filter)
        .scalar() or 0
    )

    if (
        nb_clients >= BENEFICIAIRE_MIN_CLIENTS
        or nb_transactions >= BENEFICIAIRE_MIN_TRANSACTIONS
        or total_montant >= BENEFICIAIRE_MIN_MONTANT
    ):
        account = db.query(CustomerAccount).filter(
            CustomerAccount.id == transaction.compte_id
        ).first()
        if not account:
            return

        decision = (
            f"Bénéficiaire suspect : {dest_normalized} | "
            f"{nb_clients} clients distincts | "
            f"{nb_transactions} transactions | "
            f"{total_montant:,.0f} XOF sur {FENETRE_CUMUL_JOURS}j"
        )
        create_if_not_open(
            db=db,
            client_id=account.client_id,
            type_alerte=ALERT_TYPE_BENEFICIAIRE_GROUPEMENT,
            decision=decision,
        )
        logger.warning(
            "Alerte BENEFICIAIRE_GROUPEMENT — client=%s bénéf=%s %d clients %d tx %.0f XOF",
            account.client_id, dest_normalized, nb_clients, nb_transactions, total_montant,
        )
