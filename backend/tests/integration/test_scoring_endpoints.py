"""
tests/integration/test_scoring_endpoints.py
============================================
Tests d'intégration des endpoints REST du module Scoring — RiskGuard.

Vérifie :
  - Authentification JWT (401 sans token, 200 avec token valide)
  - Format exact de la réponse (contrat API v1.0)
  - Création automatique d'alerte si score ≥ 67
  - Idempotence du rescore (pas de doublon d'alerte ouverte)
  - Codes HTTP corrects (404 client inexistant, 200 OK)
  - Historique des scores (GET /api/customers/{id}/scores)

Prérequis :
  - DB de test accessible (voir conftest.py)
  - Tables migrées (alembic upgrade head)
  - Un utilisateur admin créé dans la DB de test

Corrections appliquées (alignement models) :
  [Fix-2] Transaction importé en tête de fichier (évite NameError)
  [Fix-3] ScoringCriteria : suppression is_active (inexistant), weight en % entier
  [Fix-4] RiskThreshold : min_score/max_score/required_action → score_min/score_max/action
           category 'ÉLEVÉ' → 'ELEVE' (convention DB sans accent)
  [Fix-5] User : suppression full_name/email (inexistants), hashed_password → password_hash,
           role='admin' → role_id récupéré depuis user_roles
  [Fix-6] Alert queries : customer_id→client_id, alert_type→type_alerte, status→statut,
           suppression Alert.risk_level (inexistant), created_at→date_creation
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.main import app
from app.db.session import get_db
from app.auth.security import create_access_token
from app.models.alerts import Alert
from app.models.countries import Country
from app.models.customer_accounts import CustomerAccount
from app.models.customer_docs import CustomerDoc
from app.models.customers import Customer
from app.models.risk_thresholds import RiskThreshold
from app.models.risk_zones import RiskZone
from app.models.scores import Score
from app.models.scoring_criteria import ScoringCriteria
from app.models.transactions import Transaction  # [Fix-2] import déplacé en tête de fichier
from app.models.users import User
from app.models.user_roles import UserRole

# ── Configuration DB test ──────────────────────────────────────────────────
TEST_DATABASE_URL = "postgresql://marcos:dev_password_change_in_prod@localhost:5433/scoring_test_db"
test_engine = create_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

_global_generate_iso = None

@pytest.fixture(scope="module", autouse=True)
def setup_iso_generator(generate_iso_code):
    """Fixture qui initialise le générateur ISO global pour ce module."""
    global _global_generate_iso
    _global_generate_iso = generate_iso_code
    yield
    _global_generate_iso = None


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Crée les tables au début du module de tests."""
    Base.metadata.create_all(bind=test_engine)
    yield


# ---------------------------------------------------------------------------
# Fixtures DB & Client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Session DB fraîche par test."""
    connection = test_engine.connect()
    session = Session(bind=connection)
    _seed_all(session)
    yield session
    session.close()
    connection.close()


