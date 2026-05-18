"""
app/services/export_service.py
================================
Service d'export LBC/FT — RiskGuard (IMF béninoises)

Génère en mémoire (sans écriture disque) :
  - PDF fiche client complète (3 pages, design institutionnel)
  - CSV transactions (séparateur ;, UTF-8, colonnes françaises)
  - PDF déclaration de soupçon SAR (conforme CENTIF simplifié)

Couleurs logo RiskGuard :
  - Bleu marine  : #1B2A6B
  - Vert         : #1A7A3C
  - Gris clair   : #F5F5F5
  - Rouge risque : #C0392B

Auteur  : Dev A — AFFOKPE Magloire
Version : 1.0 — Mai 2026
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.shapes import Rect, String, Line, Group
from reportlab.graphics import renderPDF
from sqlalchemy.orm import Session

from app.models.alerts import Alert
from app.models.countries import Country
from app.models.customer_accounts import CustomerAccount
from app.models.customer_docs import CustomerDoc
from app.models.customers import Customer
from app.models.risk_zones import RiskZone
from app.models.scores import Score
from app.models.transactions import Transaction
from app.models.users import User

# ── Palette de couleurs (logo RiskGuard) ──────────────────────────────────
C_NAVY   = colors.HexColor("#1B2A6B")   # bleu marine principal
C_GREEN  = colors.HexColor("#1A7A3C")   # vert accent
C_RED    = colors.HexColor("#C0392B")   # rouge ÉLEVÉ
C_ORANGE = colors.HexColor("#E67E22")   # orange MOYEN
C_LGRAY  = colors.HexColor("#F5F5F5")   # fond lignes alternées
C_MGRAY  = colors.HexColor("#BDC3C7")   # bordures
C_DGRAY  = colors.HexColor("#2C3E50")   # texte principal
C_WHITE  = colors.white

# ── Styles globaux ────────────────────────────────────────────────────────
_BASE_STYLES = getSampleStyleSheet()


def _build_styles() -> dict[str, ParagraphStyle]:
    """Construit la feuille de style RiskGuard."""
    return {
        "logo": ParagraphStyle(
            "logo",
            fontName="Helvetica-Bold",
            fontSize=28,
            textColor=C_NAVY,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "logo_sub": ParagraphStyle(
            "logo_sub",
            fontName="Helvetica",
            fontSize=10,
            textColor=C_GREEN,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "imf_coords": ParagraphStyle(
            "imf_coords",
            fontName="Helvetica",
            fontSize=8,
            textColor=C_DGRAY,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "doc_title": ParagraphStyle(
            "doc_title",
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=C_WHITE,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=C_WHITE,
            alignment=TA_LEFT,
            leftIndent=6,
            spaceAfter=4,
            spaceBefore=12,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9,
            textColor=C_DGRAY,
            spaceAfter=3,
        ),
        "body_bold": ParagraphStyle(
            "body_bold",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=C_DGRAY,
            spaceAfter=3,
        ),
        "score_big": ParagraphStyle(
            "score_big",
            fontName="Helvetica-Bold",
            fontSize=48,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "score_cat": ParagraphStyle(
            "score_cat",
            fontName="Helvetica-Bold",
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica",
            fontSize=7,
            textColor=C_MGRAY,
            alignment=TA_CENTER,
        ),
        "sar_title": ParagraphStyle(
            "sar_title",
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=C_NAVY,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "sar_ref": ParagraphStyle(
            "sar_ref",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=C_RED,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "warning": ParagraphStyle(
            "warning",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=C_RED,
            spaceAfter=4,
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers communs
# ─────────────────────────────────────────────────────────────────────────────

def _score_color(score: int) -> colors.Color:
    """Retourne la couleur selon le niveau de risque."""
    if score >= 67:
        return C_RED
    elif score >= 34:
        return C_ORANGE
    return C_GREEN


def _category_label(category: str | None) -> str:
    """Normalise l'affichage de la catégorie."""
    mapping = {"ELEVE": "ÉLEVÉ", "ÉLEVÉ": "ÉLEVÉ", "MOYEN": "MOYEN", "FAIBLE": "FAIBLE"}
    return mapping.get((category or "").upper(), category or "N/A")


def _fmt_date(d: date | datetime | None) -> str:
    """Formate une date en DD/MM/YYYY."""
    if d is None:
        return "—"
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime("%d/%m/%Y")


def _fmt_datetime(d: datetime | None) -> str:
    """Formate un datetime en DD/MM/YYYY HH:MM."""
    if d is None:
        return "—"
    return d.strftime("%d/%m/%Y %H:%M")


