"""
tests/integration/test_exports.py
===================================
Tests d'intégration — Endpoints d'export LBC/FT — RiskGuard.

Vérifie :
  - test_export_pdf_customer_success     : 200, PDF non vide, en-têtes corrects
  - test_export_pdf_customer_not_found   : 404 client inexistant
  - test_export_csv_transactions_success : 200, CSV parsable, colonnes françaises
  - test_export_csv_unauthorized         : 401 sans token JWT
  - test_export_sar_pdf_success          : 200, PDF non vide, header X-SAR-Reference

Fixtures : base de données réelle avec rollback par test.
Utilise FastAPI TestClient (httpx en arrière-plan).

Auteur  : Dev A — AFFOKPE Magloire
Version : 1.0 — Mai 2026
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth.security import create_access_token
from app.config import settings
from app.db.session import get_db
from app.main import app
from app.models.alerts import Alert
from app.models.countries import Country
from app.models.customer_accounts import CustomerAccount
from app.models.customer_docs import CustomerDoc
from app.models.customers import Customer
from app.models.risk_thresholds import RiskThreshold
from app.models.risk_zones import RiskZone
from app.models.scores import Score
from app.models.scoring_criteria import ScoringCriteria
from app.models.transactions import Transaction
from app.models.users import User


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures : DB et TestClient
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Session DB pour la durée du module — rollback final."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Données de référence minimales
    _seed_references(session)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="module")
def test_client(db_session: Session) -> TestClient:
    """TestClient FastAPI avec override de la dépendance DB."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def auth_headers_admin(db_session: Session) -> dict[str, str]:
    """Token JWT admin valide pour tous les tests."""
    user = _get_or_create_test_user(db_session, role="admin")
    token = create_access_token(data={"sub": str(user.id), "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def auth_headers_compliance(db_session: Session) -> dict[str, str]:
    """Token JWT compliance_officer valide."""
    user = _get_or_create_test_user(db_session, role="compliance_officer")
    token = create_access_token(
        data={"sub": str(user.id), "role": "compliance_officer"}
    )
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de seeding
# ─────────────────────────────────────────────────────────────────────────────

def _seed_references(db: Session) -> None:
    """Insère les données de référence minimales (idempotent)."""
    if db.query(ScoringCriteria).count() == 0:
        for code, name, w in [
            ("C1", "Profil professionnel", 20),
            ("C2", "Zone géographique",    20),
            ("C3", "Historique transact.", 25),
            ("C4", "Ancienneté",           10),
            ("C5", "Statut PEP",           15),
            ("C6", "Cohérence KYC",        10),
        ]:
            db.add(ScoringCriteria(code=code, name=name, weight=Decimal(str(w))))

    if db.query(RiskThreshold).count() == 0:
        db.add(RiskThreshold(category="FAIBLE", score_min=0,  score_max=33))
        db.add(RiskThreshold(category="MOYEN",  score_min=34, score_max=66))
        db.add(RiskThreshold(category="ELEVE",  score_min=67, score_max=100))

    if db.query(Country).filter(Country.code_iso == "BJ").first() is None:
        db.add(Country(code_iso="BJ", name="Bénin",
                       is_uemoa=True, is_border=False, is_fatf=False))
        db.add(Country(code_iso="NG", name="Nigeria",
                       is_uemoa=False, is_border=True, is_fatf=False))

    if db.query(RiskZone).count() == 0:
        db.add(RiskZone(name="URBAINE", risk_level="FAIBLE", source="TEST"))
        db.add(RiskZone(name="FRONTIERE", risk_level="ELEVE", source="TEST"))

    db.flush()


def _get_or_create_test_user(db: Session, role: str = "admin") -> User:
    """Retourne ou crée un utilisateur de test selon le rôle."""
    login = f"test_export_{role}"
    user = db.query(User).filter(User.login == login).first()
    if not user:
        user = User(
            login=login,
            full_name=f"Test Export {role.title()}",
            email=f"export_{role}_{uuid.uuid4().hex[:4]}@test.bj",
            hashed_password="$2b$12$fakehashfortesting",
            role=role,
            is_active=True,
        )
        db.add(user)
        db.flush()
    return user


def _create_full_customer(db: Session) -> tuple[Customer, CustomerAccount, Score, Alert]:
    """
    Crée un client complet avec compte, score et alerte pour les tests d'export.
    Retourne (customer, account, score, alert).
    """
    bj = db.query(Country).filter(Country.code_iso == "BJ").first()
    zone = db.query(RiskZone).filter(RiskZone.name == "FRONTIERE").first()

    customer = Customer(
        nom="EXPORT_TEST",
        prenom="Client",
        phone=f"+229{uuid.uuid4().int % 100_000_000:08d}",
        email=f"export_{uuid.uuid4().hex[:6]}@test.bj",
        profession_code="COMMER_TRANSFR",
        profession_name="Commerçant transfrontalier",
        profession_risk="HIGH",
        revenus_declares=Decimal("350000"),
        city="Cotonou",
        region="Littoral",
        zone_geo=zone.id if zone else None,
        pays=bj.id if bj else None,
        statut_pep=False,
        kyc_completion=65,
        kyc_level="MEDIUM",
        status="ACTIVE",
        date_creation=datetime.now(timezone.utc) - timedelta(days=2 * 365),
    )
    db.add(customer)
    db.flush()

    # Document KYC
    doc = CustomerDoc(
        client_id=customer.id,
        type_doc="CNI",
        numero="CNI-TEST-001",
        date_expiration=date.today() + timedelta(days=500),
        valide=True,
    )
    db.add(doc)

    # Compte bancaire
    account = CustomerAccount(
        client_id=customer.id,
        type_compte="COURANT",
        solde_moyen=Decimal("1250000"),
        date_ouverture=date.today() - timedelta(days=365),
        status="ACTIF",
    )
    db.add(account)
    db.flush()

    # Transactions
    for i in range(5):
        tx = Transaction(
            compte_id=account.id,
            montant=Decimal(str(150_000 + i * 50_000)),
            devise="XOF",
            type_op="VIREMENT",
            date_op=datetime.now(timezone.utc) - timedelta(days=i * 10 + 1),
            canal="INTERNET",
            destination_pays_id=bj.id if bj else None,
        )
        db.add(tx)
    db.flush()

    # Score courant
    score = Score(
        client_id=customer.id,
        score_global=72,
        detail_json={
            "C1": 13.0, "C2": 13.0, "C3": 21.25,
            "C4": 7.5,  "C5": 15.0, "C6": 8.5,
        },
        categorie="ÉLEVÉ",
        is_current=True,
        calcule_par="AUTOMATED",
    )
    db.add(score)
    db.flush()

    # Alerte SCORE_ELEVE
    alert = Alert(
        customer_id=customer.id,
        alert_type="SCORE_ELEVE",
        risk_level="HIGH",
        description="Score de risque élevé (72/100) — seuil ÉLEVÉ atteint",
        status="OPEN",
        sar_filed=False,
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    db.add(alert)
    db.flush()
    db.commit()

    return customer, account, score, alert


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1 — PDF fiche client — succès (200)
# ─────────────────────────────────────────────────────────────────────────────

class TestExportCustomerPDF:

    def test_export_pdf_customer_success(
        self,
        test_client: TestClient,
        auth_headers_admin: dict,
        db_session: Session,
    ):
        """
        GET /api/exports/customer/{id}/pdf avec client valide →
        200, Content-Type application/pdf, corps non vide, magic bytes PDF.
        """
        customer, _, _, _ = _create_full_customer(db_session)

        response = test_client.get(
            f"/api/exports/customer/{customer.id}/pdf",
            headers=auth_headers_admin,
        )

        assert response.status_code == 200, (
            f"Attendu 200, obtenu {response.status_code} — {response.text[:200]}"
        )

        # Vérification Content-Type
        assert "application/pdf" in response.headers.get("content-type", ""), (
            f"Content-Type attendu 'application/pdf', obtenu : "
            f"{response.headers.get('content-type')}"
        )

        # Vérification corps non vide
        content = response.content
        assert len(content) > 1000, (
            f"PDF trop petit ({len(content)} octets) — génération probablement vide"
        )

        # Vérification magic bytes PDF (%PDF-)
        assert content[:4] == b"%PDF", (
            f"Le fichier ne commence pas par '%PDF' — pas un PDF valide. "
            f"Début reçu : {content[:20]}"
        )

        # Vérification en-tête Content-Disposition
        content_disposition = response.headers.get("content-disposition", "")
        assert "attachment" in content_disposition, (
            f"Content-Disposition devrait contenir 'attachment', obtenu : "
            f"{content_disposition}"
        )
        assert ".pdf" in content_disposition, (
            "Le nom de fichier devrait se terminer par .pdf"
        )

        # Vérification en-tête X-Generated-By
        assert response.headers.get("x-generated-by") == "RiskGuard"

    def test_export_pdf_customer_compliance_officer(
        self,
        test_client: TestClient,
        auth_headers_compliance: dict,
        db_session: Session,
    ):
        """
        Un compliance_officer peut également exporter le PDF.
        """
        customer, _, _, _ = _create_full_customer(db_session)

        response = test_client.get(
            f"/api/exports/customer/{customer.id}/pdf",
            headers=auth_headers_compliance,
        )
        assert response.status_code == 200
        assert response.content[:4] == b"%PDF"

    def test_export_pdf_customer_not_found(
        self,
        test_client: TestClient,
        auth_headers_admin: dict,
    ):
        """
        GET /api/exports/customer/{uuid_inexistant}/pdf → 404.
        """
        fake_id = uuid.uuid4()

        response = test_client.get(
            f"/api/exports/customer/{fake_id}/pdf",
            headers=auth_headers_admin,
        )

        assert response.status_code == 404, (
            f"Attendu 404, obtenu {response.status_code}"
        )
        data = response.json()
        assert "detail" in data, "La réponse 404 devrait contenir un champ 'detail'"
        assert str(fake_id) in data["detail"] or "introuvable" in data["detail"].lower()

    def test_export_pdf_customer_uuid_invalide(
        self,
        test_client: TestClient,
        auth_headers_admin: dict,
    ):
        """UUID malformé → 422 Unprocessable Entity."""
        response = test_client.get(
            "/api/exports/customer/pas-un-uuid/pdf",
            headers=auth_headers_admin,
        )
        assert response.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2 — CSV transactions — succès (200)
# ─────────────────────────────────────────────────────────────────────────────

class TestExportTransactionsCSV:

    def test_export_csv_transactions_success(
        self,
        test_client: TestClient,
        auth_headers_admin: dict,
        db_session: Session,
    ):
        """
        GET /api/exports/transactions/{id}/csv avec client valide →
        200, Content-Type text/csv, CSV parsable, colonnes en français.
        """
        customer, _, _, _ = _create_full_customer(db_session)

        response = test_client.get(
            f"/api/exports/transactions/{customer.id}/csv",
            headers=auth_headers_admin,
        )

        assert response.status_code == 200, (
            f"Attendu 200, obtenu {response.status_code} — {response.text[:200]}"
        )

        # Content-Type
        ct = response.headers.get("content-type", "")
        assert "text/csv" in ct or "csv" in ct, (
            f"Content-Type attendu 'text/csv', obtenu : {ct}"
        )

        # Parsing CSV
        content_str = response.content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(content_str), delimiter=";")
        rows = list(reader)

        assert len(rows) >= 1, "Le CSV devrait avoir au moins la ligne d'en-tête"

        # Vérification des colonnes françaises
        headers = rows[0]
        assert len(headers) >= 8, (
            f"Attendu ≥ 8 colonnes, obtenu {len(headers)} : {headers}"
        )

        expected_headers = [
            "Date opération", "Montant", "Devise", "Type opération", "Canal"
        ]
        for expected in expected_headers:
            assert any(expected.lower() in h.lower() for h in headers), (
                f"Colonne '{expected}' introuvable dans les en-têtes : {headers}"
            )

        # Vérification données (au moins 5 transactions créées)
        data_rows = rows[1:]
        assert len(data_rows) >= 1, (
            f"Le CSV devrait avoir des lignes de données, obtenu : {len(data_rows)}"
        )

    def test_export_csv_with_days_param(
        self,
        test_client: TestClient,
        auth_headers_admin: dict,
        db_session: Session,
    ):
        """
        Le paramètre ?days=180 est accepté et retourne un CSV valide.
        """
        customer, _, _, _ = _create_full_customer(db_session)

        response = test_client.get(
            f"/api/exports/transactions/{customer.id}/csv?days=180",
            headers=auth_headers_admin,
        )

        assert response.status_code == 200
        content_str = response.content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(content_str), delimiter=";")
        rows = list(reader)
        assert len(rows) >= 1   # au moins l'en-tête

    def test_export_csv_unauthorized(
        self,
        test_client: TestClient,
    ):
        """
        GET /api/exports/transactions/{id}/csv sans token JWT → 401.
        """
        fake_id = uuid.uuid4()

        response = test_client.get(
            f"/api/exports/transactions/{fake_id}/csv"
            # Pas d'Authorization header
        )

        assert response.status_code == 401, (
            f"Attendu 401 sans token, obtenu {response.status_code}"
        )
        data = response.json()
        assert "detail" in data

    def test_export_csv_token_invalide_retourne_401(
        self,
        test_client: TestClient,
    ):
        """Token JWT falsifié → 401."""
        response = test_client.get(
            f"/api/exports/transactions/{uuid.uuid4()}/csv",
            headers={"Authorization": "Bearer token_totalement_invalide"},
        )
        assert response.status_code == 401

    def test_export_csv_not_found(
        self,
        test_client: TestClient,
        auth_headers_admin: dict,
    ):
        """Client inexistant → 404."""
        response = test_client.get(
            f"/api/exports/transactions/{uuid.uuid4()}/csv",
            headers=auth_headers_admin,
        )
        assert response.status_code == 404

    def test_export_csv_days_invalide(
        self,
        test_client: TestClient,
        auth_headers_admin: dict,
        db_session: Session,
    ):
        """days=0 → 422 (validation Pydantic, ge=1)."""
        customer, _, _, _ = _create_full_customer(db_session)

        response = test_client.get(
            f"/api/exports/transactions/{customer.id}/csv?days=0",
            headers=auth_headers_admin,
        )
        assert response.status_code == 422

    def test_export_csv_content_disposition(
        self,
        test_client: TestClient,
        auth_headers_admin: dict,
        db_session: Session,
    ):
        """Le Content-Disposition doit contenir 'attachment' et '.csv'."""
        customer, _, _, _ = _create_full_customer(db_session)

        response = test_client.get(
            f"/api/exports/transactions/{customer.id}/csv",
            headers=auth_headers_admin,
        )

        assert response.status_code == 200
        cd = response.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert ".csv" in cd


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3 — SAR PDF — succès (200)
# ─────────────────────────────────────────────────────────────────────────────

class TestExportSARPDF:

    def test_export_sar_pdf_success(
        self,
        test_client: TestClient,
        auth_headers_admin: dict,
        db_session: Session,
    ):
        """
        GET /api/exports/sar/{alert_id}/pdf avec alerte valide →
        200, PDF non vide, magic bytes PDF, header X-SAR-Reference présent.
        """
        _, _, _, alert = _create_full_customer(db_session)

        response = test_client.get(
            f"/api/exports/sar/{alert.id}/pdf",
            headers=auth_headers_admin,
        )

        assert response.status_code == 200, (
            f"Attendu 200, obtenu {response.status_code} — {response.text[:300]}"
        )

        # Content-Type PDF
        assert "application/pdf" in response.headers.get("content-type", "")

        # Corps non vide
        content = response.content
        assert len(content) > 1000, (
            f"SAR PDF trop petit ({len(content)} octets)"
        )

        # Magic bytes PDF
        assert content[:4] == b"%PDF", (
            f"Le SAR ne commence pas par '%PDF'. Début : {content[:20]}"
        )

        # Header X-SAR-Reference présent
        sar_ref = response.headers.get("x-sar-reference", "")
        assert sar_ref.startswith("SAR-"), (
            f"Header X-SAR-Reference attendu commençant par 'SAR-', obtenu : '{sar_ref}'"
        )

        # Header X-Generated-By
        assert response.headers.get("x-generated-by") == "RiskGuard"

    def test_export_sar_content_disposition(
        self,
        test_client: TestClient,
        auth_headers_admin: dict,
        db_session: Session,
    ):
        """Le Content-Disposition du SAR doit contenir 'SAR_' et '.pdf'."""
        _, _, _, alert = _create_full_customer(db_session)

        response = test_client.get(
            f"/api/exports/sar/{alert.id}/pdf",
            headers=auth_headers_admin,
        )

        assert response.status_code == 200
        cd = response.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert "SAR_" in cd or "sar" in cd.lower()
        assert ".pdf" in cd

    def test_export_sar_not_found(
        self,
        test_client: TestClient,
        auth_headers_admin: dict,
    ):
        """Alerte inexistante → 404."""
        response = test_client.get(
            f"/api/exports/sar/{uuid.uuid4()}/pdf",
            headers=auth_headers_admin,
        )
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_export_sar_unauthorized(
        self,
        test_client: TestClient,
    ):
        """Sans token → 401."""
        response = test_client.get(
            f"/api/exports/sar/{uuid.uuid4()}/pdf"
        )
        assert response.status_code == 401

    def test_export_sar_compliance_officer(
        self,
        test_client: TestClient,
        auth_headers_compliance: dict,
        db_session: Session,
    ):
        """Un compliance_officer peut générer un SAR."""
        _, _, _, alert = _create_full_customer(db_session)

        response = test_client.get(
            f"/api/exports/sar/{alert.id}/pdf",
            headers=auth_headers_compliance,
        )
        assert response.status_code == 200
        assert response.content[:4] == b"%PDF"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4 — Contrôle des rôles (403)
# ─────────────────────────────────────────────────────────────────────────────

class TestExportRoles:

    def test_export_pdf_role_insuffisant_retourne_403(
        self,
        test_client: TestClient,
        db_session: Session,
    ):
        """
        Un utilisateur avec rôle 'viewer' (non autorisé) → 403.
        """
        # Créer un utilisateur avec rôle non autorisé
        viewer = User(
            login=f"viewer_{uuid.uuid4().hex[:6]}",
            full_name="Viewer Test",
            email=f"viewer_{uuid.uuid4().hex[:4]}@test.bj",
            hashed_password="$2b$12$fakehash",
            role="viewer",
            is_active=True,
        )
        db_session.add(viewer)
        db_session.flush()

        token = create_access_token(data={"sub": str(viewer.id), "role": "viewer"})
        headers = {"Authorization": f"Bearer {token}"}

        customer, _, _, _ = _create_full_customer(db_session)

        response = test_client.get(
            f"/api/exports/customer/{customer.id}/pdf",
            headers=headers,
        )
        assert response.status_code == 403, (
            f"Attendu 403 pour rôle 'viewer', obtenu {response.status_code}"
        )
        assert "detail" in response.json()