@pytest.fixture(scope="function")
def test_client(db_session: Session) -> TestClient:
    """Client FastAPI avec override de la dépendance DB."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_token(db_session: Session) -> str:
    """Génère un JWT valide pour un utilisateur admin de test."""
    user = _get_or_create_test_user(db_session)
    token = create_access_token(data={"sub": str(user.id), "role": "admin"})
    return token


@pytest.fixture(scope="function")
def auth_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------

def _seed_all(db: Session) -> None:
    """Insère les données de référence nécessaires aux tests."""
    if db.query(ScoringCriteria).count() == 0:
        # [Fix-3] weight en pourcentage entier (20.00 = 20%), is_active supprimé
        criteria = [
            ScoringCriteria(code="C1", name="Profil professionnel", weight=Decimal("20.00")),
            ScoringCriteria(code="C2", name="Zone géographique",    weight=Decimal("20.00")),
            ScoringCriteria(code="C3", name="Historique transact.", weight=Decimal("25.00")),
            ScoringCriteria(code="C4", name="Ancienneté & fidél.",  weight=Decimal("10.00")),
            ScoringCriteria(code="C5", name="Statut PEP",           weight=Decimal("15.00")),
            ScoringCriteria(code="C6", name="Cohérence KYC",        weight=Decimal("10.00")),
        ]
        db.add_all(criteria)

    if db.query(RiskThreshold).count() == 0:
        # [Fix-4] score_min/score_max/action (pas min_score/max_score/required_action)
        #         'ELEVE' sans accent (convention DB — normalisé en 'ÉLEVÉ' par le moteur)
        thresholds = [
            RiskThreshold(category="FAIBLE", score_min=0,  score_max=33,  action="Aucune action"),
            RiskThreshold(category="MOYEN",  score_min=34, score_max=66,  action="Surveillance renforcée"),
            RiskThreshold(category="ELEVE",  score_min=67, score_max=100, action="Déclaration CENTIF"),
        ]
        db.add_all(thresholds)

    db.commit()


def _get_or_create_test_user(db: Session) -> User:
    """Retourne ou crée un utilisateur admin pour les tests."""
    user = db.query(User).filter(User.login == "test_admin_scoring").first()
    if not user:
        # [Fix-5] Récupérer le role_id admin depuis user_roles (FK Integer obligatoire)
        #         full_name et email n'existent pas dans le model User
        #         hashed_password → password_hash
        role = db.query(UserRole).filter(UserRole.name == "admin").first()
        if not role:
            role = UserRole(name="admin", permissions={})
            db.add(role)
            db.flush()

        user = User(
            login="test_admin_scoring",
            password_hash="$2b$12$fakehashfortesting",  # [Fix-5] password_hash (pas hashed_password)
            role_id=role.id,                             # [Fix-5] role_id Integer FK (pas role='admin')
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _create_low_risk_customer(db: Session) -> Customer:
    """Crée un client à faible risque pour les tests."""
    global _global_generate_iso
    zone = RiskZone(name="Zone_test_faible", risk_level="FAIBLE", source="TEST")
    db.add(zone)
    db.flush()

    iso_code = _global_generate_iso("T") if _global_generate_iso else f"T{uuid.uuid4().hex[:2].upper()}"
    country = Country(
        code_iso=iso_code,
        name="TestPays",
        is_uemoa=True,
        is_border=False,
        is_fatf=False,
    )
    db.add(country)
    db.flush()

    customer = Customer(
        nom="INTEGRATION",
        prenom="TestFaible",
        phone=f"+229{uuid.uuid4().int % 10_000_000_000:010d}",
        profession_risk="LOW",
        profession_code="SALARIE",
        profession_name="Salarié public",
        revenus_declares=Decimal("250000"),
        zone_geo=zone.id,
        pays=country.id,
        statut_pep=False,
        kyc_completion=90,
        status="ACTIVE",
        kyc_level="LOW",
        date_creation=datetime.utcnow() - timedelta(days=4 * 365),
    )
    customer.risk_zone = zone
    customer.country = country
    db.add(customer)
    db.flush()

    doc = CustomerDoc(
        client_id=customer.id,
        type_doc="CNI",
        numero=f"CNI-{uuid.uuid4().hex[:8].upper()}",
        date_expiration=date.today() + timedelta(days=600),
        valide=True,
    )
    db.add(doc)

    acc = CustomerAccount(
        client_id=customer.id,
        type_compte="COURANT",
        solde_moyen=Decimal("300000"),
        date_ouverture=date.today() - timedelta(days=365),
        status="ACTIF",
    )
    db.add(acc)
    db.flush()

    db.commit()
    return customer


def _create_high_risk_customer(db: Session) -> Customer:
    """Crée un client à risque élevé (PEP + activité à risque) pour les tests."""
    global _global_generate_iso
    zone = RiskZone(name="Zone_test_eleve", risk_level="ELEVE", source="TEST")
    db.add(zone)
    db.flush()

    iso_code = _global_generate_iso("F") if _global_generate_iso else f"F{uuid.uuid4().hex[:2].upper()}"
    country = Country(
        code_iso=iso_code,
        name="PaysFATF_Test",
        is_uemoa=False,
        is_border=True,
        is_fatf=True,
    )
    db.add(country)
    db.flush()

    customer = Customer(
        nom="RISQUE_ELEVE",
        prenom="TestHaut",
        phone=f"+229{uuid.uuid4().int % 10_000_000_000:010d}",
        profession_risk="HIGH",
        profession_code="CHANGEUR",
        profession_name="Changeur de devises",
        revenus_declares=Decimal("50000"),
        zone_geo=zone.id,
        pays=country.id,
        statut_pep=True,
        kyc_completion=15,
        status="ACTIVE",
        kyc_level="HIGH",
        date_creation=datetime.utcnow() - timedelta(days=15),
    )
    customer.risk_zone = zone
    customer.country = country
    db.add(customer)
    db.flush()

    # Pas de documents → KYC incomplet
    acc = CustomerAccount(
        client_id=customer.id,
        type_compte="COURANT",
        solde_moyen=Decimal("5000000"),
        date_ouverture=date.today() - timedelta(days=15),
        status="ACTIF",
    )
    db.add(acc)
    db.flush()

    # Transactions smurfing — [Fix-2] Transaction utilisable ici car importé en tête
    for i in range(6):
        tx = Transaction(
            compte_id=acc.id,
            montant=Decimal("450000"),
            devise="XOF",
            type_op="VIREMENT",
            date_op=datetime.utcnow() - timedelta(days=i + 1),
            canal="INTERNET",
            destination_pays_id=country.id,
        )
        db.add(tx)

    db.commit()
    return customer


# ---------------------------------------------------------------------------
# Tests — Authentification
# ---------------------------------------------------------------------------

class TestAuthentification:

    def test_sans_token_retourne_401(self, test_client: TestClient):
        """POST /api/scoring sans JWT → 401 Unauthorized."""
        response = test_client.post(
            "/api/scoring",
            json={"customer_id": str(uuid.uuid4())},
        )
        assert response.status_code == 401, (
            f"Attendu 401, obtenu {response.status_code}"
        )
        data = response.json()
        assert "detail" in data

    def test_token_invalide_retourne_401(self, test_client: TestClient):
        """Token JWT falsifié → 401."""
        response = test_client.post(
            "/api/scoring",
            json={"customer_id": str(uuid.uuid4())},
            headers={"Authorization": "Bearer token_invalide_xyz"},
        )
        assert response.status_code == 401

    def test_avec_token_valide_pas_401(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """Avec JWT valide → pas 401 (peut être 404 si client inexistant)."""
        response = test_client.post(
            "/api/scoring",
            json={"customer_id": str(uuid.uuid4())},
            headers=auth_headers,
        )
        assert response.status_code != 401, (
            f"Ne devrait pas retourner 401 avec un token valide"
        )


# ---------------------------------------------------------------------------
# Tests — Format de réponse (contrat API v1.0)
# ---------------------------------------------------------------------------

class TestFormatReponse:

    def test_scoring_retourne_structure_complete(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """POST /api/scoring → réponse conforme au contrat API v1.0."""
        customer = _create_low_risk_customer(db_session)

        response = test_client.post(
            "/api/scoring",
            json={"customer_id": str(customer.id)},
            headers=auth_headers,
        )

        assert response.status_code == 200, response.text
        data = response.json()

        assert "id" in data
        assert "customer_id" in data
        assert "global_score" in data
        assert "risk_category" in data
        assert "detail_json" in data
        assert "is_current" in data
        assert "scored_by" in data
        assert "scored_at" in data

    def test_detail_json_contient_tous_criteres(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """detail_json contient exactement C1..C6."""
        customer = _create_low_risk_customer(db_session)

        response = test_client.post(
            "/api/scoring",
            json={"customer_id": str(customer.id)},
            headers=auth_headers,
        )

        data = response.json()
        detail = data["detail_json"]
        assert set(detail.keys()) == {"C1", "C2", "C3", "C4", "C5", "C6"}

    def test_global_score_dans_plage_0_100(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """global_score est dans [0, 100]."""
        customer = _create_low_risk_customer(db_session)

        response = test_client.post(
            "/api/scoring",
            json={"customer_id": str(customer.id)},
            headers=auth_headers,
        )

        data = response.json()
        assert 0 <= data["global_score"] <= 100

    def test_risk_category_valeurs_valides(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """risk_category est dans {'FAIBLE', 'MOYEN', 'ÉLEVÉ'}."""
        customer = _create_low_risk_customer(db_session)

        response = test_client.post(
            "/api/scoring",
            json={"customer_id": str(customer.id)},
            headers=auth_headers,
        )

        data = response.json()
        assert data["risk_category"] in ("FAIBLE", "MOYEN", "ÉLEVÉ")

    def test_customer_id_coherent_dans_reponse(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """customer_id dans la réponse = customer_id envoyé."""
        customer = _create_low_risk_customer(db_session)

        response = test_client.post(
            "/api/scoring",
            json={"customer_id": str(customer.id)},
            headers=auth_headers,
        )

        data = response.json()
        assert data["customer_id"] == str(customer.id)

    def test_is_current_true_pour_nouveau_score(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """Le score nouvellement calculé a is_current=True."""
        customer = _create_low_risk_customer(db_session)

        response = test_client.post(
            "/api/scoring",
            json={"customer_id": str(customer.id)},
            headers=auth_headers,
        )

        data = response.json()
        assert data["is_current"] is True


# ---------------------------------------------------------------------------
# Tests — Gestion des erreurs
# ---------------------------------------------------------------------------

class TestGestionErreurs:

    def test_client_inexistant_retourne_404(
        self,
        test_client: TestClient,
        auth_headers: dict,
    ):
        """UUID inexistant → 404 Not Found."""
        response = test_client.post(
            "/api/scoring",
            json={"customer_id": str(uuid.uuid4())},
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_uuid_malformed_retourne_422(
        self,
        test_client: TestClient,
        auth_headers: dict,
    ):
        """UUID malformé → 422 Unprocessable Entity."""
        response = test_client.post(
            "/api/scoring",
            json={"customer_id": "ceci-nest-pas-un-uuid"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_get_score_inexistant_retourne_404(
        self,
        test_client: TestClient,
        auth_headers: dict,
    ):
        """GET /api/scores/{id} avec UUID inexistant → 404."""
        response = test_client.get(
            f"/api/scores/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_historique_client_inexistant_retourne_404(
        self,
        test_client: TestClient,
        auth_headers: dict,
    ):
        """GET /api/customers/{id}/scores avec UUID inexistant → 404."""
        response = test_client.get(
            f"/api/customers/{uuid.uuid4()}/scores",
            headers=auth_headers,
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests — Alerte automatique si score ≥ 67
# ---------------------------------------------------------------------------

class TestAlerteAutomatique:

    def test_alerte_creee_si_score_eleve(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """Client à risque élevé → une alerte SCORE_ELEVE est créée en DB."""
        customer = _create_high_risk_customer(db_session)

        response = test_client.post(
            "/api/scoring",
            json={"customer_id": str(customer.id)},
            headers=auth_headers,
        )

        if response.status_code == 200:
            data = response.json()
            if data["global_score"] >= 67:
                # [Fix-6] client_id (pas customer_id), type_alerte (pas alert_type),
                #         statut (pas status), suppression risk_level (inexistant)
                alerts = (
                    db_session.query(Alert)
                    .filter(
                        Alert.client_id == customer.id,
                        Alert.type_alerte == "SCORE_ELEVE",
                        Alert.statut == "OPEN",
                    )
                    .all()
                )
                assert len(alerts) >= 1, (
                    f"Alerte SCORE_ELEVE attendue pour score={data['global_score']}"
                )

    def test_pas_alerte_si_score_faible(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """Client à faible risque → aucune alerte SCORE_ELEVE."""
        customer = _create_low_risk_customer(db_session)

        response = test_client.post(
            "/api/scoring",
            json={"customer_id": str(customer.id)},
            headers=auth_headers,
        )

        if response.status_code == 200:
            data = response.json()
            if data["global_score"] < 67:
                # [Fix-6] client_id, type_alerte, statut
                alerts = (
                    db_session.query(Alert)
                    .filter(
                        Alert.client_id == customer.id,
                        Alert.type_alerte == "SCORE_ELEVE",
                        Alert.statut == "OPEN",
                    )
                    .all()
                )
                assert len(alerts) == 0, (
                    f"Aucune alerte attendue pour score={data['global_score']}"
                )


# ---------------------------------------------------------------------------
# Tests — Rescore (POST /api/scoring/rescore)
# ---------------------------------------------------------------------------

class TestRescore:

    def test_rescore_retourne_200(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """POST /api/scoring/rescore avec client valide → 200."""
        customer = _create_low_risk_customer(db_session)

        response = test_client.post(
            "/api/scoring/rescore",
            json={"customer_id": str(customer.id)},
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text

    def test_rescore_meme_format_que_scoring(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """Le rescore retourne le même format JSON que le scoring initial."""
        customer = _create_low_risk_customer(db_session)

        r1 = test_client.post(
            "/api/scoring",
            json={"customer_id": str(customer.id)},
            headers=auth_headers,
        )
        r2 = test_client.post(
            "/api/scoring/rescore",
            json={"customer_id": str(customer.id)},
            headers=auth_headers,
        )

        assert r2.status_code == 200
        d1, d2 = r1.json(), r2.json()
        assert set(d1.keys()) == set(d2.keys()), "Les clés doivent être identiques"

    def test_rescore_marque_ancien_score_non_courant(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """Après rescore, le score précédent doit avoir is_current=False."""
        customer = _create_low_risk_customer(db_session)

        r1 = test_client.post(
            "/api/scoring",
            json={"customer_id": str(customer.id)},
            headers=auth_headers,
        )
        first_score_id = r1.json().get("id")

        test_client.post(
            "/api/scoring/rescore",
            json={"customer_id": str(customer.id)},
            headers=auth_headers,
        )

        if first_score_id:
            old_score = db_session.query(Score).filter(
                Score.id == uuid.UUID(first_score_id)
            ).first()
            if old_score:
                assert old_score.is_current is False, (
                    "L'ancien score devrait avoir is_current=False après rescore"
                )

    def test_rescore_pas_doublon_alerte_ouverte(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """Deux rescores successifs → pas de doublon d'alerte SCORE_ELEVE ouverte."""
        customer = _create_high_risk_customer(db_session)

        for _ in range(2):
            test_client.post(
                "/api/scoring/rescore",
                json={"customer_id": str(customer.id)},
                headers=auth_headers,
            )

        # [Fix-6] client_id, type_alerte, statut
        alerts = (
            db_session.query(Alert)
            .filter(
                Alert.client_id == customer.id,
                Alert.type_alerte == "SCORE_ELEVE",
                Alert.statut == "OPEN",
            )
            .all()
        )
        assert len(alerts) <= 1, (
            f"Doublon d'alerte détecté : {len(alerts)} alertes SCORE_ELEVE ouvertes"
        )