def _fmt_montant(m) -> str:
    """Formate un montant en XOF."""
    if m is None:
        return "—"
    return f"{float(m):,.0f}".replace(",", " ") + " XOF"


def _section_table(title: str, bg: colors.Color = None) -> Table:
    """Crée un bandeau de titre de section (fond coloré)."""
    bg = bg or C_NAVY
    t = Table([[title]], colWidths=[17 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), bg),
        ("TEXTCOLOR",   (0, 0), (-1, -1), C_WHITE),
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _standard_table(headers: list[str], rows: list[list], col_widths: list[float]) -> Table:
    """Crée un tableau standard avec style RiskGuard."""
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        # En-tête
        ("BACKGROUND",    (0, 0), (-1, 0),  C_NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  C_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  8),
        ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, 0),  5),
        ("BOTTOMPADDING", (0, 0), (-1, 0),  5),
        # Corps
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("TEXTCOLOR",     (0, 1), (-1, -1), C_DGRAY),
        ("TOPPADDING",    (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        # Grille
        ("GRID",          (0, 0), (-1, -1), 0.5, C_MGRAY),
        ("LINEBELOW",     (0, 0), (-1, 0),  1.5, C_NAVY),
    ]
    # Lignes alternées
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), C_LGRAY))
    t.setStyle(TableStyle(style))
    return t


def _build_bar_chart(detail: dict[str, float]) -> Drawing:
    """
    Construit un diagramme en barres horizontal pour les contributions C1..C6.
    Retourne un objet Drawing ReportLab (robuste, pas de dépendance externe).
    """
    width, height = 400, 160
    d = Drawing(width, height)

    labels = list(detail.keys())
    values = list(detail.values())
    max_val = max(values) if values else 1
    bar_h   = 16
    bar_gap = 6
    left_margin = 45
    chart_w = width - left_margin - 20

    for i, (label, val) in enumerate(zip(labels, values)):
        y = height - 30 - i * (bar_h + bar_gap)

        # Label critère
        s = String(left_margin - 5, y + 3, label,
                   fontName="Helvetica-Bold", fontSize=8,
                   fillColor=colors.HexColor("#1B2A6B"),
                   textAnchor="end")
        d.add(s)

        # Barre de fond (grise)
        bg = Rect(left_margin, y, chart_w, bar_h,
                  fillColor=colors.HexColor("#ECF0F1"),
                  strokeColor=colors.HexColor("#BDC3C7"),
                  strokeWidth=0.5)
        d.add(bg)

        # Barre de valeur (colorée)
        bar_w = (val / max_val) * chart_w if max_val > 0 else 0
        # Couleur selon contribution
        if val >= 15:
            bar_color = C_RED
        elif val >= 8:
            bar_color = C_ORANGE
        else:
            bar_color = C_GREEN

        bar = Rect(left_margin, y, bar_w, bar_h,
                   fillColor=bar_color,
                   strokeColor=None)
        d.add(bar)

        # Valeur numérique
        val_str = f"{val:.2f}"
        sv = String(left_margin + bar_w + 4, y + 3, val_str,
                    fontName="Helvetica-Bold", fontSize=7,
                    fillColor=C_DGRAY)
        d.add(sv)

    # Titre du graphique
    title = String(width / 2, height - 12,
                   "Contributions par critère (points absolus)",
                   fontName="Helvetica-Bold", fontSize=9,
                   fillColor=C_NAVY, textAnchor="middle")
    d.add(title)

    return d


