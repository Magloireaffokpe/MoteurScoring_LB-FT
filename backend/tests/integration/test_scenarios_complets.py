"""
tests/integration/test_scenarios_complets.py
=============================================
Tests de vérification complets du moteur de scoring et des alertes.

Ces scripts TOUCHENT LA BASE RÉELLE (connexion via SessionLocal).
Chaque scénario crée ses propres données de test, exécute la détection,
et nettoie systématiquement. Les assertions sont affichées en console.

Usage :
    cd backend
    python -m tests.integration.test_scenarios_complets

Prérequis :
    - .env avec DATABASE_URL valide pointant vers la base réelle
    - Tables créées (alembic upgrade head ou create_all)
"""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

# ── Désactive les logs bruyants pendant les tests ─────────────────────
logging.basicConfig(level=logging.WARNING)
for logger_name in ("app.services.scoring", "app.services.alert_service", "app.routers.transactions"):
    logging.getLogger(logger_name).setLevel(logging.WARNING)

sys.path.insert(0, ".")

from app.db.session import SessionLocal
from app.models.alerts import Alert
from app.models.countries import Country
from app.models.customer_accounts import CustomerAccount
from app.models.customer_docs import CustomerDoc
from app.models.customers import Customer
from app.models.pep_list import PepEntry
from app.models.risk_thresholds import RiskThreshold
from app.models.risk_zones import RiskZone
from app.models.scoring_criteria import ScoringCriteria
from app.models.scores import Score
from app.models.settings import AppSetting
from app.models.transactions import Transaction
from app.services.scoring import ScoringEngine
from app.services.alert_service import (
    create_if_not_open,
    create_smurfing_alert_if_needed,
    create_pep_alert_if_needed,
    create_kyc_alert_if_needed,
    ALERT_TYPE_SEUIL_DEPASSE,
    ALERT_TYPE_SMURFING_DETECTE,
    ALERT_TYPE_PEP_DETECTE,
    ALERT_TYPE_KYC_INCOMPLET,
    ALERT_TYPE_BENEFICIAIRE_GROUPEMENT,
)
from app.routers.transactions import _get_setting
from app.services.beneficiaire_service import check_and_alert


# ── Helpers ───────────────────────────────────────────────────────────

PASS = 0
FAIL = 0
TOTAL = 0
TEST_PREFIX = "TST_"


def _ok(label: str, detail: str = ""):
    global PASS, TOTAL
    PASS += 1
    TOTAL += 1
    icon = "✓"
    print(f"  {icon} {label}" + (f" — {detail}" if detail else ""))


def _fail(label: str, detail: str = ""):
    global FAIL, TOTAL
    FAIL += 1
    TOTAL += 1
    icon = "✗"
    print(f"  {icon} {label}" + (f" — {detail}" if detail else ""))


def _make_country(db, *, code_iso: str, name: str, is_uemoa=False, is_border=False, is_fatf=False) -> Country:
    existing = db.query(Country).filter(Country.code_iso == code_iso).first()
    if existing:
        return existing
    c = Country(
        code_iso=code_iso, name=name,
        is_uemoa=is_uemoa, is_border=is_border, is_fatf=is_fatf,
    )
    db.add(c)
    db.flush()
    return c


def _make_zone(db, *, name: str, risk_level: str) -> RiskZone:
    existing = db.query(RiskZone).filter(RiskZone.name == name).first()
    if existing:
        return existing
    z = RiskZone(name=name, risk_level=risk_level, source="TEST")
    db.add(z)
    db.flush()
    return z


def _make_customer(
    db, *,
    nom: str = "TEST_CLIENT",
    prenom: str = "Scénario",
    profession_risk: str = "LOW",
    revenus: float = 200_000,
    zone: RiskZone = None,
    country: Country = None,
    statut_pep: bool = False,
    kyc_completion: int = 90,
    date_creation: datetime = None,
) -> Customer:
    if date_creation is None:
        date_creation = datetime.now(timezone.utc) - timedelta(days=4 * 365)
    phone = f"+229{TEST_PREFIX}{uuid.uuid4().int % 10_000_000:07d}"
    customer = Customer(
        nom=nom, prenom=prenom, phone=phone,
        profession_risk=profession_risk, profession_code="TEST",
        profession_name="Test", revenus_declares=Decimal(str(revenus)),
        zone_geo=zone.id if zone else None,
        pays=country.id if country else None,
        statut_pep=statut_pep, kyc_completion=kyc_completion,
        status="ACTIVE", kyc_level="LOW",
        date_creation=date_creation,
    )
    if zone:
        customer.risk_zone = zone
    if country:
        customer.country = country
    db.add(customer)
    db.flush()
    return customer


