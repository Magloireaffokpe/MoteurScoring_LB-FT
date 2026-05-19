"""
app/routers/exports.py
=======================
Endpoints d'export LBC/FT — RiskGuard (IMF béninoises)

Routes (section 7 du contrat API v1.0) :
  GET /exports/customer/{customer_id}/pdf      → Fiche client PDF
  GET /exports/transactions/{customer_id}/csv  → Transactions CSV
  GET /exports/sar/{alert_id}/pdf              → SAR PDF (CENTIF)

Authentification : JWT obligatoire (rôle compliance_officer ou admin).
Réponse         : StreamingResponse (aucune écriture disque).

Auteur  : Dev A — AFFOKPE Magloire
Version : 1.0 — Mai 2026
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.users import User
from app.models.customers import Customer
from app.services import audit_service
from app.services.export_service import (
    generate_customer_pdf,
    generate_sar_pdf,
    generate_transactions_csv,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Exports"])

# ── Rôles autorisés ───────────────────────────────────────────────────────
_ALLOWED_ROLES = {"admin", "compliance_officer"}


def _check_role(user: User) -> None:
    """
    Vérifie que l'utilisateur possède un rôle autorisé pour les exports.

    Le modèle User expose `role` comme une relation SQLAlchemy vers UserRole.
    On lit donc `user.role.name` pour obtenir le nom du rôle.

    :raises HTTPException 403: si le rôle est insuffisant.
    """
    # FIX: user.role est une relation vers l'objet UserRole (pas une string).
    # user.role_id est la FK, user.role est l'objet chargé par SQLAlchemy.
    role_name = ""
    user_role = getattr(user, "role", None)
    if user_role is not None:
        if isinstance(user_role, str):
            # Cas de compatibilité si jamais role est déjà une string
            role_name = user_role
        else:
            # Cas normal : user.role est un objet UserRole → on lit .name
            role_name = getattr(user_role, "name", "")

    if role_name not in _ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Rôle '{role_name}' insuffisant. Requis : compliance_officer ou admin.",
        )


def _today_str() -> str:
    """Retourne la date du jour au format YYYY-MM-DD."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