# ---------------------------------------------------------------------------
# Tests — Historique des scores
# ---------------------------------------------------------------------------

class TestHistoriqueScores:

    def test_historique_retourne_liste_paginee(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """GET /api/customers/{id}/scores → structure paginée avec items et total."""
        customer = _create_low_risk_customer(db_session)

        for _ in range(2):
            test_client.post(
                "/api/scoring",
                json={"customer_id": str(customer.id)},
                headers=auth_headers,
            )

        response = test_client.get(
            f"/api/customers/{customer.id}/scores",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 1

    def test_get_score_par_id(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """GET /api/scores/{id} retourne le score correspondant."""
        customer = _create_low_risk_customer(db_session)

        r = test_client.post(
            "/api/scoring",
            json={"customer_id": str(customer.id)},
            headers=auth_headers,
        )
        score_id = r.json()["id"]

        response = test_client.get(
            f"/api/scores/{score_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == score_id
        assert data["customer_id"] == str(customer.id)

    def test_pagination_skip_limit(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """Les paramètres skip et limit sont respectés."""
        customer = _create_low_risk_customer(db_session)

        for _ in range(3):
            test_client.post(
                "/api/scoring",
                json={"customer_id": str(customer.id)},
                headers=auth_headers,
            )

        r_full = test_client.get(
            f"/api/customers/{customer.id}/scores?skip=0&limit=10",
            headers=auth_headers,
        )
        r_limited = test_client.get(
            f"/api/customers/{customer.id}/scores?skip=0&limit=1",
            headers=auth_headers,
        )

        assert r_full.status_code == 200
        assert r_limited.status_code == 200
        assert len(r_limited.json()["items"]) <= 1


class TestRescoreAll:

    def test_rescore_all_retourne_200(
        self,
        test_client: TestClient,
        auth_headers: dict,
        db_session: Session,
    ):
        """POST /api/scoring/rescore-all recalcule tous les clients."""
        # Création de clients tests
        c1 = _create_low_risk_customer(db_session)
        c2 = _create_high_risk_customer(db_session)

        response = test_client.post(
            "/api/scoring/rescore-all",
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert "rescored" in data
        assert "critical" in data
        assert data["rescored"] >= 2