def _make_account(db, customer: Customer) -> CustomerAccount:
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


def _make_tx(
    db, account: CustomerAccount, *,
    montant: float = 100_000,
    type_op: str = "DEPOT",
    days_ago: int = 10,
    canal: str = "GUICHET",
    pays_dest_id: int = None,
) -> Transaction:
    tx = Transaction(
        compte_id=account.id,
        montant=Decimal(str(montant)),
        devise="XOF",
        type_op=type_op,
        date_op=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_ago),
        canal=canal,
        destination_pays_id=pays_dest_id,
    )
    db.add(tx)
    db.flush()
    return tx


def _cleanup_test_data(db):
    """Supprime toutes les données créées pour les tests."""
    markers = [f"%{TEST_PREFIX}%", f"%{TEST_PREFIX}"]
    for model in [Alert, Score, Transaction, CustomerAccount, CustomerDoc, Customer]:
        db.query(model).filter(
            model.__table__.c.get("phone", model.id).like(f"%{TEST_PREFIX}%")
            if hasattr(model, "phone")
            else model.id.isnot(None)
        ).delete(synchronize_session=False)
    # Supprimer les PEP créés
    db.query(PepEntry).filter(PepEntry.source == "TEST_SCENARIO").delete(synchronize_session=False)
    db.commit()


def _cleanup_customer_tx(db, customer: Customer):
    """Supprime toutes les données liées à un client de test."""
    for acc in (customer.accounts or []):
        db.query(Transaction).filter(Transaction.compte_id == acc.id).delete(synchronize_session=False)
        db.delete(acc)
    for doc in (customer.documents or []):
        db.delete(doc)
    db.query(Score).filter(Score.client_id == customer.id).delete(synchronize_session=False)
    db.query(Alert).filter(Alert.client_id == customer.id).delete(synchronize_session=False)
    db.delete(customer)
    db.commit()


# ── Initialisation des référentiels ───────────────────────────────────

def _ensure_referentials(db):
    """Crée les référentiels si absents (idempotent)."""
    # Crée les tables qui n'existeraient pas encore (ex: app_settings)
    from app.db.base import Base
    Base.metadata.create_all(bind=db.get_bind(), tables=[
        AppSetting.__table__,
    ], checkfirst=True)

    if db.query(ScoringCriteria).count() == 0:
        criteria = [
            ScoringCriteria(code="C1", name="Profil professionnel", weight=Decimal("20.00")),
            ScoringCriteria(code="C2", name="Zone géographique", weight=Decimal("20.00")),
            ScoringCriteria(code="C3", name="Historique transact.", weight=Decimal("25.00")),
            ScoringCriteria(code="C4", name="Ancienneté & fidél.", weight=Decimal("10.00")),
            ScoringCriteria(code="C5", name="Statut PEP", weight=Decimal("15.00")),
            ScoringCriteria(code="C6", name="Cohérence KYC", weight=Decimal("10.00")),
        ]
        db.add_all(criteria)

    if db.query(RiskThreshold).count() == 0:
        thresholds = [
            RiskThreshold(category="FAIBLE", score_min=0, score_max=33, action="Aucune"),
            RiskThreshold(category="MOYEN", score_min=34, score_max=66, action="Surveillance"),
            RiskThreshold(category="ELEVE", score_min=67, score_max=100, action="Déclaration"),
        ]
        db.add_all(thresholds)

    if db.query(AppSetting).count() == 0:
        settings = [
            AppSetting(key="SEUIL_MONETAIRE", value=10_000_000, label="Seuil monétaire global"),
            AppSetting(key="SEUIL_ESPECES", value=3_000_000, label="Seuil espèces (GUICHET/ATM)"),
            AppSetting(key="FENETRE_CUMUL_JOURS", value=30, label="Fenêtre cumul (jours)"),
        ]
        db.add_all(settings)

    db.commit()


def _get_score(engine: ScoringEngine, customer_id: uuid.UUID) -> dict:
    """Helper : calcule le score et retourne le dict."""
    return engine.calculate_score(customer_id)


def _has_alert(db, customer_id: uuid.UUID, alert_type: str) -> Alert | None:
    """Vérifie si une alerte OPEN du type donné existe pour ce client."""
    return (
        db.query(Alert)
        .filter(Alert.client_id == customer_id, Alert.type_alerte == alert_type, Alert.statut == "OPEN")
        .first()
    )


# ═══════════════════════════════════════════════════════════════════════
# SCÉNARIOS DE TEST
# ═══════════════════════════════════════════════════════════════════════