# GET /exports/customer/{customer_id}/pdf
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/exports/customer/{customer_id}/pdf",
    summary="Export PDF — Fiche d'évaluation client LBC/FT",
    description=(
        "Génère la fiche d'évaluation du risque LBC/FT d'un client en PDF (3 pages). "
        "Contient : en-tête institutionnel, KYC, score global, graphique contributions, "
        "historique des scores, alertes ouvertes, mention de conformité CENTIF. "
        "\n\nRôles autorisés : **admin**, **compliance_officer**."
    ),
    responses={
        200: {
            "description": "PDF généré avec succès",
            "content": {"application/pdf": {}},
        },
        403: {"description": "Rôle insuffisant"},
        404: {"description": "Client introuvable"},
        422: {"description": "Erreur de génération du PDF"},
    },
    response_class=StreamingResponse,
)
async def export_customer_pdf(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Exporte la fiche d'évaluation LBC/FT du client au format PDF.

    - **customer_id** : UUID du client à exporter.
    """
    _check_role(current_user)
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client introuvable")

    try:
        pdf_bytes = generate_customer_pdf(
            db=db,
            customer_id=customer_id,
            agent=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.exception("Erreur génération PDF client %s", customer_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erreur lors de la génération du PDF : {exc}",
        )

    # Journalisation audit (optionnelle — ne bloque pas si échoue)
    try:
        audit_service.log_action(
            db=db,
            user_id=current_user.id,
            action="EXPORT_CUSTOMER_PDF",
            resource_type="customer",
            resource_id=str(customer_id),
        )
        db.commit()
    except Exception:
        pass   # L'audit ne doit jamais bloquer l'export

    filename = f"fiche_client_{customer.nom} {customer.prenom}_{customer_id}_{_today_str()}.pdf"
    logger.info("Export PDF client — %s — agent=%s", customer_id, current_user.id)

    return StreamingResponse(
        content=iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
            "X-Generated-By": "RiskGuard",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /exports/transactions/{customer_id}/csv
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/exports/transactions/{customer_id}/csv",
    summary="Export CSV — Transactions du client",
    description=(
        "Exporte les transactions d'un client au format CSV (séparateur `;`, UTF-8). "
        "Par défaut les 90 derniers jours. Paramètre `?days=180` pour étendre la période. "
        "Colonnes : date, montant, devise, type, canal, pays origine/destination, "
        "type compte, solde moyen. "
        "\n\nRôles autorisés : **admin**, **compliance_officer**."
    ),
    responses={
        200: {
            "description": "CSV généré avec succès",
            "content": {"text/csv": {}},
        },
        403: {"description": "Rôle insuffisant"},
        404: {"description": "Client introuvable"},
    },
    response_class=StreamingResponse,
)
async def export_transactions_csv(
    customer_id: UUID,
    days: int = Query(
        default=90,
        ge=1,
        le=730,
        description="Fenêtre temporelle en jours (1–730, défaut 90)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Exporte les transactions du client au format CSV.

    - **customer_id** : UUID du client.
    - **days**        : nombre de jours à exporter (défaut 90, max 730).
    """
    _check_role(current_user)
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client introuvable")

    try:
        csv_bytes = generate_transactions_csv(
            db=db,
            customer_id=customer_id,
            days=days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.exception("Erreur génération CSV transactions client %s", customer_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erreur lors de la génération du CSV : {exc}",
        )

    # Journalisation audit
    try:
        audit_service.log_action(
            db=db,
            user_id=current_user.id,
            action="EXPORT_TRANSACTIONS_CSV",
            resource_type="customer",
            resource_id=str(customer_id),
        )
        db.commit()
    except Exception:
        pass

    filename = f"transactions_{customer.nom} {customer.prenom}_{customer_id}_{_today_str()}.csv"
    logger.info("Export CSV transactions — %s — %d jours", customer_id, days)

    return StreamingResponse(
        content=iter([csv_bytes]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(csv_bytes)),
            "X-Generated-By": "RiskGuard",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /exports/sar/{alert_id}/pdf
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/exports/sar/{alert_id}/pdf",
    summary="Export PDF — Déclaration de Soupçon SAR (CENTIF)",
    description=(
        "Génère la Déclaration de Soupçon (SAR) conforme CENTIF Bénin au format PDF. "
        "Contient : référence SAR unique, données client, détail alerte, "
        "transactions suspectes des 90 derniers jours, motif, action recommandée, "
        "et signature de l'agent. "
        "\n\nRôles autorisés : **admin**, **compliance_officer**."
    ),
    responses={
        200: {
            "description": "SAR PDF généré avec succès",
            "content": {"application/pdf": {}},
        },
        403: {"description": "Rôle insuffisant"},
        404: {"description": "Alerte introuvable"},
        422: {"description": "Erreur de génération du SAR"},
    },
    response_class=StreamingResponse,
)
async def export_sar_pdf(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Génère la Déclaration de Soupçon (SAR) pour une alerte donnée.

    - **alert_id** : UUID de l'alerte LBC/FT déclenchant la déclaration.
    """
    _check_role(current_user)

    try:
        pdf_bytes = generate_sar_pdf(
            db=db,
            alert_id=alert_id,
            agent=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.exception("Erreur génération SAR PDF alerte %s", alert_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erreur lors de la génération du SAR : {exc}",
        )

    # Journalisation audit
    try:
        audit_service.log_action(
            db=db,
            user_id=current_user.id,
            action="EXPORT_SAR_PDF",
            resource_type="alert",
            resource_id=str(alert_id),
        )
        db.commit()
    except Exception:
        pass

    filename = f"SAR_{str(alert_id)[:8].upper()}_{_today_str()}.pdf"
    logger.info("Export SAR PDF — alerte=%s — agent=%s", alert_id, current_user.id)

    return StreamingResponse(
        content=iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
            "X-Generated-By": "RiskGuard",
            "X-SAR-Reference": f"SAR-{str(alert_id).upper()[:8]}",
        },
    )