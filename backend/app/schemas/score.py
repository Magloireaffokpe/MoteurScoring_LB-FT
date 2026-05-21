"""
app/schemas/score.py
====================
Schémas Pydantic pour le module Scoring LBC/FT — RiskGuard.

Conforme au contrat API v1.0 (section 5 — Endpoints Scoring).

Auteur  : Dev A — AFFOKPE Magloire
Version : 1.2 — Mai 2026

Changelog v1.2 :
  [Fix 2] ScoreResponse.risk_category : validateur @field_validator qui normalise
           'ELEVE' → 'ÉLEVÉ' au niveau Pydantic (troisième ligne de défense).
  [Fix 4] scored_at : déclaré avec datetime (supporte naive et aware UTC).
  [Rob-1] DetailJson : tous les champs float avec ge=0.0 (jamais négatif).
  [Rob-2] ScoreSummary : même validateur risk_category pour l'historique.
  [Doc]   Docstrings complètes sur chaque classe et champ.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Constantes partagées
# ─────────────────────────────────────────────────────────────────────────────

# Valeurs autorisées pour risk_category (contrat API v1.0)
RiskCategoryType = Literal["FAIBLE", "MOYEN", "ÉLEVÉ"]

# Table de normalisation : valeurs brutes DB → valeurs contrat API
_CATEGORY_MAP: dict[str, str] = {
    "ELEVE":  "ÉLEVÉ",
    "ÉLEVÉ":  "ÉLEVÉ",
    "MOYEN":  "MOYEN",
    "FAIBLE": "FAIBLE",
}


def _normalize_risk_category(value: str) -> str:
    """
    Normalise la catégorie de risque pour la conformité au contrat API v1.0.

    Transforme 'ELEVE' (sans accent, stocké en base par seed_db.py)
    en 'ÉLEVÉ' (avec accent, exigé par le contrat).

    :param value: valeur brute (depuis DB ou moteur de scoring).
    :returns: valeur normalisée conformément au contrat.
    :raises ValueError: si la valeur n'est pas reconnue.
    """
    normalized = _CATEGORY_MAP.get((value or "").upper())
    if normalized is None:
        raise ValueError(
            f"risk_category invalide : '{value}'. "
            f"Valeurs acceptées : {list(_CATEGORY_MAP.values())}"
        )
    return normalized


# ─────────────────────────────────────────────────────────────────────────────
# Request
# ─────────────────────────────────────────────────────────────────────────────

class ScoringRequest(BaseModel):
    """
    Corps de la requête pour POST /api/scoring et POST /api/scoring/rescore.

    Exemple ::

        { "customer_id": "550e8400-e29b-41d4-a716-446655440000" }
    """

    customer_id: UUID = Field(
        ...,
        description="UUID du client à scorer",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sous-schéma : détail par critère
# ─────────────────────────────────────────────────────────────────────────────

class DetailJson(BaseModel):
    """
    Contributions absolues de chaque critère au score global.

    Chaque valeur = note_brute (0–100) × poids_normalisé.
    La somme des 6 contributions est égale à `global_score` (à l'arrondi près).

    Exemple pour un client à risque moyen ::

        { "C1": 9.0, "C2": 15.0, "C3": 16.25, "C4": 5.5, "C5": 0.0, "C6": 4.0 }
        → global_score = 50 (somme arrondie)
    """

    C1: float = Field(
        ..., ge=0.0,
        description="Profil professionnel — contribution au score global",
    )
    C2: float = Field(
        ..., ge=0.0,
        description="Zone géographique — contribution au score global",
    )
    C3: float = Field(
        ..., ge=0.0,
        description="Historique transactionnel — contribution au score global",
    )
    C4: float = Field(
        ..., ge=0.0,
        description="Ancienneté & fidélité — contribution au score global",
    )
    C5: float = Field(
        ..., ge=0.0,
        description="Statut PEP — contribution au score global",
    )
    C6: float = Field(
        ..., ge=0.0,
        description="Cohérence KYC — contribution au score global",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Response — score complet
# ─────────────────────────────────────────────────────────────────────────────

class ScoreResponse(BaseModel):
    """
    Réponse complète d'un calcul ou recalcul de score LBC/FT.

    Conforme à la section 5 du contrat API v1.0.

    Exemple ::

        {
            "id": "990e8400-e29b-41d4-a716-446655440004",
            "customer_id": "550e8400-e29b-41d4-a716-446655440000",
            "global_score": 48,
            "risk_category": "MOYEN",
            "detail_json": { "C1": 9.0, "C2": 15.0, "C3": 16.25,
                             "C4": 5.5, "C5": 0.0, "C6": 4.0 },
            "is_current": true,
            "scored_by": "AUTOMATED",
            "scored_at": "2026-05-06T08:20:00Z"
        }
    """

    id: UUID = Field(
        ...,
        description="UUID du score enregistré en base",
    )
    customer_id: UUID = Field(
        ..., alias="client_id",
        description="UUID du client scoré",
    )
    global_score: int = Field(
        ..., alias="score_global", ge=0, le=100,
        description="Score global de risque LBC/FT (0 = minimal, 100 = maximal)",
    )
    risk_category: str = Field(
        ..., alias="categorie",
        description="Catégorie de risque normalisée : FAIBLE | MOYEN | ÉLEVÉ",
        examples=["FAIBLE", "MOYEN", "ÉLEVÉ"],
    )
    detail_json: DetailJson = Field(
        ...,
        description="Contributions absolues de chaque critère (C1 à C6)",
    )
    is_current: bool = Field(
        default=True,
        description="True si ce score est le score courant du client",
    )
    scored_by: str = Field(
        default="AUTOMATED", alias="calcule_par",
        description="Identifiant du déclencheur : 'AUTOMATED' ou UUID utilisateur",
    )
    scored_at: datetime = Field(
        ..., alias="date_calcul",
        description="Date et heure du calcul (ISO 8601)",
    )

    # [Fix 2] — normalisation risk_category au niveau Pydantic
    @field_validator("risk_category", mode="before")
    @classmethod
    def normalize_risk_category(cls, value: str) -> str:
        return _normalize_risk_category(value)

    model_config = {"from_attributes": True, "populate_by_name": True}


# ─────────────────────────────────────────────────────────────────────────────
# Response — résumé pour listes paginées
# ─────────────────────────────────────────────────────────────────────────────

class ScoreSummary(BaseModel):
    """
    Résumé d'un score pour l'historique paginé.

    Utilisé dans GET /api/customers/{customer_id}/scores.
    Ne contient pas le `detail_json` pour alléger la réponse.
    """

    id: UUID = Field(..., description="UUID du score")
    global_score: int = Field(..., alias="score_global", ge=0, le=100, description="Score global 0–100")
    risk_category: str = Field(
        ..., alias="categorie",
        description="Catégorie de risque : FAIBLE | MOYEN | ÉLEVÉ",
    )
    is_current: bool = Field(
        ...,
        description="True si ce score est le score courant du client",
    )
    scored_at: datetime = Field(..., alias="date_calcul", description="Date et heure du calcul")

    @field_validator("risk_category", mode="before")
    @classmethod
    def normalize_risk_category(cls, value: str) -> str:
        return _normalize_risk_category(value)

    model_config = {"from_attributes": True, "populate_by_name": True}


# ─────────────────────────────────────────────────────────────────────────────
# Response — liste paginée
# ─────────────────────────────────────────────────────────────────────────────

class ScoreListResponse(BaseModel):
    """
    Réponse paginée pour GET /api/customers/{customer_id}/scores.

    Exemple ::

        {
            "items": [
                {
                    "id": "990e8400-...",
                    "global_score": 48,
                    "risk_category": "MOYEN",
                    "is_current": true,
                    "scored_at": "2026-05-06T08:20:00Z"
                }
            ],
            "total": 1
        }
    """

    items: list[ScoreSummary] = Field(
        ...,
        description="Liste des scores pour la page courante",
    )
    total: int = Field(
        ..., ge=0,
        description="Nombre total de scores pour ce client (toutes pages)",
    )


class RescoreAllResponse(BaseModel):
    """
    Réponse renvoyée après un recalcul global de tous les scores de risque.
    """
    rescored: int = Field(
        ..., ge=0,
        description="Nombre de clients recalculés avec succès",
    )
    critical: int = Field(
        ..., ge=0,
        description="Nombre de clients ayant atteint le seuil critique (score >= 67)",
    )