def _header_block(styles: dict, export_date: str, agent_name: str) -> list:
    """Génère le bloc d'en-tête institutionnel commun aux PDF."""
    elements = []

    # Cadre logo + coordonnées
    header_data = [[
        Paragraph("<b>Risk<font color='#1A7A3C'>Guard</font></b>", styles["logo"]),
    ]]
    header_t = Table(header_data, colWidths=[17 * cm])
    header_t.setStyle(TableStyle([
        ("BOX",         (0, 0), (-1, -1), 1.5, C_NAVY),
        ("BACKGROUND",  (0, 0), (-1, -1), colors.HexColor("#EBF5FB")),
        ("TOPPADDING",  (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(header_t)

    elements.append(Paragraph(
        "Scoring LBC/FT — Compliance Module",
        styles["logo_sub"],
    ))
    elements.append(Paragraph(
        "Microfinance Béninoise SA — 01 BP 1234 Cotonou — contact@riskguard.bj",
        styles["imf_coords"],
    ))
    elements.append(HRFlowable(width="100%", thickness=2, color=C_GREEN, spaceAfter=4))

    # Ligne date + agent
    meta = Table(
        [[
            Paragraph(f"Date d'export : <b>{export_date}</b>", styles["body"]),
            Paragraph(f"Agent : <b>{agent_name}</b>", styles["body"]),
        ]],
        colWidths=[8.5 * cm, 8.5 * cm],
    )
    meta.setStyle(TableStyle([("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    elements.append(meta)
    elements.append(Spacer(1, 6))

    return elements


def _footer_elements(styles: dict, page_label: str, agent_name: str) -> list:
    """Génère le pied de page."""
    elements = [
        Spacer(1, 12),
        HRFlowable(width="100%", thickness=0.5, color=C_MGRAY),
        Spacer(1, 4),
        Table(
            [[
                Paragraph(f"Généré par RiskGuard — {page_label}", styles["footer"]),
                Paragraph(
                    f"Agent : {agent_name} — {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC",
                    ParagraphStyle("footer_r", fontName="Helvetica", fontSize=7,
                                   textColor=C_MGRAY, alignment=TA_RIGHT),
                ),
            ]],
            colWidths=[8.5 * cm, 8.5 * cm],
        ),
    ]
    return elements


# ─────────────────────────────────────────────────────────────────────────────
# 1. PDF — Fiche client complète
# ─────────────────────────────────────────────────────────────────────────────

def generate_customer_pdf(
    db: Session,
    customer_id: UUID,
    agent: User,
) -> bytes:
    """
    Génère la fiche d'évaluation du risque LBC/FT d'un client en PDF.

    3 pages :
      Page 1 — En-tête, KYC, score global
      Page 2 — Graphique contributions, historique scores
      Page 3 — Alertes ouvertes, mentions CENTIF

    :param db: Session SQLAlchemy.
    :param customer_id: UUID du client.
    :param agent: Utilisateur ayant demandé l'export.
    :returns: bytes du PDF généré en mémoire.
    :raises ValueError: si le client est introuvable.
    """
    # ── Chargement des données ────────────────────────────────────────────
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise ValueError(f"Client introuvable : {customer_id}")

    current_score: Score | None = (
        db.query(Score)
        .filter(Score.client_id == customer_id, Score.is_current == True)  # noqa
        .first()
    )
    score_history: list[Score] = (
        db.query(Score)
        .filter(Score.client_id == customer_id)
        .order_by(Score.date_calcul.desc())
        .limit(10)
        .all()
    )
    open_alerts: list[Alert] = (
        db.query(Alert)
        .filter(Alert.client_id == customer_id)
        .order_by(Alert.date_creation.desc())
        .limit(10)
        .all()
    )
    zone: RiskZone | None = (
        db.query(RiskZone).filter(RiskZone.id == customer.zone_geo).first()
        if customer.zone_geo else None
    )

    # ── Setup document ────────────────────────────────────────────────────
    buffer  = io.BytesIO()
    styles  = _build_styles()
    export_date = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M") + " UTC"
    # FIX: User n'a pas de champ full_name — on utilise login (seul champ disponible)
    agent_name = agent.login

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.5 * cm, bottomMargin=2 * cm,
        title=f"Fiche LBC/FT — {customer.prenom} {customer.nom}",
        author="RiskGuard",
        subject="Évaluation du risque LBC/FT",
    )

    elements = []

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 1 — En-tête + KYC + Score
    # ════════════════════════════════════════════════════════════════════════

    # En-tête institutionnel
    elements += _header_block(styles, export_date, agent_name)

    # Titre document
    title_t = Table(
        [["FICHE D'ÉVALUATION DU RISQUE LBC/FT"]],
        colWidths=[17 * cm],
    )
    title_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, -1), C_WHITE),
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 13),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(title_t)

    # Identifiant client
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        f"Identifiant client : <b>{customer_id}</b>",
        styles["body"],
    ))
    elements.append(Spacer(1, 8))

    # ── Section KYC ──────────────────────────────────────────────────────
    elements.append(_section_table("📋  INFORMATIONS KYC"))
    elements.append(Spacer(1, 4))

    statut_pep_str = (
        "<font color='red'><b>OUI — Vigilance maximale</b></font>"
        if customer.statut_pep else
        "<font color='green'>Non</font>"
    )

    kyc_rows = [
        ["Nom complet",      f"{customer.prenom} {customer.nom}",
         "Date de naissance", _fmt_date(customer.date_naissance)],
        ["Téléphone",        customer.phone or "—",
         "Email",            customer.email or "—"],
        ["Profession",       customer.profession_name or "—",
         "Code métier",      customer.profession_code or "—"],
        ["Risque profession", customer.profession_risk or "—",
         "Revenus déclarés", _fmt_montant(customer.revenus_declares)],
        ["Ville",            customer.city or "—",
         "Région",           customer.region or "—"],
        ["Zone géographique", zone.name if zone else "—",
         "Niveau zone",      zone.risk_level if zone else "—"],
        ["Statut PEP",       Paragraph(statut_pep_str, styles["body"]),
         "KYC complétion",   f"{customer.kyc_completion or 0} %"],
        ["Date d'adhésion",  _fmt_datetime(customer.date_creation),
         "Statut compte",    customer.status or "—"],
    ]

    kyc_t = Table(
        kyc_rows,
        colWidths=[3.5 * cm, 5 * cm, 3.5 * cm, 5 * cm],
    )
    kyc_t.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),  # labels col 0
        ("FONTNAME",      (2, 0), (2, -1), "Helvetica-Bold"),  # labels col 2
        ("TEXTCOLOR",     (0, 0), (0, -1), C_NAVY),
        ("TEXTCOLOR",     (2, 0), (2, -1), C_NAVY),
        ("BACKGROUND",    (0, 0), (0, -1), colors.HexColor("#EBF5FB")),
        ("BACKGROUND",    (2, 0), (2, -1), colors.HexColor("#EBF5FB")),
        ("GRID",          (0, 0), (-1, -1), 0.5, C_MGRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    elements.append(kyc_t)
    elements.append(Spacer(1, 12))

    # ── Section Score ─────────────────────────────────────────────────────
    elements.append(_section_table("📊  SCORE DE RISQUE LBC/FT"))
    elements.append(Spacer(1, 6))

    if current_score:
        score_val  = current_score.score_global
        score_cat  = _category_label(current_score.categorie)
        score_col  = _score_color(score_val)
        detail     = current_score.detail_json or {}

        # Score en gros + catégorie
        score_display = Table(
            [[
                Paragraph(
                    f'<font color="{score_col.hexval()}">'
                    f'<b>{score_val}</b></font><font size="14">/100</font>',
                    styles["score_big"],
                ),
                Paragraph(
                    f'<font color="{score_col.hexval()}"><b>{score_cat}</b></font>',
                    styles["score_cat"],
                ),
            ]],
            colWidths=[6 * cm, 11 * cm],
        )
        score_display.setStyle(TableStyle([
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("BOX",           (0, 0), (-1, -1), 1.5, score_col),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(score_display)
        elements.append(Spacer(1, 6))

        elements.append(Paragraph(
            f"Calculé le : <b>{_fmt_datetime(current_score.date_calcul)}</b> — "
            f"Par : <b>{current_score.calcule_par or 'AUTOMATED'}</b>",
            styles["body"],
        ))
        elements.append(Spacer(1, 6))

        # Tableau des contributions C1..C6
        c_headers = ["Critère", "Libellé", "Contribution (pts)", "% du score"]
        c_labels = {
            "C1": "Profil professionnel",
            "C2": "Zone géographique",
            "C3": "Historique transactionnel",
            "C4": "Ancienneté & fidélité",
            "C5": "Statut PEP",
            "C6": "Cohérence KYC",
        }
        c_rows = []
        for code in ("C1", "C2", "C3", "C4", "C5", "C6"):
            val = float(detail.get(code, 0))
            pct = f"{(val / score_val * 100):.1f} %" if score_val > 0 else "—"
            c_rows.append([code, c_labels.get(code, ""), f"{val:.2f}", pct])

        elements.append(_standard_table(
            c_headers, c_rows,
            [2 * cm, 7 * cm, 4 * cm, 4 * cm],
        ))
    else:
        elements.append(Paragraph(
            "⚠ Aucun score calculé pour ce client.",
            styles["warning"],
        ))

    elements += _footer_elements(styles, "Page 1/3", agent_name)

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 2 — Graphique + Historique des scores
    # ════════════════════════════════════════════════════════════════════════
    elements.append(PageBreak())
    elements += _header_block(styles, export_date, agent_name)
    elements.append(_section_table("📈  ANALYSE GRAPHIQUE DES CONTRIBUTIONS"))
    elements.append(Spacer(1, 8))

    if current_score and current_score.detail_json:
        chart = _build_bar_chart(current_score.detail_json)
        elements.append(chart)
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(
            "<i>Le graphique ci-dessus représente la contribution absolue (en points) "
            "de chaque critère au score global. Plus la barre est longue, "
            "plus ce facteur contribue au risque.</i>",
            ParagraphStyle("italic_note", fontName="Helvetica-Oblique",
                           fontSize=8, textColor=C_MGRAY, spaceAfter=12),
        ))
    else:
        elements.append(Paragraph("Aucune donnée disponible pour le graphique.", styles["body"]))

    elements.append(Spacer(1, 8))
    elements.append(_section_table("🗂  HISTORIQUE DES SCORES"))
    elements.append(Spacer(1, 4))

    if score_history:
        h_rows = []
        for s in score_history:
            courant = "✓" if s.is_current else ""
            h_rows.append([
                _fmt_datetime(s.date_calcul),
                str(s.score_global),
                _category_label(s.categorie),
                s.calcule_par or "AUTOMATED",
                courant,
            ])
        elements.append(_standard_table(
            ["Date calcul", "Score", "Catégorie", "Agent", "Courant"],
            h_rows,
            [5 * cm, 2.5 * cm, 3 * cm, 4.5 * cm, 2 * cm],
        ))
    else:
        elements.append(Paragraph("Aucun historique de score disponible.", styles["body"]))

    elements += _footer_elements(styles, "Page 2/3", agent_name)

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 3 — Alertes + Conformité CENTIF
    # ════════════════════════════════════════════════════════════════════════
    elements.append(PageBreak())
    elements += _header_block(styles, export_date, agent_name)
    elements.append(_section_table("🚨  ALERTES ACTIVES", bg=C_RED))
    elements.append(Spacer(1, 4))

    if open_alerts:
        a_rows = []
        for a in open_alerts:
            # FIX: champs corrects du modèle Alert
            # type_alerte / date_creation / statut / sar_declare
            a_rows.append([
                a.type_alerte or "—",
                _fmt_datetime(a.date_creation),
                a.statut or "—",
                "Oui" if a.sar_declare else "Non",
            ])
        elements.append(_standard_table(
            ["Type", "Date création", "Statut", "SAR déposé"],
            a_rows,
            [5 * cm, 4 * cm, 4 * cm, 4 * cm],
        ))
    else:
        elements.append(Paragraph(
            "✓ Aucune alerte ouverte pour ce client.",
            ParagraphStyle("ok", fontName="Helvetica-Bold", fontSize=9,
                           textColor=C_GREEN, spaceAfter=4),
        ))

    elements.append(Spacer(1, 12))

    # Mention conformité CENTIF
    centif_t = Table(
        [[Paragraph(
            "⚖  CONFORMITÉ RÉGLEMENTAIRE — CENTIF BÉNIN\n\n"
            "Ce document est généré conformément aux dispositions de la loi n°2006-14 "
            "du 31 octobre 2006 portant lutte contre le blanchiment de capitaux et le "
            "financement du terrorisme en République du Bénin, et aux recommandations "
            "du GIABA/FATF applicables aux institutions de microfinance.\n\n"
            "Toute alerte de niveau ÉLEVÉ (score ≥ 67) doit faire l'objet d'une "
            "Déclaration de Soupçon (SAR) transmise à la CENTIF dans un délai de "
            "<b>48 heures</b> suivant la détection.",
            ParagraphStyle("centif", fontName="Helvetica", fontSize=8,
                           textColor=C_DGRAY, spaceAfter=0, leading=13),
        )]],
        colWidths=[17 * cm],
    )
    centif_t.setStyle(TableStyle([
        ("BOX",           (0, 0), (-1, -1), 1, C_NAVY),
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#EBF5FB")),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    elements.append(centif_t)

    elements.append(Spacer(1, 10))

    # Signature électronique
    sig_t = Table(
        [[
            Paragraph("Signature électronique :", styles["body_bold"]),
            Paragraph(
                f"<b>{agent_name}</b> — {export_date}",
                styles["body"],
            ),
        ]],
        colWidths=[5 * cm, 12 * cm],
    )
    sig_t.setStyle(TableStyle([
        ("BOX",     (0, 0), (-1, -1), 0.5, C_MGRAY),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    elements.append(sig_t)

    elements += _footer_elements(styles, "Page 3/3 — Document confidentiel", agent_name)

    # ── Build ─────────────────────────────────────────────────────────────
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


# ─────────────────────────────────────────────────────────────────────────────
# 2. CSV — Transactions du client
# ─────────────────────────────────────────────────────────────────────────────

def generate_transactions_csv(
    db: Session,
    customer_id: UUID,
    days: int = 90,
) -> bytes:
    """
    Génère le CSV des transactions d'un client sur une période donnée.

    Colonnes : date_op, montant, devise, type_op, canal, origine_pays,
               destination_pays, type_compte, solde_moyen_compte.

    :param db: Session SQLAlchemy.
    :param customer_id: UUID du client.
    :param days: fenêtre temporelle en jours (défaut 90).
    :returns: bytes CSV encodé UTF-8-sig (compatible Excel).
    :raises ValueError: si le client est introuvable.
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise ValueError(f"Client introuvable : {customer_id}")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Récupérer tous les comptes du client
    accounts = (
        db.query(CustomerAccount)
        .filter(CustomerAccount.client_id == customer_id)
        .all()
    )
    account_ids = [a.id for a in accounts]
    account_map = {a.id: a for a in accounts}

    # Récupérer les pays pour jointure manuelle
    all_countries = {c.id: c for c in db.query(Country).all()}

    transactions: list[Transaction] = []
    if account_ids:
        transactions = (
            db.query(Transaction)
            .filter(
                Transaction.compte_id.in_(account_ids),
                Transaction.date_op >= cutoff,
            )
            .order_by(Transaction.date_op.desc())
            .all()
        )

    # Construction CSV en mémoire
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    # En-têtes en français
    writer.writerow([
        "Date opération",
        "Montant",
        "Devise",
        "Type opération",
        "Canal",
        "Pays origine",
        "Pays destination",
        "Type compte",
        "Solde moyen compte",
        "Origine (texte libre)",
        "Destination (texte libre)",
    ])

    for tx in transactions:
        acc = account_map.get(tx.compte_id)
        orig_pays = all_countries.get(tx.origine_pays_id)
        dest_pays = all_countries.get(tx.destination_pays_id)

        date_str = ""
        if tx.date_op:
            d = tx.date_op
            if hasattr(d, "tzinfo") and d.tzinfo:
                d = d.replace(tzinfo=None)
            date_str = d.strftime("%d/%m/%Y %H:%M")

        writer.writerow([
            date_str,
            f"{float(tx.montant):.2f}" if tx.montant is not None else "",
            tx.devise or "XOF",
            tx.type_op or "",
            tx.canal or "",
            orig_pays.name if orig_pays else "",
            dest_pays.name if dest_pays else "",
            acc.type_compte if acc else "",
            f"{float(acc.solde_moyen):.2f}" if (acc and acc.solde_moyen is not None) else "",
            tx.origine or "",
            tx.destination or "",
        ])

    # UTF-8 avec BOM pour compatibilité Excel
    return output.getvalue().encode("utf-8-sig")


# ─────────────────────────────────────────────────────────────────────────────
# 3. PDF — Déclaration de soupçon SAR (CENTIF)
# ─────────────────────────────────────────────────────────────────────────────

def generate_sar_pdf(
    db: Session,
    alert_id: UUID,
    agent: User,
) -> bytes:
    """
    Génère la Déclaration de Soupçon (SAR) conforme CENTIF Bénin en PDF.

    :param db: Session SQLAlchemy.
    :param alert_id: UUID de l'alerte déclenchant le SAR.
    :param agent: Utilisateur ayant demandé l'export.
    :returns: bytes du PDF SAR généré en mémoire.
    :raises ValueError: si l'alerte ou le client est introuvable.
    """
    # ── Chargement des données ────────────────────────────────────────────
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise ValueError(f"Alerte introuvable : {alert_id}")

    customer = db.query(Customer).filter(Customer.id == alert.client_id).first()
    if not customer:
        raise ValueError(f"Client introuvable pour alerte : {alert_id}")

    current_score: Score | None = (
        db.query(Score)
        .filter(Score.client_id == customer.id, Score.is_current == True)  # noqa
        .first()
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    account_ids = [
        a.id for a in
        db.query(CustomerAccount)
        .filter(CustomerAccount.client_id == customer.id)
        .all()
    ]
    suspicious_txs: list[Transaction] = []
    if account_ids:
        suspicious_txs = (
            db.query(Transaction)
            .filter(
                Transaction.compte_id.in_(account_ids),
                Transaction.date_op >= cutoff,
            )
            .order_by(Transaction.date_op.desc())
            .limit(20)
            .all()
        )

    all_countries = {c.id: c for c in db.query(Country).all()}

    # Numéro SAR unique
    sar_number = f"SAR-{str(alert_id).upper()[:8]}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"

    # ── Setup document ────────────────────────────────────────────────────
    buffer     = io.BytesIO()
    styles     = _build_styles()
    export_date = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M") + " UTC"
    # FIX: User n'a pas de champ full_name — on utilise login (seul champ disponible)
    agent_name = agent.login

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
        topMargin=2 * cm, bottomMargin=2.5 * cm,
        title=f"SAR — {sar_number}",
        author="RiskGuard",
        subject="Déclaration de Soupçon CENTIF",
    )

    elements = []

    # ── En-tête officiel ──────────────────────────────────────────────────
    header_sar = Table(
        [[
            Paragraph("RÉPUBLIQUE DU BÉNIN", ParagraphStyle(
                "rep", fontName="Helvetica-Bold", fontSize=9,
                textColor=C_NAVY, alignment=TA_CENTER)),
            Paragraph("CELLULE NATIONALE DE TRAITEMENT\nDES INFORMATIONS FINANCIÈRES", ParagraphStyle(
                "centif_h", fontName="Helvetica-Bold", fontSize=9,
                textColor=C_NAVY, alignment=TA_CENTER)),
        ]],
        colWidths=[8 * cm, 9 * cm],
    )
    header_sar.setStyle(TableStyle([
        ("BOX",       (0, 0), (-1, -1), 1.5, C_NAVY),
        ("LINEAFTER", (0, 0), (0, -1), 0.5, C_MGRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(header_sar)
    elements.append(Spacer(1, 12))

    # Titre principal
    elements.append(Paragraph(
        "DÉCLARATION DE SOUPÇON",
        styles["sar_title"],
    ))
    elements.append(Paragraph(
        "Article 26 — Loi n°2006-14 du 31 octobre 2006 portant LBC/FT",
        ParagraphStyle("sar_law", fontName="Helvetica-Oblique", fontSize=9,
                       textColor=C_DGRAY, alignment=TA_CENTER, spaceAfter=4),
    ))
    elements.append(HRFlowable(width="100%", thickness=2, color=C_NAVY, spaceAfter=6))

    # Références
    ref_t = Table(
        [[
            Paragraph(f"N° SAR : <b>{sar_number}</b>", styles["sar_ref"]),
            Paragraph(f"Date : <b>{export_date}</b>", styles["body_bold"]),
        ]],
        colWidths=[9 * cm, 8 * cm],
    )
    ref_t.setStyle(TableStyle([
        ("BOX",   (0, 0), (-1, -1), 0.5, C_RED),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(ref_t)
    elements.append(Spacer(1, 10))

    # ── Section 1 : Déclarant ─────────────────────────────────────────────
    elements.append(_section_table("1. DÉCLARANT"))
    elements.append(Spacer(1, 4))
    decl_t = Table(
        [
            ["Institution", "Microfinance Béninoise SA",
             "Secteur", "Microfinance"],
            ["Adresse", "01 BP 1234 Cotonou, Bénin",
             "Contact", "contact@riskguard.bj"],
            ["Agent déclarant", agent_name,
             "Système", "RiskGuard v1.2"],
        ],
        colWidths=[3.5 * cm, 6 * cm, 3 * cm, 4.5 * cm],
    )
    decl_t.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), C_NAVY),
        ("TEXTCOLOR", (2, 0), (2, -1), C_NAVY),
        ("FONTSIZE",  (0, 0), (-1, -1), 8),
        ("GRID",      (0, 0), (-1, -1), 0.5, C_MGRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(decl_t)
    elements.append(Spacer(1, 10))

    # ── Section 2 : Personne concernée ───────────────────────────────────
    elements.append(_section_table("2. PERSONNE CONCERNÉE"))
    elements.append(Spacer(1, 4))

    score_str = "Non calculé"
    cat_str   = "—"
    if current_score:
        score_str = f"{current_score.score_global}/100"
        cat_str   = _category_label(current_score.categorie)

    pep_str = "OUI — Personne Politiquement Exposée" if customer.statut_pep else "Non"

    person_data = [
        ["Nom et prénom", f"{customer.prenom} {customer.nom}",
         "Date naissance", _fmt_date(customer.date_naissance)],
        ["Téléphone", customer.phone or "—",
         "Email", customer.email or "—"],
        ["Profession", customer.profession_name or "—",
         "Code risque", customer.profession_risk or "—"],
        ["Revenus déclarés", _fmt_montant(customer.revenus_declares),
         "Statut PEP", pep_str],
        ["Score LBC/FT", score_str,
         "Catégorie risque", cat_str],
        ["Ville", customer.city or "—",
         "ID client", str(customer.id)[:18] + "..."],
    ]
    person_t = Table(person_data, colWidths=[3.5 * cm, 6 * cm, 3.5 * cm, 4.5 * cm])
    person_t.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), C_NAVY),
        ("TEXTCOLOR", (2, 0), (2, -1), C_NAVY),
        ("FONTSIZE",  (0, 0), (-1, -1), 8),
        ("GRID",      (0, 0), (-1, -1), 0.5, C_MGRAY),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EBF5FB")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#EBF5FB")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(person_t)
    elements.append(Spacer(1, 10))

    # ── Section 3 : Détail alerte ─────────────────────────────────────────
    elements.append(_section_table("3. DÉTAIL DE L'ALERTE", bg=C_RED))
    elements.append(Spacer(1, 4))

    # FIX: champs corrects du modèle Alert :
    # type_alerte / statut / sar_declare / date_creation / decision
    alert_data = [
        ["Type d'alerte",  alert.type_alerte or "—",
         "Statut",         alert.statut or "—"],
        ["Date détection", _fmt_datetime(alert.date_creation),
         "SAR déclaré",    "Oui" if alert.sar_declare else "Non"],
        ["Décision/Motif", Paragraph(alert.decision or "—",
                                     styles["body"]), "", ""],
    ]
    alert_t = Table(alert_data, colWidths=[3.5 * cm, 5.5 * cm, 3 * cm, 5 * cm])
    alert_t.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",    (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR",   (0, 0), (0, -1), C_NAVY),
        ("TEXTCOLOR",   (2, 0), (2, -1), C_NAVY),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("GRID",        (0, 0), (-1, -1), 0.5, C_MGRAY),
        ("SPAN",        (1, 2), (3, 2)),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(alert_t)
    elements.append(Spacer(1, 10))

    # ── Section 4 : Transactions suspectes ───────────────────────────────
    elements.append(_section_table("4. TRANSACTIONS SUSPECTES (90 derniers jours)"))
    elements.append(Spacer(1, 4))

    if suspicious_txs:
        tx_rows = []
        for tx in suspicious_txs:
            date_str = ""
            if tx.date_op:
                d = tx.date_op
                if hasattr(d, "tzinfo") and d.tzinfo:
                    d = d.replace(tzinfo=None)
                date_str = d.strftime("%d/%m/%Y")

            dest = all_countries.get(tx.destination_pays_id)
            orig = all_countries.get(tx.origine_pays_id)
            tx_rows.append([
                date_str,
                _fmt_montant(tx.montant),
                tx.type_op or "—",
                tx.canal or "—",
                orig.name if orig else "—",
                dest.name if dest else "—",
            ])

        elements.append(_standard_table(
            ["Date", "Montant", "Type", "Canal", "Pays origine", "Pays destination"],
            tx_rows,
            [2.5 * cm, 3.5 * cm, 2.5 * cm, 2 * cm, 3 * cm, 3.5 * cm],
        ))
    else:
        elements.append(Paragraph(
            "Aucune transaction sur les 90 derniers jours.", styles["body"]
        ))

    elements.append(Spacer(1, 10))

    # ── Section 5 : Motif et action recommandée ───────────────────────────
    elements.append(_section_table("5. MOTIF DE LA DÉCLARATION"))
    elements.append(Spacer(1, 4))

    motif_text = (
        f"Le système RiskGuard a détecté un score de risque LBC/FT de "
        f"<b>{score_str}</b> (catégorie <b>{cat_str}</b>), dépassant le seuil "
        f"réglementaire de 67 points fixé par la politique de vigilance de "
        f"l'établissement. Ce niveau de risque résulte de la combinaison de "
        f"facteurs incluant le profil professionnel, la zone géographique, "
        f"l'analyse des transactions et le statut PEP du client concerné."
    )
    elements.append(Paragraph(motif_text, styles["body"]))
    elements.append(Spacer(1, 8))

    action_t = Table(
        [[Paragraph(
            "⚠  ACTION RECOMMANDÉE : Transmission à la CENTIF dans les <b>48 heures</b> "
            "suivant la présente déclaration, conformément à l'article 26 de la loi "
            "n°2006-14 portant LBC/FT en République du Bénin.",
            styles["warning"],
        )]],
        colWidths=[17 * cm],
    )
    action_t.setStyle(TableStyle([
        ("BOX",     (0, 0), (-1, -1), 1.5, C_RED),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FDEDEC")),
        ("TOPPADDING",  (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(action_t)
    elements.append(Spacer(1, 12))

    # ── Signature ─────────────────────────────────────────────────────────
    sig_t = Table(
        [[
            Table(
                [
                    [Paragraph("Agent déclarant :", styles["body_bold"])],
                    [Paragraph(f"<b>{agent_name}</b>", styles["body"])],
                    [Paragraph(f"Date : {export_date}", styles["body"])],
                    [Paragraph("Signature : ___________________", styles["body"])],
                ],
                colWidths=[7 * cm],
            ),
            Table(
                [
                    [Paragraph("Cachet de l'établissement :", styles["body_bold"])],
                    [Spacer(1, 30)],
                    [Paragraph("[Microfinance Béninoise SA]", ParagraphStyle(
                        "cachet", fontName="Helvetica-Oblique", fontSize=8,
                        textColor=C_MGRAY))],
                ],
                colWidths=[10 * cm],
            ),
        ]],
        colWidths=[7 * cm, 10 * cm],
    )
    sig_t.setStyle(TableStyle([
        ("BOX",   (0, 0), (-1, -1), 0.5, C_NAVY),
        ("TOPPADDING",  (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(sig_t)

    elements += _footer_elements(
        styles,
        f"SAR {sar_number} — CONFIDENTIEL",
        agent_name,
    )

    # ── Build ─────────────────────────────────────────────────────────────
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()