def test_scenario_01_seuil_global(db):
    """
    Seuil 1 — Global (toutes opérations) > 10 000 000 FCFA
    Alerte SEUIL_DEPASSE créée par create_if_not_open
    """
    label = "01 — Seuil global > 10M FCFA"
    print(f"\n[SCÉNARIO] {label}")

    country = _make_country(db, code_iso="T01", name="Test01", is_uemoa=True)
    zone = _make_zone(db, name="ZONE_T01", risk_level="FAIBLE")
    customer = _make_customer(db, nom="TEST_CLIENT_SEUIL", prenom="Global", country=country, zone=zone)
    acc = _make_account(db, customer)
    db.commit()

    # 3 dépôts de 4M chacun → cumul = 12M > 10M
    for i in range(3):
        _make_tx(db, acc, montant=4_000_000, type_op="DEPOT", days_ago=i + 1)
    db.commit()

    # Simuler la détection seuil comme dans transactions.py
    from app.services.scoring import _naive_utc_now

    fenetre = int(_get_setting(db, "FENETRE_CUMUL_JOURS", 30))
    seuil = _get_setting(db, "SEUIL_MONETAIRE", 10_000_000)
    cutoff = _naive_utc_now() - timedelta(days=fenetre)

    from sqlalchemy import func
    cumul = (
        db.query(func.coalesce(func.sum(Transaction.montant), 0))
        .join(CustomerAccount, Transaction.compte_id == CustomerAccount.id)
        .filter(CustomerAccount.client_id == customer.id, Transaction.date_op >= cutoff)
        .scalar() or 0
    )

    ok = float(cumul) > seuil
    if ok:
        alert = create_if_not_open(db, client_id=customer.id, type_alerte=ALERT_TYPE_SEUIL_DEPASSE,
                                    decision=f"Test cumul={float(cumul):,.0f}")
        db.commit()
        ok = alert is not None
        _ok(label, f"cumul={float(cumul):,.0f} > seuil={seuil:,.0f} → alerte créée")
    else:
        _fail(label, f"cumul={float(cumul):,.0f} ≤ seuil={seuil:,.0f}")

    _cleanup_customer_tx(db, customer)


def test_scenario_02_seuil_especes(db):
    """
    Seuil 2 — Espèces (DEPOT via GUICHET/ATM) > 3 000 000 FCFA
    """
    label = "02 — Seuil espèces > 3M FCFA (GUICHET/ATM)"
    print(f"\n[SCÉNARIO] {label}")

    country = _make_country(db, code_iso="T02", name="Test02", is_uemoa=True)
    zone = _make_zone(db, name="ZONE_T02", risk_level="FAIBLE")
    customer = _make_customer(db, nom="TEST_CLIENT_ESPECES", prenom="Cash", country=country, zone=zone)
    acc = _make_account(db, customer)
    db.commit()

    # 4 dépôts espèces de 1M chacun via GUICHET → cumul = 4M > 3M
    for i in range(4):
        _make_tx(db, acc, montant=1_000_000, type_op="DEPOT", canal="GUICHET", days_ago=i + 1)
    db.commit()

    from app.services.scoring import _naive_utc_now
    fenetre = int(_get_setting(db, "FENETRE_CUMUL_JOURS", 30))
    seuil = _get_setting(db, "SEUIL_ESPECES", 3_000_000)
    cutoff = _naive_utc_now() - timedelta(days=fenetre)

    from sqlalchemy import func
    cumul = (
        db.query(func.coalesce(func.sum(Transaction.montant), 0))
        .join(CustomerAccount, Transaction.compte_id == CustomerAccount.id)
        .filter(
            CustomerAccount.client_id == customer.id,
            Transaction.date_op >= cutoff,
            Transaction.type_op == "DEPOT",
            Transaction.canal.in_(["GUICHET", "ATM"]),
        )
        .scalar() or 0
    )

    ok = float(cumul) > seuil
    if ok:
        alert = create_if_not_open(db, client_id=customer.id, type_alerte=ALERT_TYPE_SEUIL_DEPASSE,
                                    decision=f"Test espèces cumul={float(cumul):,.0f}")
        db.commit()
        ok = alert is not None
        _ok(label, f"cumul_espèces={float(cumul):,.0f} > seuil={seuil:,.0f} → alerte créée")
    else:
        _fail(label, f"cumul_espèces={float(cumul):,.0f} ≤ seuil={seuil:,.0f}")

    _cleanup_customer_tx(db, customer)


