"""
app/services/alert_service.py
==============================
Service de création et gestion des alertes LBC/FT — RiskGuard.

Auteur  : Dev A — AFFOKPE Magloire / Dev B — Marcos
Version : 1.2 — Mai 2026

Changelog v1.2 :
  [Fix A] Types d'alertes étendus :
            PEP_ACTIF    → PEP en fonction (ex-PEP_DETECTE, plus précis)
            PEP_ANCIEN   → Ancienne PEP inactive (GAFI R.12 — 5 ans post-mandat)
            CARD_TESTING → Card testing comportemental (micro-tx carte répétées)
  [Fix B] create_pep_alert_if_needed : différencie PEP active (100) et
            ancienne PEP (50) — deux alertes distinctes filtrables en dashboard
  [Fix C] create_card_testing_alert_if_needed : alerte dédiée card testing,
            évite la dilution dans les alertes SCORE_ELEVE génériques
  [Fix D] create_smurfing_alert_if_needed : déplacé ici depuis scoring.py —
            le router orchestre les alertes, pas le moteur de scoring

Compatibilité :
  - Modèle Alert (Marcos) : client_id, type_alerte, statut, decision, sar_declare
  - Aucun changement de signature des fonctions existantes (non-breaking)
  - Les nouvelles constantes de type sont ADDITIVES — rien n'est renommé côté
    code existant. PEP_DETECTE est conservé comme alias pour ne pas casser
    les tests ou le code qui l'utiliserait déjà.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.alerts import Alert

logger = logging.getLogger(__name__)

# ── Types d'alertes standardisés ─────────────────────────────────────────
# Existants (inchangés — non-breaking)
ALERT_TYPE_SCORE_ELEVE = "SCORE_ELEVE"
ALERT_TYPE_KYC_INCOMPLET = "KYC_INCOMPLET"
ALERT_TYPE_SMURFING = "SMURFING"
ALERT_TYPE_PEP_DETECTE = "PEP_DETECTE"  # conservé pour rétrocompatibilité

# Nouveaux [Fix A]
ALERT_TYPE_PEP_ACTIF = "PEP_ACTIF"  # PEP en fonction — priorité critique
ALERT_TYPE_PEP_ANCIEN = "PEP_ANCIEN"  # Ancienne PEP — surveillance GAFI 5 ans
ALERT_TYPE_CARD_TESTING = "CARD_TESTING"  # Card testing comportemental

# ── Statuts ───────────────────────────────────────────────────────────────
STATUS_OPEN = "OPEN"
STATUS_UNDER_REVIEW = "UNDER_REVIEW"
STATUS_CLOSED = "CLOSED"


# ═══════════════════════════════════════════════════════════════════════════
# Fonctions de base
# ═══════════════════════════════════════════════════════════════════════════


def create_alert(
    db: Session,
    customer_id: UUID,
    alert_type: str,
    decision: Optional[str] = None,
) -> Alert:
    """
    Crée une nouvelle alerte pour un client.
    Utilise les noms de colonnes réels du modèle Alert.

    :param db:          Session SQLAlchemy active.
    :param customer_id: UUID du client concerné.
    :param alert_type:  Type d'alerte (constantes ALERT_TYPE_*).
    :param decision:    Texte libre décrivant la raison de l'alerte.
    :returns:           Instance Alert flushée (pas encore commitée).
    """
    alert = Alert(
        client_id=customer_id,  # ← client_id (pas customer_id)
        type_alerte=alert_type,  # ← type_alerte (pas alert_type)
        statut=STATUS_OPEN,  # ← statut (pas status)
        decision=decision,
        sar_declare=False,
    )
    db.add(alert)
    db.flush()
    logger.info("Alerte créée — type=%s client=%s", alert_type, customer_id)
    return alert


def has_open_alert(db: Session, customer_id: UUID, alert_type: str) -> bool:
    """
    Vérifie s'il existe déjà une alerte ouverte du même type pour ce client.

    :param db:          Session SQLAlchemy active.
    :param customer_id: UUID du client.
    :param alert_type:  Type d'alerte à vérifier.
    :returns:           True si une alerte OPEN du même type existe déjà.
    """
    return (
        db.query(Alert)
        .filter(
            Alert.client_id == customer_id,  # ← client_id
            Alert.type_alerte == alert_type,  # ← type_alerte
            Alert.statut == STATUS_OPEN,  # ← statut
        )
        .first()
    ) is not None


# ═══════════════════════════════════════════════════════════════════════════
# Fonctions d'alertes conditionnelles
# ═══════════════════════════════════════════════════════════════════════════


def create_score_alert_if_needed(
    db: Session,
    customer_id: UUID,
    global_score: int,
    skip_if_open: bool = False,
) -> Optional[Alert]:
    """
    Crée automatiquement une alerte SCORE_ELEVE si le score global ≥ 67.
    Ne crée pas de doublon si skip_if_open=True et alerte déjà ouverte.

    :param db:           Session SQLAlchemy active.
    :param customer_id:  UUID du client.
    :param global_score: Score global calculé par ScoringEngine (0-100).
    :param skip_if_open: Si True, ne crée pas de doublon.
    :returns:            Instance Alert créée, ou None.
    """
    if global_score < 67:
        return None

    if skip_if_open and has_open_alert(db, customer_id, ALERT_TYPE_SCORE_ELEVE):
        logger.info(
            "Alerte SCORE_ELEVE déjà ouverte pour client %s — pas de doublon",
            customer_id,
        )
        return None

    return create_alert(
        db=db,
        customer_id=customer_id,
        alert_type=ALERT_TYPE_SCORE_ELEVE,
        decision=(
            f"Score de risque élevé ({global_score}/100) — "
            f"seuil ÉLEVÉ atteint (≥67)"
        ),
    )


def create_pep_alert_if_needed(
    db: Session,
    customer_id: UUID,
    c5_score: float,
    skip_if_open: bool = True,
) -> Optional[Alert]:
    """
    Crée l'alerte PEP appropriée selon la note brute C5.  [Fix B]

    Logique :
      c5_score == 100 → PEP_ACTIF  : PEP en fonction — vigilance renforcée obligatoire
      c5_score ==  50 → PEP_ANCIEN : Ancienne PEP inactive — surveillance 5 ans (GAFI R.12)
      autre           → aucune alerte

    Les deux types sont distincts et filtrables indépendamment en dashboard.

    :param db:           Session SQLAlchemy active.
    :param customer_id:  UUID du client.
    :param c5_score:     Note brute C5 retournée par ScoringEngine (0 | 50 | 100).
    :param skip_if_open: Si True, ne crée pas de doublon par type.
    :returns:            Instance Alert créée, ou None.
    """
    if c5_score == 100.0:
        alert_type = ALERT_TYPE_PEP_ACTIF
        decision = (
            "PEP active identifiée — vigilance renforcée obligatoire (GAFI R.12). "
            "Vérifier la source des fonds et justifier la relation commerciale."
        )
    elif c5_score == 50.0:
        alert_type = ALERT_TYPE_PEP_ANCIEN
        decision = (
            "Ancienne PEP identifiée — surveillance renforcée post-mandat "
            "(GAFI R.12 §14 — 5 ans minimum)."
        )
    else:
        return None

    if skip_if_open and has_open_alert(db, customer_id, alert_type):
        logger.info(
            "Alerte %s déjà ouverte pour client %s — pas de doublon",
            alert_type,
            customer_id,
        )
        return None

    return create_alert(
        db=db,
        customer_id=customer_id,
        alert_type=alert_type,
        decision=decision,
    )


def create_smurfing_alert_if_needed(
    db: Session,
    customer_id: UUID,
    skip_if_open: bool = True,
) -> Optional[Alert]:
    """
    Crée une alerte SMURFING dédiée quand le moteur de scoring a détecté
    un fractionnement probable.  [Fix D]

    Séparée de SCORE_ELEVE pour permettre aux analystes de filtrer précisément
    les dossiers de fractionnement dans leur dashboard sans les noyer dans les
    alertes de score générique.

    :param db:           Session SQLAlchemy active.
    :param customer_id:  UUID du client.
    :param skip_if_open: Si True, ne crée pas de doublon.
    :returns:            Instance Alert créée, ou None.
    """
    if skip_if_open and has_open_alert(db, customer_id, ALERT_TYPE_SMURFING):
        logger.info(
            "Alerte SMURFING déjà ouverte pour client %s — pas de doublon",
            customer_id,
        )
        return None

    return create_alert(
        db=db,
        customer_id=customer_id,
        alert_type=ALERT_TYPE_SMURFING,
        decision=(
            "Fractionnement probable détecté : transactions à montants ronds ou "
            "near-threshold (< 500 000 XOF) concentrées sur une courte période. "
            "Vérifier la cohérence avec les revenus déclarés."
        ),
    )


def create_card_testing_alert_if_needed(
    db: Session,
    customer_id: UUID,
    micro_tx_count: int,
    skip_if_open: bool = True,
) -> Optional[Alert]:
    """
    Crée une alerte CARD_TESTING si un nombre suffisant de micro-transactions
    carte ont été détectées par le moteur de scoring.  [Fix C]

    Seuil de déclenchement : micro_tx_count ≥ 5 (aligné sur _CARD_TESTING_ALERT_COUNT
    dans scoring.py). En dessous, pas d'alerte formelle mais le score C3 est déjà
    pénalisé.

    :param db:              Session SQLAlchemy active.
    :param customer_id:     UUID du client.
    :param micro_tx_count:  Nombre de micro-tx carte détectées (issu de result["card_testing_count"]).
    :param skip_if_open:    Si True, ne crée pas de doublon.
    :returns:               Instance Alert créée, ou None.
    """
    if micro_tx_count < 5:
        return None

    if skip_if_open and has_open_alert(db, customer_id, ALERT_TYPE_CARD_TESTING):
        logger.info(
            "Alerte CARD_TESTING déjà ouverte pour client %s — pas de doublon",
            customer_id,
        )
        return None

    return create_alert(
        db=db,
        customer_id=customer_id,
        alert_type=ALERT_TYPE_CARD_TESTING,
        decision=(
            f"Card testing probable — {micro_tx_count} micro-transactions carte "
            f"(≤ 1 000 XOF) détectées sur les 90 derniers jours. "
            f"Pattern typique de validation de carte volée avant fraude."
        ),
    )


def create_kyc_alert_if_needed(
    db: Session,
    customer_id: UUID,
    kyc_completion: int,
    skip_if_open: bool = True,
) -> Optional[Alert]:
    """
    Crée une alerte KYC_INCOMPLET si le taux de complétion est insuffisant.

    Seuil : kyc_completion < 40 % (niveau LOW selon determine_kyc_level).

    :param db:              Session SQLAlchemy active.
    :param customer_id:     UUID du client.
    :param kyc_completion:  Taux de complétion KYC (0-100, calculé par customer_service).
    :param skip_if_open:    Si True, ne crée pas de doublon.
    :returns:               Instance Alert créée, ou None.
    """
    if kyc_completion >= 40:
        return None

    if skip_if_open and has_open_alert(db, customer_id, ALERT_TYPE_KYC_INCOMPLET):
        logger.info(
            "Alerte KYC_INCOMPLET déjà ouverte pour client %s — pas de doublon",
            customer_id,
        )
        return None

    return create_alert(
        db=db,
        customer_id=customer_id,
        alert_type=ALERT_TYPE_KYC_INCOMPLET,
        decision=(
            f"Dossier KYC incomplet — taux de complétion : {kyc_completion}% "
            f"(seuil minimum : 40%). Relancer le client pour compléter le dossier."
        ),
    )
