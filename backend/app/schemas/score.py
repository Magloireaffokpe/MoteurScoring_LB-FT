"""
app/schemas/score.py
====================
Schémas Pydantic pour le module Scoring LBC/FT — RiskGuard.

Conforme au contrat API v1.0 (section 5 — Endpoints Scoring).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class ScoringRequest(BaseModel):
    """Corps de la requête POST /api/scoring et POST /api/scoring/rescore."""

    customer_id: UUID = Field(
        ...,
        description="UUID du client à scorer",
        example="550e8400-e29b-41d4-a716-446655440000",
    )


# ---------------------------------------------------------------------------
# Response — détail par critère
# ---------------------------------------------------------------------------

class DetailJson(BaseModel):
    """Contributions absolues (note × poids) pour chaque critère."""

    C1: float = Field(..., description="Profil professionnel (contribution)")
    C2: float = Field(..., description="Zone géographique (contribution)")
    C3: float = Field(..., description="Historique transactionnel (contribution)")
    C4: float = Field(..., description="Ancienneté & fidélité (contribution)")
    C5: float = Field(..., description="Statut PEP (contribution)")
    C6: float = Field(..., description="Cohérence KYC (contribution)")


# ---------------------------------------------------------------------------
# Response — score complet
# ---------------------------------------------------------------------------

class ScoreResponse(BaseModel):
    """Réponse complète d'un calcul ou recalcul de score."""

    id: UUID = Field(..., description="UUID du score enregistré")
    customer_id: UUID = Field(..., description="UUID du client")
    global_score: int = Field(..., ge=0, le=100, description="Score global 0-100")
    risk_category: str = Field(
        ...,
        description="Catégorie de risque : FAIBLE | MOYEN | ÉLEVÉ",
        example="MOYEN",
    )
    detail_json: DetailJson
    is_current: bool = Field(default=True)
    scored_by: str = Field(default="AUTOMATED")
    scored_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Response — liste historique (GET /api/customers/{id}/scores)
# ---------------------------------------------------------------------------

class ScoreSummary(BaseModel):
    """Résumé d'un score pour la liste historique."""

    id: UUID
    global_score: int
    risk_category: str
    is_current: bool
    scored_at: datetime

    class Config:
        from_attributes = True


class ScoreListResponse(BaseModel):
    """Réponse paginée pour l'historique des scores d'un client."""

    items: list[ScoreSummary]
    total: int