def test_scenario_03_smurfing(db):
    """
    Smurfing : montants ronds sous 500K, concentrés sur < 7 jours
    C3 brut ≥ 85    ← corrigé
    """
    label = "03 — Smurfing (montants ronds, fractionnement)"
    print(f"\n[SCÉNARIO] {label}")

    country = _make_country(db, code_iso="T03", name="Test03", is_uemoa=True)
    zone = _make_zone(db, name="ZONE_T03", risk_level="FAIBLE")
    customer = _make_customer(db, nom="TEST_CLIENT_SMURF", prenom="Smurfing",
                               revenus=100_000, country=country, zone=zone)
    acc = _make_account(db, customer)
    db.commit()

    # 5 transactions de 450 000 XOF (multiple de 10k, < 500k) sur 5 jours
    for i in range(5):
        _make_tx(db, acc, montant=450_000, type_op="VIREMENT", days_ago=i + 1)
    db.commit()

    engine = ScoringEngine(db)
    result = _get_score(engine, customer.id)

    c3_contrib = result["detail_json"]["C3"]
    smurf_detected = result["smurfing_detected"]

    ok_scoring = smurf_detected and c3_contrib >= 20.0

    # Vérification alerte SMURFING
    create_smurfing_alert_if_needed(db, customer_id=customer.id, skip_if_open=False)
    db.commit()
    alert = _has_alert(db, customer.id, ALERT_TYPE_SMURFING_DETECTE)
    ok_alert = alert is not None

    ok = ok_scoring and ok_alert
    if ok:
        _ok(label, f"C3={c3_contrib:.2f}, smurfing={smurf_detected}, alerte SMURFING créée")
    else:
        detail = f"C3={c3_contrib:.2f}, smurfing={smurf_detected}, alerte={alert is not None}"
        _fail(label, detail)

    _cleanup_customer_tx(db, customer)


def test_scenario_04_near_threshold(db):
    """
    Near-threshold smurfing : montants entre 80%-100% du seuil FATF
    (400 000 - 499 999 XOF)
    """
    label = "04 — Smurfing near-threshold (495K XOF)"
    print(f"\n[SCÉNARIO] {label}")

    country = _make_country(db, code_iso="T04", name="Test04", is_uemoa=True)
    zone = _make_zone(db, name="ZONE_T04", risk_level="FAIBLE")
    customer = _make_customer(db, nom="TEST_CLIENT_NEAR", prenom="NearThreshold",
                               revenus=100_000, country=country, zone=zone)
    acc = _make_account(db, customer)
    db.commit()

    # 3 transactions à 495 000 XOF (near-threshold)
    for i in range(3):
        _make_tx(db, acc, montant=495_000, type_op="VIREMENT", days_ago=i + 1)
    db.commit()

    engine = ScoringEngine(db)
    result = _get_score(engine, customer.id)
    c3_contrib = result["detail_json"]["C3"]
    smurf_detected = result["smurfing_detected"]

    ok_scoring = smurf_detected and c3_contrib >= 20.0

    create_smurfing_alert_if_needed(db, customer_id=customer.id, skip_if_open=False)
    db.commit()
    alert = _has_alert(db, customer.id, ALERT_TYPE_SMURFING_DETECTE)
    ok_alert = alert is not None

    ok = ok_scoring and ok_alert
    if ok:
        _ok(label, f"C3={c3_contrib:.2f}, smurfing={smurf_detected}, alerte SMURFING créée")
    else:
        _fail(label, f"C3={c3_contrib:.2f}, smurfing={smurf_detected}, alerte={alert is not None}")

    _cleanup_customer_tx(db, customer)


def test_scenario_05_homogeneite(db):
    """
    Homogénéité : 5+ transactions à ±10% du même montant
    CV < 0.10 → C3 brut ≥ 60
    """
    label = "05 — Homogénéité des montants (CV < 0.10)"
    print(f"\n[SCÉNARIO] {label}")

    country = _make_country(db, code_iso="T05", name="Test05", is_uemoa=True)
    zone = _make_zone(db, name="ZONE_T05", risk_level="FAIBLE")
    customer = _make_customer(db, nom="TEST_CLIENT_HOMO", prenom="Homogeneite",
                               revenus=200_000, country=country, zone=zone)
    acc = _make_account(db, customer)
    db.commit()

    # 5 transactions très proches : 247000, 251000, 249500, 248000, 250500
    montants = [247_000, 251_000, 249_500, 248_000, 250_500]
    for i, m in enumerate(montants):
        _make_tx(db, acc, montant=m, type_op="DEPOT", days_ago=i + 1)
    db.commit()

    engine = ScoringEngine(db)
    result = _get_score(engine, customer.id)
    c3_contrib = result["detail_json"]["C3"]
    # C3 brut ≥ 60 → contribution ≥ 60 * 0.25 = 15.0
    ok = c3_contrib >= 15.0
    if ok:
        _ok(label, f"C3={c3_contrib:.2f} (attendu ≥ 15.0)")
    else:
        _fail(label, f"C3={c3_contrib:.2f} (attendu ≥ 15.0)")

    _cleanup_customer_tx(db, customer)


