"""
tests/unit/test_scoring.py
===========================
Tests unitaires du moteur de scoring LBC/FT — RiskGuard.

Chaque test couvre un cas précis de la grille de notation (CDC pages 6-7).
La session DB est réelle mais wrapped dans un SAVEPOINT avec rollback final
pour garantir l'isolation des tests (pas de données persistées).

Prérequis :
  - Variables d'env DATABASE_URL configurées (voir conftest.py)
  - Tables migrées (alembic upgrade head)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.countries import Country
from app.models.customer_accounts import CustomerAccount
from app.models.customer_docs import CustomerDoc  # fichier : customer_docs.py
from app.models.customers import Customer
from app.models.pep_list import PepEntry
from app.models.risk_thresholds import RiskThreshold
from app.models.risk_zones import RiskZone
from app.models.scoring_criteria import ScoringCriteria
from app.models.transactions import Transaction
from app.services.scoring import ScoringEngine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "postgresql://marcos:dev_password_change_in_prod@localhost:5433/scoring_test_db"

@pytest.fixture(scope="module")
def db_engine():
    """Crée un engine PostgreSQL et les tables pour la durée du module de tests."""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db(db_engine, generate_iso_code) -> Generator[Session, None, None]:
    """
    Fournit une session DB fraîche par test.
    Les tables sont créées au niveau du module, les données sont isolées
    par le rollback implicite de la fermeture de connexion.
    """
    connection = db_engine.connect()
    session = Session(bind=connection)

    _seed_scoring_params(session)

    yield session

    session.close()
    connection.close()


def _seed_scoring_params(db: Session) -> None:
    """Insère les critères et seuils de scoring si absents."""
    if db.query(ScoringCriteria).count() == 0:
        # weight est en pourcentage entier (20.00 = 20%), conformément au model
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
        # Champs du model : score_min, score_max, action (pas min_score/max_score/required_action)
        thresholds = [
            RiskThreshold(category="FAIBLE", score_min=0,  score_max=33,  action="Aucune action"),
            RiskThreshold(category="MOYEN",  score_min=34, score_max=66,  action="Surveillance renforcée"),
            RiskThreshold(category="ELEVE",  score_min=67, score_max=100, action="Déclaration CENTIF"),
        ]
        db.add_all(thresholds)

    db.flush()


# Stockage global de generate_iso_code pour l'utiliser dans les helpers
_global_generate_iso = None

@pytest.fixture(scope="module", autouse=True)
def setup_iso_generator(generate_iso_code):
    """Fixture qui initialise le générateur ISO global pour ce module."""
    global _global_generate_iso
    _global_generate_iso = generate_iso_code
    yield
    _global_generate_iso = None


# ---------------------------------------------------------------------------
# Helpers constructeurs de fixtures
# ---------------------------------------------------------------------------

def _make_country(db: Session, *, is_border=False, is_fatf=False, is_uemoa=True) -> Country:
    global _global_generate_iso
    iso_code = _global_generate_iso("T") if _global_generate_iso else f"T{uuid.uuid4().hex[:2].upper()}"
    country = Country(
        code_iso=iso_code,  # ← Utilise le générateur global ou fallback
        name="TestPays",
        is_uemoa=is_uemoa,
        is_border=is_border,
        is_fatf=is_fatf,
    )
    db.add(country)
    db.flush()
    return country


def _make_zone(db: Session, risk_level: str = "FAIBLE") -> RiskZone:
    zone = RiskZone(name=f"Zone_{risk_level}", risk_level=risk_level, source="TEST")
    db.add(zone)
    db.flush()
    return zone


def _make_customer(
    db: Session,
    *,
    profession_risk: str = "LOW",
    revenus: float = 200_000,
    zone: RiskZone | None = None,
    country: Country | None = None,
    statut_pep: bool = False,
    kyc_completion: int = 90,
    date_creation: datetime | None = None,
    nom: str = "TEST",
    prenom: str = "Client",
) -> Customer:
    if date_creation is None:
        date_creation = datetime.now(timezone.utc) - timedelta(days=4 * 365)

    customer = Customer(
        nom=nom,
        prenom=prenom,
        phone=f"+229{uuid.uuid4().int % 10_000_000_000:010d}",
        profession_risk=profession_risk,
        profession_code="AGRI_MARAICH",
        profession_name="Agriculteur",
        revenus_declares=Decimal(str(revenus)),
        zone_geo=zone.id if zone else None,
        pays=country.id if country else None,
        statut_pep=statut_pep,
        kyc_completion=kyc_completion,
        status="ACTIVE",
        kyc_level="LOW",
        date_creation=date_creation,
    )
    if zone:
        customer.risk_zone = zone
    if country:
        customer.country = country
    db.add(customer)
    db.flush()
    return customer


def _make_account(db: Session, customer: Customer) -> CustomerAccount:
    acc = CustomerAccount(
        client_id=customer.id,
        type_compte="COURANT",
        solde_moyen=Decimal("500000"),
        date_ouverture=date.today() - timedelta(days=365),
        status="ACTIF",
    )
    db.add(acc)
    db.flush()
    return acc


def _make_doc(
    db: Session,
    customer: Customer,
    *,
    expiration_delta_days: int = 365,
) -> CustomerDoc:
    doc = CustomerDoc(
        client_id=customer.id,
        type_doc="CNI",
        numero=f"DOC-{uuid.uuid4().hex[:8].upper()}",
        date_expiration=date.today() + timedelta(days=expiration_delta_days),
    )
    db.add(doc)
    db.flush()
    return doc


def _make_transaction(
    db: Session,
    account: CustomerAccount,
    *,
    montant: float = 100_000,
    type_op: str = "DEPOT",
    days_ago: int = 10,
    pays_dest_id: int | None = None,
) -> Transaction:
    tx = Transaction(
        compte_id=account.id,
        montant=Decimal(str(montant)),
        devise="XOF",
        type_op=type_op,
        date_op=datetime.now(timezone.utc) - timedelta(days=days_ago),
        canal="GUICHET",
        destination_pays_id=pays_dest_id,
    )
    db.add(tx)
    db.flush()
    return tx


# ---------------------------------------------------------------------------
# CAS 1 — Client standard → score FAIBLE (< 34)
# ---------------------------------------------------------------------------

class TestClientStandard:
    """Client modèle : salarié formel, zone urbaine stable, KYC complet, ancien."""

    def test_score_faible(self, db: Session):
        zone = _make_zone(db, "FAIBLE")
        country = _make_country(db, is_uemoa=True)
        customer = _make_customer(
            db,
            profession_risk="LOW",
            revenus=300_000,
            zone=zone,
            country=country,
            kyc_completion=95,
            date_creation=datetime.now(timezone.utc) - timedelta(days=4 * 365),
        )
        acc = _make_account(db, customer)
        _make_doc(db, customer, expiration_delta_days=500)

        # Transactions régulières cohérentes avec revenus
        for i in range(6):
            _make_transaction(db, acc, montant=150_000, type_op="DEPOT", days_ago=15 * i + 1)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        assert result["global_score"] < 34, (
            f"Score attendu < 34 (FAIBLE), obtenu {result['global_score']}"
        )
        assert result["risk_category"] == "FAIBLE"
        assert set(result["detail_json"].keys()) == {"C1", "C2", "C3", "C4", "C5", "C6"}

    def test_detail_sum_equals_global(self, db: Session):
        """La somme des contributions doit être égale au global_score (arrondi)."""
        zone = _make_zone(db, "FAIBLE")
        customer = _make_customer(db, zone=zone, kyc_completion=80)
        _make_doc(db, customer)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        detail_sum = round(sum(result["detail_json"].values()))
        assert abs(detail_sum - result["global_score"]) <= 1, (
            f"Somme détail={detail_sum} ≠ global_score={result['global_score']}"
        )


# ---------------------------------------------------------------------------
# CAS 2 — Client PEP déclaré → C5 = contribution maximale
# ---------------------------------------------------------------------------

class TestClientPEP:

    def test_c5_max_si_correspondance_liste_pep_active(self, db: Session):
        """Correspondance nom/prénom dans pep_list (active=True) → C5 = 100, statut_pep sync True."""
        country = _make_country(db)
        pep = PepEntry(
            nom="BIOKOU",
            prenom="Achille",
            fonction="Ministre",
            active=True,
            pays=country.id,
        )
        db.add(pep)
        db.flush()

        customer = _make_customer(
            db,
            nom="BIOKOU",
            prenom="Achille",
            statut_pep=False,
            kyc_completion=70,
        )
        _make_doc(db, customer)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        expected_c5 = round(100 * 0.15, 4)
        assert result["detail_json"]["C5"] == pytest.approx(expected_c5, abs=0.5)
        assert customer.statut_pep is True

    def test_c5_zero_si_non_pep(self, db: Session):
        """Client sans lien PEP → C5 = 0, statut_pep sync False."""
        customer = _make_customer(db, statut_pep=True, kyc_completion=80)
        _make_doc(db, customer)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        assert result["detail_json"]["C5"] == 0.0
        assert customer.statut_pep is False


# ---------------------------------------------------------------------------
# CAS 3 — Zone frontalière → C2 élevé
# ---------------------------------------------------------------------------

class TestZoneFrontaliere:

    def test_c2_eleve_zone_frontaliere(self, db: Session):
        """Zone risque ELEVE → note C2 ≥ 51 → contribution ≥ 51 * 0.20 = 10.2."""
        zone = _make_zone(db, "ELEVE")
        country = _make_country(db, is_border=True)
        customer = _make_customer(db, zone=zone, country=country, kyc_completion=80)
        _make_doc(db, customer)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c2_contribution = result["detail_json"]["C2"]
        assert c2_contribution >= 10.2, (
            f"C2 contribution attendue ≥ 10.2, obtenue {c2_contribution}"
        )

    def test_c2_faible_zone_urbaine(self, db: Session):
        """Zone FAIBLE + pays UEMOA → C2 contribution faible."""
        zone = _make_zone(db, "FAIBLE")
        country = _make_country(db, is_uemoa=True)
        customer = _make_customer(db, zone=zone, country=country, kyc_completion=80)
        _make_doc(db, customer)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c2_contribution = result["detail_json"]["C2"]
        assert c2_contribution <= 8.0, (
            f"C2 contribution attendue ≤ 8.0, obtenue {c2_contribution}"
        )

    def test_c2_eleve_pays_fatf(self, db: Session):
        """Pays listé FATF → C2 contribution élevée quelle que soit la zone."""
        zone = _make_zone(db, "MOYEN")
        country = _make_country(db, is_fatf=True)
        customer = _make_customer(db, zone=zone, country=country, kyc_completion=75)
        _make_doc(db, customer)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c2_contribution = result["detail_json"]["C2"]
        assert c2_contribution >= 14.0, (
            f"C2 pays FATF attendue ≥ 14.0, obtenue {c2_contribution}"
        )


# ---------------------------------------------------------------------------
# CAS 4 — Smurfing → C3 élevé
# ---------------------------------------------------------------------------

class TestSmurfing:

    def test_c3_eleve_smurfing(self, db: Session):
        """
        Plusieurs transactions de montants ronds juste sous le seuil
        → détection smurfing → C3 contribution très élevée.
        """
        customer = _make_customer(db, revenus=100_000, kyc_completion=60)
        acc = _make_account(db, customer)
        _make_doc(db, customer)

        # 5 transactions de 450 000 XOF (multiple de 50k, < 500k) → smurfing
        for i in range(5):
            _make_transaction(
                db, acc,
                montant=450_000,
                type_op="VIREMENT",
                days_ago=i + 1,
            )

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c3_contribution = result["detail_json"]["C3"]
        # Note brute C3 = 85 → contribution = 85 * 0.25 = 21.25
        assert c3_contribution >= 20.0, (
            f"C3 smurfing attendue ≥ 20.0, obtenue {c3_contribution}"
        )

    def test_c3_faible_transactions_regulieres(self, db: Session):
        """Transactions régulières cohérentes avec revenus → C3 faible."""
        customer = _make_customer(db, revenus=300_000, kyc_completion=85)
        acc = _make_account(db, customer)
        _make_doc(db, customer)

        for i in range(4):
            _make_transaction(db, acc, montant=150_000, type_op="DEPOT", days_ago=20 * i + 5)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c3_contribution = result["detail_json"]["C3"]
        assert c3_contribution <= 5.0, (
            f"C3 régulier attendue ≤ 5.0, obtenue {c3_contribution}"
        )

    def test_c3_eleve_destination_pays_fatf(self, db: Session):
        """Transactions vers pays FATF → C3 pénalisé."""
        fatf_country = _make_country(db, is_fatf=True)
        customer = _make_customer(db, revenus=200_000, kyc_completion=70)
        acc = _make_account(db, customer)
        _make_doc(db, customer)

        for i in range(4):
            _make_transaction(
                db, acc,
                montant=180_000,
                type_op="VIREMENT",
                days_ago=i + 2,
                pays_dest_id=fatf_country.id,
            )

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c3_contribution = result["detail_json"]["C3"]
        assert c3_contribution >= 11.0, (
            f"C3 FATF attendue ≥ 11.0, obtenue {c3_contribution}"
        )

    def test_c3_minimal_sans_transactions(self, db: Session):
        """Client sans transactions → C3 = 10 (note minimale, pas de pénalité)."""
        customer = _make_customer(db, kyc_completion=80)
        _make_doc(db, customer)
        # Pas de compte ni de transaction

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        # Note brute C3 = 10 → contribution = 10 * 0.25 = 2.5
        c3_contribution = result["detail_json"]["C3"]
        assert c3_contribution <= 3.0, (
            f"C3 sans TX attendue ≤ 3.0, obtenue {c3_contribution}"
        )


# ---------------------------------------------------------------------------
# CAS 5 — KYC incomplet / document expiré → C6 élevé
# ---------------------------------------------------------------------------

class TestKYCIncomplet:

    def test_c6_eleve_doc_invalide(self, db: Session):
        """Document expiré → C6 contribution élevée."""
        customer = _make_customer(db, kyc_completion=40)
        _make_doc(db, customer, expiration_delta_days=-10)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c6_contribution = result["detail_json"]["C6"]
        # Note brute C6 ≥ 55 → contribution ≥ 55 * 0.10 = 5.5
        assert c6_contribution >= 5.0, (
            f"C6 doc invalide attendue ≥ 5.0, obtenue {c6_contribution}"
        )

    def test_c6_eleve_doc_expire(self, db: Session):
        """Document expiré (date_expiration passée) → C6 élevé."""
        customer = _make_customer(db, kyc_completion=50)
        _make_doc(db, customer, expiration_delta_days=-10)  # expiré

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c6_contribution = result["detail_json"]["C6"]
        assert c6_contribution >= 5.0

    def test_c6_eleve_sans_document(self, db: Session):
        """Aucun document → C6 maximal."""
        customer = _make_customer(db, kyc_completion=0)
        # Pas de doc

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c6_contribution = result["detail_json"]["C6"]
        # Note brute C6 = 85 → contribution = 85 * 0.10 = 8.5
        assert c6_contribution >= 8.0

    def test_c6_faible_dossier_complet(self, db: Session):
        """Dossier complet, revenus cohérents, docs valides → C6 faible."""
        customer = _make_customer(db, kyc_completion=95, revenus=200_000)
        acc = _make_account(db, customer)
        _make_doc(db, customer, expiration_delta_days=700)

        # Transactions cohérentes
        for i in range(3):
            _make_transaction(db, acc, montant=180_000, days_ago=30 * i + 5)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c6_contribution = result["detail_json"]["C6"]
        assert c6_contribution <= 3.0, (
            f"C6 dossier complet attendue ≤ 3.0, obtenue {c6_contribution}"
        )


# ---------------------------------------------------------------------------
# CAS 6 — Client très ancien (> 3 ans) → C4 bas
# ---------------------------------------------------------------------------

class TestAnciennete:

    def test_c4_faible_client_ancien(self, db: Session):
        """Client de plus de 3 ans → C4 note brute = 10 → contribution = 1.0."""
        customer = _make_customer(
            db,
            date_creation=datetime.now(timezone.utc) - timedelta(days=4 * 365),
            kyc_completion=80,
        )
        _make_doc(db, customer)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c4_contribution = result["detail_json"]["C4"]
        # 10 * 0.10 = 1.0
        assert c4_contribution <= 2.5, (
            f"C4 ancien attendue ≤ 2.5, obtenu {c4_contribution}"
        )

    def test_c4_eleve_client_recent(self, db: Session):
        """Client de moins de 6 mois → C4 élevé."""
        customer = _make_customer(
            db,
            date_creation=datetime.now(timezone.utc) - timedelta(days=30),
            kyc_completion=60,
        )
        _make_doc(db, customer)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c4_contribution = result["detail_json"]["C4"]
        # Note brute ≥ 75 → contribution ≥ 7.5
        assert c4_contribution >= 6.0, (
            f"C4 récent attendue ≥ 6.0, obtenu {c4_contribution}"
        )

    def test_c4_moyen_client_1_a_3_ans(self, db: Session):
        """Client entre 1 et 3 ans → C4 contribution intermédiaire."""
        customer = _make_customer(
            db,
            date_creation=datetime.now(timezone.utc) - timedelta(days=2 * 365),
            kyc_completion=70,
        )
        _make_doc(db, customer)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c4_contribution = result["detail_json"]["C4"]
        # Note brute = 35 → contribution = 3.5
        assert 2.0 <= c4_contribution <= 6.0, (
            f"C4 moyen attendue entre 2.0 et 6.0, obtenu {c4_contribution}"
        )


# ---------------------------------------------------------------------------
# CAS 7 — Profil professionnel à risque → C1 élevé
# ---------------------------------------------------------------------------

class TestProfilProfessionnel:

    def test_c1_faible_salarie_formel(self, db: Session):
        """Salarié formel (LOW) → C1 contribution faible."""
        customer = _make_customer(db, profession_risk="LOW", kyc_completion=80)
        _make_doc(db, customer)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c1_contribution = result["detail_json"]["C1"]
        # Note brute = 10 → contribution = 2.0
        assert c1_contribution <= 4.0

    def test_c1_eleve_activite_risque(self, db: Session):
        """Activité à risque élevé (HIGH) → C1 contribution élevée."""
        customer = _make_customer(db, profession_risk="HIGH", kyc_completion=60)
        _make_doc(db, customer)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c1_contribution = result["detail_json"]["C1"]
        # Note brute = 65 → contribution = 13.0
        assert c1_contribution >= 10.0

    def test_c1_max_sans_profession(self, db: Session):
        """Pas de profession renseignée → C1 maximal."""
        customer = _make_customer(db, profession_risk=None, kyc_completion=50)
        customer.profession_risk = None
        db.flush()
        _make_doc(db, customer)

        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        c1_contribution = result["detail_json"]["C1"]
        # Note brute = 85 → contribution = 17.0
        assert c1_contribution >= 15.0


# ---------------------------------------------------------------------------
# CAS 8 — Gestion des erreurs
# ---------------------------------------------------------------------------

class TestGestionErreurs:

    def test_client_inexistant_leve_valueerror(self, db: Session):
        """UUID inexistant → ValueError."""
        fake_id = uuid.uuid4()
        engine = ScoringEngine(db)

        with pytest.raises(ValueError, match="Client introuvable"):
            engine.calculate_score(fake_id)

    def test_result_keys_toujours_presents(self, db: Session):
        """Le résultat contient toujours global_score, risk_category, detail_json."""
        customer = _make_customer(db, kyc_completion=50)
        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        assert "global_score" in result
        assert "risk_category" in result
        assert "detail_json" in result
        assert result["risk_category"] in ("FAIBLE", "MOYEN", "ÉLEVÉ")

    def test_score_dans_plage_0_100(self, db: Session):
        """Le score global est toujours dans [0, 100]."""
        customer = _make_customer(
            db,
            profession_risk="HIGH",
            statut_pep=True,
            kyc_completion=0,
            revenus=0,
        )
        engine = ScoringEngine(db)
        result = engine.calculate_score(customer.id)

        assert 0 <= result["global_score"] <= 100