import sys
import os


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Maintenant les imports de l'application fonctionnent
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user_roles import UserRole
from app.models.users import User
from app.models.countries import Country
from app.models.risk_zones import RiskZone
from app.models.scoring_criteria import ScoringCriteria
from app.models.risk_thresholds import RiskThreshold
from app.auth.security import hash_password, create_access_token

# ── Base de données de test ───────────────────────────────────────────────────
TEST_DATABASE_URL = "postgresql://marcos:dev_password_change_in_prod@localhost:5433/scoring_test_db"

engine_test = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


#Fixtures DB

@pytest.fixture(scope="session")
def db_setup():
    """Crée toutes les tables au début de la session de tests."""
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(scope="function")
def db(db_setup):
    """
    Session DB par test — rollback automatique après chaque test.
    Garantit l'isolation entre les tests.
    """
    connection = engine_test.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db):
    """TestClient FastAPI avec DB de test injectée."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Fixtures données de référence ─────────────────────────────────────────────

@pytest.fixture(scope="function")
def reference_data(db):
    """Insère les données de référence minimales pour les tests."""
    # Rôles
    role_admin = UserRole(name="admin", permissions={
        "can_read_clients": True, "can_create_clients": True,
        "can_rescore": True, "can_export": True,
        "can_manage_users": True, "can_configure": True,
    })
    role_compliance = UserRole(name="compliance_officer", permissions={
        "can_read_clients": True, "can_rescore": True,
        "can_export": True, "can_manage_alerts": True,
    })
    db.add_all([role_admin, role_compliance])
    db.flush()

    # Pays
    benin = Country(code_iso="BJ", name="Bénin", is_uemoa=True, is_border=False, is_fatf=False)
    nigeria = Country(code_iso="NG", name="Nigeria", is_uemoa=False, is_border=True, is_fatf=False)
    db.add_all([benin, nigeria])
    db.flush()

    # Zones de risque
    zone_urbaine = RiskZone(name="URBAINE", risk_level="FAIBLE", source="BCEAO")
    zone_frontiere = RiskZone(name="FRONTIERE", risk_level="ELEVE", source="FATF")
    db.add_all([zone_urbaine, zone_frontiere])
    db.flush()

    # Critères de scoring
    criteria = [
        ScoringCriteria(code="C1", weight=20.00, name="Profil professionnel"),
        ScoringCriteria(code="C2", weight=20.00, name="Zone géographique"),
        ScoringCriteria(code="C3", weight=25.00, name="Historique transactionnel"),
        ScoringCriteria(code="C4", weight=10.00, name="Ancienneté et fidélité"),
        ScoringCriteria(code="C5", weight=15.00, name="Statut PEP"),
        ScoringCriteria(code="C6", weight=10.00, name="Cohérence KYC"),
    ]
    db.add_all(criteria)
    db.flush()

    # Seuils de risque
    thresholds = [
        RiskThreshold(category="FAIBLE", score_min=0,  score_max=33, action="Vigilance standard"),
        RiskThreshold(category="MOYEN",  score_min=34, score_max=66, action="Vigilance renforcée"),
        RiskThreshold(category="ELEVE",  score_min=67, score_max=100, action="Déclaration SAR"),
    ]
    db.add_all(thresholds)
    db.flush()

    db.commit()

    return {
        "role_admin": role_admin,
        "role_compliance": role_compliance,
        "benin": benin,
        "nigeria": nigeria,
        "zone_urbaine": zone_urbaine,
        "zone_frontiere": zone_frontiere,
    }


@pytest.fixture(scope="function")
def admin_user(db, reference_data):
    """Crée un utilisateur admin pour les tests."""
    user = User(
        login="test_admin",
        password_hash=hash_password("testpass123"),
        role_id=reference_data["role_admin"].id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def compliance_user(db, reference_data):
    """Crée un compliance officer pour les tests."""
    user = User(
        login="test_compliance",
        password_hash=hash_password("testpass123"),
        role_id=reference_data["role_compliance"].id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_token(admin_user):
    """Token JWT admin valide."""
    return create_access_token({
        "sub": str(admin_user.id),
        "role": "admin"
    })


@pytest.fixture(scope="function")
def compliance_token(compliance_user):
    """Token JWT compliance officer valide."""
    return create_access_token({
        "sub": str(compliance_user.id),
        "role": "compliance_officer"
    })


@pytest.fixture(scope="function")
def admin_headers(admin_token):
    """Headers HTTP avec token admin."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="function")
def compliance_headers(compliance_token):
    """Headers HTTP avec token compliance officer."""
    return {"Authorization": f"Bearer {compliance_token}"}