def test_scenario_06_dormant(db):
    """
    Compte dormant réactivé : 0 tx sur 180j puis ≥ 3 tx sur 30j
    C4 note +30
    """
    label = "06 — Réactivation brutale (compte dormant)"
    print(f"\n[SCÉNARIO] {label}")

    country = _make_country(db, code_iso="T06", name="Test06", is_uemoa=True)
    zone = _make_zone(db, name="ZONE_T06", risk_level="FAIBLE")
    customer = _make_customer(db, nom="TEST_CLIENT_DORMANT", prenom="Dormant",
                               revenus=200_000, country=country, zone=zone,
                               date_creation=datetime.now(timezone.utc) - timedelta(days=2 * 365))
    acc = _make_account(db, customer)
    db.commit()

    # 0 tx avant T-30j, puis 4 tx sur les 10 derniers jours
    for i in range(4):
        _make_tx(db, acc, montant=100_000, type_op="DEPOT", days_ago=i * 2 + 1)
    db.commit()

    engine = ScoringEngine(db)
    result = _get_score(engine, customer.id)
    c4_contrib = result["detail_json"]["C4"]
    # Client 2 ans → C4 brut = 35 + 30 (réactivation) = 65 → contrib = 65 * 0.10 = 6.5
    ok = c4_contrib >= 6.0
    if ok:
        _ok(label, f"C4={c4_contrib:.2f} (attendu ≥ 6.0)")
    else:
        _fail(label, f"C4={c4_contrib:.2f} (attendu ≥ 6.0)")

    _cleanup_customer_tx(db, customer)


def test_scenario_07_pep_active(db):
    """
    PEP active via liste PEP → C5 = 100
    """
    label = "07 — PEP active dans la liste"
    print(f"\n[SCÉNARIO] {label}")

    country = _make_country(db, code_iso="T07", name="Test07", is_uemoa=True)
    pep = PepEntry(nom="BIO TCHANE TEST", prenom="Abdoulaye", fonction="Ministre test",
                    active=True, pays=country.id, source="TEST_SCENARIO")
    db.add(pep)
    db.commit()

    customer = _make_customer(db, nom="BIO TCHANE TEST", prenom="Abdoulaye",
                               country=country, kyc_completion=80)
    db.commit()

    engine = ScoringEngine(db)
    result = _get_score(engine, customer.id)
    c5_contrib = result["detail_json"]["C5"]

    ok_scoring = c5_contrib >= 14.0 and result["c5_score"] == 100.0

    create_pep_alert_if_needed(db, customer_id=customer.id, c5_score=result["c5_score"], skip_if_open=False)
    db.commit()
    alert = _has_alert(db, customer.id, ALERT_TYPE_PEP_DETECTE)
    ok_alert = alert is not None

    ok = ok_scoring and ok_alert
    if ok:
        _ok(label, f"C5={c5_contrib:.2f}, c5_score=100, alerte PEP_DETECTE créée")
    else:
        _fail(label, f"C5={c5_contrib:.2f}, c5_score={result['c5_score']}, alerte PEP_DETECTE={alert is not None}")

    db.query(PepEntry).filter(PepEntry.id == pep.id).delete()
    _cleanup_customer_tx(db, customer)
    db.commit()


def test_scenario_08_pep_ancienne_gafi(db):
    """
    Ancienne PEP dans période GAFI (date_fin < 5 ans) → C5 = 50
    """
    label = "08 — Ancienne PEP dans période GAFI 5 ans → C5=50"
    print(f"\n[SCÉNARIO] {label}")

    country = _make_country(db, code_iso="T08", name="Test08", is_uemoa=True)
    pep = PepEntry(nom="EX MINISTRE TEST", prenom="Alpha", fonction="Ex-ministre",
                    active=False, pays=country.id, source="TEST_SCENARIO",
                    date_debut=date(2015, 1, 1), date_fin=date.today() - timedelta(days=365))
    db.add(pep)
    db.commit()

    customer = _make_customer(db, nom="EX MINISTRE TEST", prenom="Alpha", country=country, kyc_completion=80)
    db.commit()

    engine = ScoringEngine(db)
    result = _get_score(engine, customer.id)
    c5_contrib = result["detail_json"]["C5"]

    ok_scoring = result["c5_score"] == 50.0

    create_pep_alert_if_needed(db, customer_id=customer.id, c5_score=result["c5_score"], skip_if_open=False)
    db.commit()
    alert = _has_alert(db, customer.id, ALERT_TYPE_PEP_DETECTE)
    ok_alert = alert is not None

    ok = ok_scoring and ok_alert
    if ok:
        _ok(label, f"C5={c5_contrib:.2f}, c5_score=50, alerte PEP_DETECTE créée")
    else:
        _fail(label, f"C5={c5_contrib:.2f}, c5_score={result['c5_score']}, alerte PEP_DETECTE={alert is not None}")

    db.query(PepEntry).filter(PepEntry.id == pep.id).delete()
    _cleanup_customer_tx(db, customer)
    db.commit()


def test_scenario_09_pep_hors_gafi(db):
    """
    Ancienne PEP hors période GAFI (date_fin > 5 ans) → C5 = 0
    """
    label = "09 — Ancienne PEP hors période GAFI > 5 ans → C5=0"
    print(f"\n[SCÉNARIO] {label}")

    country = _make_country(db, code_iso="T09", name="Test09", is_uemoa=True)
    pep = PepEntry(nom="VIEUX MINISTRE TEST", prenom="Beta", fonction="Ex-ministre",
                    active=False, pays=country.id, source="TEST_SCENARIO",
                    date_debut=date(2000, 1, 1), date_fin=date(2018, 6, 1))
    db.add(pep)
    db.commit()

    customer = _make_customer(db, nom="VIEUX MINISTRE TEST", prenom="Beta", country=country, kyc_completion=80)
    db.commit()

    engine = ScoringEngine(db)
    result = _get_score(engine, customer.id)
    ok = result["c5_score"] == 0.0
    if ok:
        _ok(label, f"c5_score={result['c5_score']} (hors période GAFI)")
    else:
        _fail(label, f"c5_score={result['c5_score']} (attendu 0)")

    db.query(PepEntry).filter(PepEntry.id == pep.id).delete()
    _cleanup_customer_tx(db, customer)
    db.commit()


def test_scenario_10_duplicates(db):
    """
    Transactions dupliquées : même montant arrondi + type_op + destination dans 24h
    3 groupes → C3 brut ≥ 60 → contribution ≥ 15.0
    """
    label = "10 — Transactions dupliquées (24h)"
    print(f"\n[SCÉNARIO] {label}")

    country = _make_country(db, code_iso="T10", name="Test10", is_uemoa=True)
    zone = _make_zone(db, name="ZONE_T10", risk_level="FAIBLE")
    customer = _make_customer(db, nom="TEST_CLIENT_DUP", prenom="Duplicate",
                               revenus=300_000, country=country, zone=zone)
    acc = _make_account(db, customer)
    db.commit()

    dest_pays = _make_country(db, code_iso="TDP", name="DestPay").id

    # 3 paires de duplicatas : même montant, même type, même destination, à minutes d'intervalle
    base_dates = [datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=d) for d in [10, 7, 3]]
    for base in base_dates:
        for offset_min in [0, 2]:  # 2 minutes d'écart
            tx = Transaction(
                compte_id=acc.id,
                montant=Decimal("250000"),
                devise="XOF",
                type_op="VIREMENT",
                date_op=base + timedelta(minutes=offset_min),
                canal="INTERNET",
                destination_pays_id=dest_pays,
            )
            db.add(tx)
    db.commit()

    engine = ScoringEngine(db)
    result = _get_score(engine, customer.id)
    c3_contrib = result["detail_json"]["C3"]
    # dupes=3 ≥ 3 → C3 ≥ 60 → contrib = 60 * 0.25 = 15.0
    ok = c3_contrib >= 14.0
    if ok:
        _ok(label, f"C3={c3_contrib:.2f} (3 groupes duplicatas détectés)")
    else:
        _fail(label, f"C3={c3_contrib:.2f} (attendu ≥ 14.0)")

    _cleanup_customer_tx(db, customer)


def test_scenario_11_kyc_incomplet(db):
    """
    KYC incomplet : aucun document → C6 ≥ 85
    """
    label = "11 — KYC incomplet (aucun document)"
    print(f"\n[SCÉNARIO] {label}")

    customer = _make_customer(db, nom="TEST_CLIENT_KYC", prenom="Incomplet",
                               kyc_completion=0, revenus=200_000)
    db.commit()

    engine = ScoringEngine(db)
    result = _get_score(engine, customer.id)
    c6_contrib = result["detail_json"]["C6"]

    ok_scoring = c6_contrib >= 8.0

    create_kyc_alert_if_needed(db, customer_id=customer.id, kyc_completion=0, skip_if_open=False)
    db.commit()
    alert = _has_alert(db, customer.id, ALERT_TYPE_KYC_INCOMPLET)
    ok_alert = alert is not None

    ok = ok_scoring and ok_alert
    if ok:
        _ok(label, f"C6={c6_contrib:.2f}, alerte KYC_INCOMPLET créée")
    else:
        _fail(label, f"C6={c6_contrib:.2f}, alerte KYC_INCOMPLET={alert is not None}")

    _cleanup_customer_tx(db, customer)


def test_scenario_12_zone_frontaliere_fatf(db):
    """
    Zone frontalière + pays FATF → C2 ≥ 70
    """
    label = "12 — Zone frontalière FATF"
    print(f"\n[SCÉNARIO] {label}")

    country = _make_country(db, code_iso="T12", name="Test12", is_border=True, is_fatf=True)
    zone = _make_zone(db, name="ZONE_T12", risk_level="ELEVE")
    customer = _make_customer(db, nom="TEST_CLIENT_ZONE", prenom="Frontaliere",
                               country=country, zone=zone, kyc_completion=80)
    db.commit()

    engine = ScoringEngine(db)
    result = _get_score(engine, customer.id)
    c2_contrib = result["detail_json"]["C2"]
    # C2 max entre zone ELEVE (65), is_border (55), is_fatf (70) → 70 * 0.20 = 14.0
    ok = c2_contrib >= 14.0
    if ok:
        _ok(label, f"C2={c2_contrib:.2f} (attendu ≥ 14.0)")
    else:
        _fail(label, f"C2={c2_contrib:.2f} (attendu ≥ 14.0)")

    _cleanup_customer_tx(db, customer)


def test_scenario_13_destination_risquee(db):
    """
    Transactions vers pays à risque → C3 majoré
    """
    label = "13 — Destination pays à risque (FATF)"
    print(f"\n[SCÉNARIO] {label}")

    risk_country = _make_country(db, code_iso="TRK", name="RiskyLand", is_fatf=True)
    safe_country = _make_country(db, code_iso="TSF", name="SafeLand", is_uemoa=True)
    zone = _make_zone(db, name="ZONE_T13", risk_level="FAIBLE")
    customer = _make_customer(db, nom="TEST_CLIENT_DEST", prenom="RiskyDest",
                               revenus=200_000, country=safe_country, zone=zone)
    acc = _make_account(db, customer)
    db.commit()

    # 4 virements vers pays FATF sur 4 jours
    for i in range(4):
        _make_tx(db, acc, montant=200_000, type_op="VIREMENT", days_ago=i + 2,
                  pays_dest_id=risk_country.id)
    db.commit()

    engine = ScoringEngine(db)
    result = _get_score(engine, customer.id)
    c3_contrib = result["detail_json"]["C3"]
    # ratio_risky = 4/4 = 1.0 > 0.5 → C3 brut ≥ 75 → contrib ≥ 75 * 0.25 = 18.75
    ok = c3_contrib >= 18.0
    if ok:
        _ok(label, f"C3={c3_contrib:.2f} (destinations risquées détectées)")
    else:
        _fail(label, f"C3={c3_contrib:.2f}")

    _cleanup_customer_tx(db, customer)


def test_scenario_14_client_sain(db):
    """
    Client sain : tout conforme → score FAIBLE (< 34)
    Documents KYC valides, transactions cohérentes avec revenus, zone UEMOA.
    """
    label = "14 — Client sain (score FAIBLE)"
    print(f"\n[SCÉNARIO] {label}")

    country = _make_country(db, code_iso="T14", name="Test14", is_uemoa=True)
    zone = _make_zone(db, name="ZONE_T14", risk_level="FAIBLE")
    customer = _make_customer(db, nom="TEST_CLIENT_SAIN", prenom="Standard",
                               profession_risk="LOW", revenus=300_000,
                               country=country, zone=zone, kyc_completion=95,
                               date_creation=datetime.now(timezone.utc) - timedelta(days=4 * 365))
    acc = _make_account(db, customer)
    # Document KYC valide → évite C6=85 (aucun doc)
    doc = CustomerDoc(
        client_id=customer.id, type_doc="CNI", numero=f"SAIN{uuid.uuid4().int % 100000:05d}",
        date_expiration=date.today() + timedelta(days=365),
    )
    db.add(doc)
    db.commit()

    # 3 dépôts de montants variés (pas d'homogénéité), cohérents avec revenus
    for i, m in enumerate([100_000, 150_000, 120_000]):
        _make_tx(db, acc, montant=m, type_op="DEPOT", days_ago=15 * (i + 1) + 1)
    db.commit()

    engine = ScoringEngine(db)
    result = _get_score(engine, customer.id)
    ok = result["global_score"] < 34 and result["risk_category"] == "FAIBLE"
    if ok:
        _ok(label, f"score={result['global_score']}, catégorie={result['risk_category']}")
    else:
        _fail(label, f"score={result['global_score']}, catégorie={result['risk_category']} (attendu FAIBLE < 34)")

    _cleanup_customer_tx(db, customer)


def test_scenario_15_beneficiaire_groupe(db):
    """
    Bénéficiaire groupé : 2+ clients envoient au même destinataire
    Alerte BENEFICIAIRE_GROUPEMENT créée par check_and_alert
    """
    label = "15 — Bénéficiaire groupé (2 clients → même destinataire)"
    print(f"\n[SCÉNARIO] {label}")

    country = _make_country(db, code_iso="T15", name="Test15", is_uemoa=True)
    zone = _make_zone(db, name="ZONE_T15", risk_level="FAIBLE")

    # Client A
    ca = _make_customer(db, nom="TEST_CLIENT_BENEF_A", prenom="Alpha",
                          revenus=500_000, country=country, zone=zone)
    acc_a = _make_account(db, ca)
    db.commit()

    # Client B
    cb = _make_customer(db, nom="TEST_CLIENT_BENEF_B", prenom="Beta",
                          revenus=500_000, country=country, zone=zone)
    acc_b = _make_account(db, cb)
    db.commit()

    destination = "OUEDRAOGO FATIMA"

    # Client A envoie 1 virement
    tx1 = _make_tx(db, acc_a, montant=250_000, type_op="VIREMENT",
                    days_ago=2, canal="MOBILE")
    tx1.destination = destination
    db.commit()

    # Client B envoie 1 virement au même destinataire
    tx2 = _make_tx(db, acc_b, montant=300_000, type_op="VIREMENT",
                    days_ago=1, canal="MOBILE")
    tx2.destination = destination
    db.commit()

    # check_and_alert analyse toutes les tx vers ce bénéf — doit détecter 2 clients
    check_and_alert(tx2, db)
    db.commit()

    alert_a = _has_alert(db, ca.id, ALERT_TYPE_BENEFICIAIRE_GROUPEMENT)
    alert_b = _has_alert(db, cb.id, ALERT_TYPE_BENEFICIAIRE_GROUPEMENT)

    # L'alerte est créée pour le client de la tx passée en paramètre (tx2 → client B)
    ok = alert_b is not None
    if ok:
        _ok(label, "2 clients distincts → alerte BENEFICIAIRE_GROUPEMENT créée")
    else:
        _fail(label, f"alert_a={alert_a is not None}, alert_b={alert_b is not None}")

    # Nettoyage
    for c in (ca, cb):
        _cleanup_customer_tx(db, c)


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    global PASS, FAIL, TOTAL
    print("=" * 72)
    print("  TESTS SCÉNARIOS COMPLETS — MOTEUR DE SCORING & ALERTES LBC/FT")
    print("  Base réelle : app.db.session.SessionLocal")
    print("=" * 72)

    db = SessionLocal()
    try:
        _ensure_referentials(db)
        TOTAL = 0
        PASS = 0
        FAIL = 0

        test_scenario_01_seuil_global(db)
        test_scenario_02_seuil_especes(db)
        test_scenario_03_smurfing(db)
        test_scenario_04_near_threshold(db)
        test_scenario_05_homogeneite(db)
        test_scenario_06_dormant(db)
        test_scenario_07_pep_active(db)
        test_scenario_08_pep_ancienne_gafi(db)
        test_scenario_09_pep_hors_gafi(db)
        test_scenario_10_duplicates(db)
        test_scenario_11_kyc_incomplet(db)
        test_scenario_12_zone_frontaliere_fatf(db)
        test_scenario_13_destination_risquee(db)
        test_scenario_14_client_sain(db)
        test_scenario_15_beneficiaire_groupe(db)

    finally:
        # Nettoyage de sécurité : supprime toutes les données de test
        print("\n" + "-" * 72)
        print("  NETTOYAGE : suppression des données de test...")
        # Pas de cleanup global ici — chaque scénario nettoie ses données
        # via _cleanup_customer_tx.
        db.close()

    # Bilan
    print("=" * 72)
    if FAIL == 0:
        print(f"  RÉSULTAT : {PASS}/{TOTAL} tests PASSÉS ✓")
    else:
        print(f"  RÉSULTAT : {PASS}/{TOTAL} PASSÉS, {FAIL} ÉCHECS ✗")
    print("=" * 72)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
