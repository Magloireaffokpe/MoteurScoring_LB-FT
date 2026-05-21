"""
scripts/generate_fake_data.py
==============================
Générateur de données de test — RiskGuard (IMF béninoises)
Produit exactement 500 clients avec profils variés + 3 scénarios obligatoires.

Auteur  : Dev B — BATAMOUSSI Marcos
Version : 1.1 — Mai 2026 (optimisations perf)

Changements v1.1 :
  - UUIDs générés côté client → suppression de tous les db.flush() individuels
  - Transactions accumulées par batch → db.add_all() au lieu de 10 000+ add()+flush()
  - BATCH_SIZE 50 → 100
  - Timing ajouté (durée totale + durée par phase)

Usage :
    cd backend/
    python scripts/generate_fake_data.py          # génère 500 clients
    python scripts/generate_fake_data.py --dry-run # affiche le plan sans écrire

Le script est IDEMPOTENT : nettoie ses propres tables avant de regénérer.
Ne touche JAMAIS aux tables de référence (countries, risk_zones, scoring_criteria,
risk_thresholds, user_roles, users).
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time  # NOUVEAU : mesure de performance
import uuid as _uuid  # NOUVEAU : génération UUID côté client
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

# ── Permet de lancer depuis n'importe quel répertoire ─────────────────────
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faker import Faker
from sqlalchemy.orm import Session

from app.db.session import SessionLocal

# FIX: imports complets — Score, Alert, AuditLog nécessaires pour le cleanup
from app.models.alerts import Alert
from app.models.audit_logs import AuditLog
from app.models.countries import Country
from app.models.customer_accounts import CustomerAccount
from app.models.customer_docs import CustomerDoc
from app.models.customers import Customer
from app.models.pep_list import PepEntry
from app.models.risk_zones import RiskZone
from app.models.scores import Score
from app.models.transactions import Transaction

# ══════════════════════════════════════════════════════════════════════════
# 1. CONSTANTES LOCALES
# ══════════════════════════════════════════════════════════════════════════

fake = Faker("fr_FR")
random.seed(42)
Faker.seed(42)

TOTAL_CLIENTS = 500
BATCH_SIZE = 100  # PERF: 50 → 100 (moins de commits, moins de round-trips)

# ── Listes anthroponymiques béninoises ────────────────────────────────────
PRENOMS_BENINOIS = [
    "Adjovi",
    "Akossiwa",
    "Akoua",
    "Amenan",
    "Amidath",
    "Assogba",
    "Béatrice",
    "Bénédicte",
    "Cécile",
    "Clarisse",
    "Dossou",
    "Edwige",
    "Evelyne",
    "Fatima",
    "Fatoumata",
    "Félicité",
    "Fiacre",
    "Firmin",
    "Flore",
    "Gbèdji",
    "Gilles",
    "Grâce",
    "Henriette",
    "Hervé",
    "Honoré",
    "Huguette",
    "Idrissou",
    "Innocent",
    "Irène",
    "Isidore",
    "Jean-Baptiste",
    "Joël",
    "Jonas",
    "Joséphine",
    "Justine",
    "Koffi",
    "Kossi",
    "Latifa",
    "Lionel",
    "Luc",
    "Madeleine",
    "Marcel",
    "Marcelline",
    "Mariam",
    "Marie-Claire",
    "Mathieu",
    "Maxime",
    "Médard",
    "Modeste",
    "Monique",
    "Nadège",
    "Narcisse",
    "Nicaise",
    "Nicolas",
    "Norbert",
    "Odette",
    "Olivia",
    "Omar",
    "Onésime",
    "Oswald",
    "Pascal",
    "Patrice",
    "Paul",
    "Pauline",
    "Pélagie",
    "Raïmi",
    "Raphaël",
    "Regina",
    "René",
    "Richard",
    "Rosalie",
    "Rosine",
    "Rufin",
    "Sébastien",
    "Séraphin",
    "Simone",
    "Sipho",
    "Sodji",
    "Soumaïla",
    "Stanislas",
    "Sylvain",
    "Sylvestre",
    "Théodore",
    "Thierry",
    "Thomas",
    "Urbain",
    "Valentin",
    "Victor",
    "Victorin",
    "Vincent",
    "Viviane",
    "Xavier",
    "Yves",
    "Zacharie",
    "Zénab",
]

NOMS_BENINOIS = [
    "Adjagba",
    "Adjaï",
    "Adjanohoun",
    "Agbodjan",
    "Agossou",
    "Ahouandjinou",
    "Aïkpé",
    "Akindes",
    "Akognon",
    "Alagnon",
    "Alapini",
    "Alassane",
    "Alidou",
    "Alokpo",
    "Amouzou",
    "Anago",
    "Anonrin",
    "Assogba",
    "Azonkpon",
    "Biaou",
    "Bio",
    "Bocco",
    "Bossou",
    "Chabi",
    "Codjo",
    "Dako",
    "Dansou",
    "Dèdèwanou",
    "Dégbélo",
    "Dessouassi",
    "Djinadou",
    "Djossou",
    "Dossou",
    "Dougnon",
    "Dovonou",
    "Edou",
    "Elegbede",
    "Faïnou",
    "Fandohan",
    "Fassinou",
    "Ganfon",
    "Gbaguidi",
    "Gbèssémèhou",
    "Gbodogbe",
    "Gnonlonfoun",
    "Gnimassoun",
    "Gossou",
    "Gouvon",
    "Guèdègbé",
    "Hachimou",
    "Hinkati",
    "Houngbédji",
    "Hounto",
    "Hounyovi",
    "Hunlédé",
    "Igue",
    "Kassa",
    "Kérékou",
    "Kiki",
    "Klotchéou",
    "Kossou",
    "Kouagou",
    "Kpatchavi",
    "Kpessou",
    "Kpoton",
    "Lafia",
    "Lagnide",
    "Lalèyè",
    "Lawson",
    "Lédégan",
    "Lokossou",
    "Mawuégnon",
    "Medenou",
    "Metonnou",
    "Mikponhoué",
    "Montcho",
    "Noudéhouenou",
    "Ogoudèlè",
    "Olaniyi",
    "Olodo",
    "Ouédraogo",
    "Padonou",
    "Pognon",
    "Quenum",
    "Sagbohan",
    "Saka",
    "Sinzogan",
    "Soglo",
    "Sohouénou",
    "Sossou",
    "Tamou",
    "Tchibozo",
    "Tchobo",
    "Togbadja",
    "Totin",
    "Vigan",
    "Vodounou",
    "Winsou",
    "Yarou",
    "Zinsou",
]

VILLES_BENINOISE = [
    "Cotonou",
    "Porto-Novo",
    "Parakou",
    "Abomey-Calavi",
    "Djougou",
    "Bohicon",
    "Kandi",
    "Lokossa",
    "Ouidah",
    "Malanville",
    "Natitingou",
    "Abomey",
    "Savalou",
    "Savè",
    "Nikki",
    "Comè",
    "Pobè",
    "Aplahoué",
    "Dassa-Zoumé",
    "Bassila",
    "Tanguiéta",
    "Bembèrèkè",
    "Tchaourou",
    "Dogbo",
    "Sèmè-Kpodji",
    "Glazoué",
    "Azovè",
    "Cové",
    "Zagnanado",
    "Allada",
    "Zogbodomè",
    "Toffo",
    "Lalo",
    "Athiémé",
    "Kétou",
    "Adja-Ouèrè",
    "Ifangni",
    "Sakété",
    "Kalale",
    "Pèrèrè",
]

DEPARTEMENTS_BENIN = [
    "Alibori",
    "Atacora",
    "Atlantique",
    "Borgou",
    "Collines",
    "Couffo",
    "Donga",
    "Littoral",
    "Mono",
    "Ouémé",
    "Plateau",
    "Zou",
]

PROFESSIONS = [
    ("FONCT_PUBL", "Fonctionnaire public", "LOW", 80_000, 350_000),
    ("SALARIE_PRIV", "Salarié secteur privé formel", "LOW", 70_000, 400_000),
    ("ENSEIGNANT", "Enseignant", "LOW", 60_000, 200_000),
    ("INFIRMIER", "Infirmier / Agent de santé", "LOW", 75_000, 250_000),
    ("MILITAIRE", "Militaire / Gendarme", "LOW", 90_000, 300_000),
    ("AGRI_MARAICH", "Agriculteur maraîcher", "LOW", 30_000, 120_000),
    ("AGRI_VIVRIER", "Agriculteur vivrier", "LOW", 20_000, 80_000),
    ("PECHEUR", "Pêcheur", "LOW", 25_000, 90_000),
    ("COMMER_LOCAL", "Commerçant local", "MEDIUM", 60_000, 300_000),
    ("ARTISAN", "Artisan / Menuisier / Couturier", "MEDIUM", 40_000, 180_000),
    ("MOTO_TAXI", "Conducteur zémidjan (moto-taxi)", "MEDIUM", 35_000, 100_000),
    ("REVENDEUR", "Revendeur informel", "MEDIUM", 30_000, 150_000),
    ("ELEV_ANIMAL", "Éleveur", "MEDIUM", 50_000, 200_000),
    ("COMMER_TRANSFR", "Commerçant transfrontalier", "HIGH", 100_000, 800_000),
    ("CHANGEUR", "Changeur de devises / Bureau", "HIGH", 200_000, 1_500_000),
    ("TRANSPORTEUR", "Transporteur international", "HIGH", 150_000, 900_000),
    ("IMPORT_EXPORT", "Importateur / Exportateur", "HIGH", 200_000, 2_000_000),
    ("CASINO_JEU", "Gérant casino / Parieur", "HIGH", 300_000, 3_000_000),
    ("INCONNU", "Activité non déclarée", "HIGH", 0, 50_000),
]

CANAUX = ["MOBILE", "GUICHET", "INTERNET", "ATM"]
TYPES_OP = ["DEPOT", "RETRAIT", "VIREMENT", "PAIEMENT"]
TYPES_DOC = ["CNI", "PASSEPORT", "CARTE_RESIDENT", "PERMIS_CONDUIRE"]

SCENARIO_PHONES: set[str] = {
    "+22966110001",  # Amélie SOGLO
    "+22966110002",  # Koffi BIAOU
    "+22966110003",  # Fatima OUÉDRAOGO
}

# ══════════════════════════════════════════════════════════════════════════
# 2. CHARGEMENT DES RÉFÉRENCES
# ══════════════════════════════════════════════════════════════════════════


class Referentiels:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._load()

    def _load(self) -> None:
        print("  📥 Chargement des référentiels...")

        pays_rows = self.db.query(Country).all()
        if not pays_rows:
            raise RuntimeError(
                "❌ Table 'countries' vide — exécute d'abord : python scripts/seed_db.py"
            )
        self.pays: dict[str, Country] = {p.code_iso: p for p in pays_rows}

        self.bj = self._get_pays("BJ")
        self.ng = self._get_pays("NG")
        self.bf = self._get_pays("BF")
        self.tg = self._get_pays("TG")
        self.ly = self._get_pays("LY")
        self.kp = self._get_pays("KP")

        self.pays_fatf: list[Country] = [p for p in pays_rows if p.is_fatf]
        self.pays_border: list[Country] = [
            p for p in pays_rows if p.is_border and p.code_iso != "BJ"
        ]

        zone_rows = self.db.query(RiskZone).all()
        if not zone_rows:
            raise RuntimeError(
                "❌ Table 'risk_zones' vide — exécute d'abord : python scripts/seed_db.py"
            )
        self.zones: dict[str, RiskZone] = {z.name: z for z in zone_rows}
        self.zones_faible = [z for z in zone_rows if z.risk_level == "FAIBLE"]
        self.zones_moyen = [z for z in zone_rows if z.risk_level == "MOYEN"]
        self.zones_eleve = [
            z for z in zone_rows if z.risk_level in ("ELEVE", "TRES_ELEVE")
        ]

        print(f"     ✓ {len(pays_rows)} pays  |  {len(zone_rows)} zones  chargés")

    def _get_pays(self, code_iso: str) -> Country:
        pays = self.pays.get(code_iso)
        if not pays:
            raise RuntimeError(
                f"❌ Pays '{code_iso}' introuvable en base. "
                "Vérifie seed_db.py → seed_countries()"
            )
        return pays

    def zone_par_nom(self, nom: str) -> RiskZone:
        zone = self.zones.get(nom)
        if not zone:
            zone = next(iter(self.zones.values()))
        return zone


# ══════════════════════════════════════════════════════════════════════════
# 3. NETTOYAGE
# ══════════════════════════════════════════════════════════════════════════


def cleanup_magloire_tables(db: Session) -> None:
    print("\n🧹 Nettoyage des tables de test...")
    t0 = time.perf_counter()

    counts = {
        "audit_logs (client_id non null)": db.query(AuditLog)
        .filter(AuditLog.client_id.isnot(None))
        .count(),
        "scores": db.query(Score).count(),
        "alerts": db.query(Alert).count(),
        "transactions": db.query(Transaction).count(),
        "customer_docs": db.query(CustomerDoc).count(),
        "customer_accounts": db.query(CustomerAccount).count(),
        "pep_list": db.query(PepEntry).count(),
        "customers": db.query(Customer).count(),
    }

    fake_ids = [c.id for c in db.query(Customer.id).all()]
    from sqlalchemy import update

    if fake_ids:
        db.execute(
            update(AuditLog)
            .values(client_id=None)
            .where(AuditLog.client_id.in_(fake_ids))
        )

    db.query(Score).delete(synchronize_session=False)
    db.query(Alert).delete(synchronize_session=False)
    db.query(Transaction).delete(synchronize_session=False)
    db.query(CustomerDoc).delete(synchronize_session=False)
    db.query(CustomerAccount).delete(synchronize_session=False)
    db.query(PepEntry).delete(synchronize_session=False)
    db.query(Customer).delete(synchronize_session=False)
    db.commit()

    for table, count in counts.items():
        print(f"   🗑  {table:<40} {count:>5} ligne(s)")

    print(f"   ✅ Nettoyage terminé en {time.perf_counter() - t0:.2f}s\n")


# ══════════════════════════════════════════════════════════════════════════
# 4. HELPERS GÉNÉRIQUES
# ══════════════════════════════════════════════════════════════════════════


def _random_phone() -> str:
    return f"+229{random.randint(60_000_000, 99_999_999)}"


def _random_date_creation(min_years: float = 0.1, max_years: float = 8.0) -> datetime:
    days = int(random.uniform(min_years * 365, max_years * 365))
    return datetime.now(timezone.utc) - timedelta(days=days)


def _random_prenom() -> str:
    return random.choice(PRENOMS_BENINOIS)


def _random_nom() -> str:
    return random.choice(NOMS_BENINOIS).upper()


def _pick_profession() -> tuple[str, str, str, int, int]:
    return random.choice(PROFESSIONS)


def _random_revenu(rev_min: int, rev_max: int, profession_risk: str) -> Decimal:
    base = random.randint(rev_min, rev_max)
    variation = random.uniform(0.90, 1.10)
    return Decimal(str(round(base * variation / 1000) * 1000))


def _random_city() -> str:
    return random.choice(VILLES_BENINOISE)


def _random_region() -> str:
    return random.choice(DEPARTEMENTS_BENIN)


# ══════════════════════════════════════════════════════════════════════════
# 5. CRÉATION DES ENTITÉS
#
# PERF v1.1 :
#   - Chaque helper génère l'UUID côté Python (id=_uuid.uuid4()).
#     Cela évite le round-trip DB que db.flush() déclenchait pour
#     récupérer l'id généré par PostgreSQL (server_default gen_random_uuid()).
#   - db.flush() retiré de tous les helpers.
#     SQLAlchemy batche automatiquement les INSERTs jusqu'au db.commit().
#   - Les FKs (account.client_id, doc.client_id, etc.) utilisent
#     directement customer.id qui est maintenant disponible immédiatement.
# ══════════════════════════════════════════════════════════════════════════


def _create_customer(
    db: Session,
    ref: Referentiels,
    *,
    nom: str,
    prenom: str,
    profession_code: str,
    profession_name: str,
    profession_risk: str,
    revenus: Decimal,
    zone: RiskZone,
    country: Country,
    statut_pep: bool = False,
    kyc_completion: int = 80,
    kyc_level: str = "LOW",
    date_creation: Optional[datetime] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    status: str = "ACTIVE",
    city: Optional[str] = None,
    region: Optional[str] = None,
) -> Customer:
    customer = Customer(
        id=_uuid.uuid4(),  # PERF: UUID client-side
        nom=nom,
        prenom=prenom,
        date_naissance=fake.date_of_birth(minimum_age=18, maximum_age=70),
        phone=phone or _random_phone(),
        email=email,
        profession_code=profession_code,
        profession_name=profession_name,
        profession_risk=profession_risk,
        revenus_declares=revenus,
        city=city or _random_city(),
        region=region or _random_region(),
        latitude=str(round(random.uniform(6.2, 12.4), 4)),
        longitude=str(round(random.uniform(0.8, 3.8), 4)),
        zone_geo=zone.id,
        pays=country.id,
        statut_pep=statut_pep,
        kyc_completion=kyc_completion,
        kyc_level=kyc_level,
        status=status,
        date_creation=date_creation or _random_date_creation(),
    )
    db.add(customer)
    # PERF: db.flush() supprimé — id disponible immédiatement via _uuid.uuid4()
    return customer


def _create_account(
    db: Session,
    customer: Customer,
    *,
    type_compte: str = "COURANT",
    solde_moyen: Optional[Decimal] = None,
    date_ouverture: Optional[date] = None,
    status: str = "ACTIF",
) -> CustomerAccount:
    if solde_moyen is None:
        rev = float(customer.revenus_declares or 0)
        solde_moyen = Decimal(str(round(rev * random.uniform(0.5, 3.0) / 1000) * 1000))

    account = CustomerAccount(
        id=_uuid.uuid4(),  # PERF: UUID client-side
        client_id=customer.id,
        type_compte=type_compte,
        solde_moyen=solde_moyen,
        date_ouverture=date_ouverture
        or (customer.date_creation.date() + timedelta(days=random.randint(1, 30))),
        status=status,
    )
    db.add(account)
    # PERF: db.flush() supprimé
    return account


def _create_doc(
    db: Session,
    customer: Customer,
    *,
    type_doc: str = "CNI",
    expiration_delta_days: int = 730,
) -> CustomerDoc:
    doc = CustomerDoc(
        id=_uuid.uuid4(),  # PERF: UUID client-side
        client_id=customer.id,
        type_doc=type_doc,
        numero=f"{type_doc[:2]}{fake.bothify('??########').upper()}",
        date_expiration=date.today() + timedelta(days=expiration_delta_days),
    )
    db.add(doc)
    # PERF: db.flush() supprimé
    return doc


def _create_transaction(
    db: Session,
    account: CustomerAccount,
    *,
    montant: Decimal,
    type_op: str = "DEPOT",
    days_ago: int = 10,
    canal: str = "GUICHET",
    origine_pays: Optional[Country] = None,
    destination_pays: Optional[Country] = None,
    origine_txt: Optional[str] = None,
    destination_txt: Optional[str] = None,
    accumulator: Optional[list] = None,  # PERF: accumulateur batch
) -> Transaction:
    """
    Crée une transaction.

    PERF v1.1 :
      - id généré côté client.
      - Si `accumulator` est fourni, la transaction y est ajoutée au lieu
        d'être immédiatement db.add()-ée. L'appelant fait db.add_all(accumulator)
        au moment du commit de batch → drastiquement moins de round-trips.
      - Si accumulator=None (scénarios individuels), comportement original
        préservé (db.add direct).
    """
    tx = Transaction(
        id=_uuid.uuid4(),  # PERF: UUID client-side
        compte_id=account.id,
        montant=montant,
        devise="XOF",
        type_op=type_op,
        date_op=datetime.now(timezone.utc)
        - timedelta(days=days_ago, hours=random.randint(0, 23)),
        canal=canal,
        origine=origine_txt,
        destination=destination_txt,
        origine_pays_id=origine_pays.id if origine_pays else None,
        destination_pays_id=destination_pays.id if destination_pays else None,
    )
    if accumulator is not None:
        accumulator.append(tx)  # PERF: pas de db.add() ici
    else:
        db.add(tx)  # comportement original pour scénarios
    return tx


def _add_to_pep_list(
    db: Session,
    customer: Customer,
    country: Country,
    *,
    fonction: str = "Personnalité politique",
    source: str = "GIABA",
) -> PepEntry:
    entry = PepEntry(
        id=_uuid.uuid4(),  # PERF: UUID client-side
        nom=customer.nom,
        prenom=customer.prenom,
        fonction=fonction,
        date_debut=date.today() - timedelta(days=random.randint(180, 2000)),
        date_fin=None,
        source=source,
        active=True,
        pays=country.id,
    )
    db.add(entry)
    # PERF: db.flush() supprimé
    return entry


# ══════════════════════════════════════════════════════════════════════════
# 6. TRANSACTIONS COHÉRENTES PAR PROFIL
# ══════════════════════════════════════════════════════════════════════════


def _generate_regular_transactions(
    db: Session,
    account: CustomerAccount,
    customer: Customer,
    ref: Referentiels,
    *,
    nb_months: int = 3,
    anomaly_factor: float = 1.0,
    accumulator: Optional[list] = None,  # PERF: propagé depuis generate_random_clients
) -> None:
    rev_mensuel = float(customer.revenus_declares or 50_000)

    for month in range(nb_months):
        nb_tx = random.randint(3, 8)
        budget_mensuel = rev_mensuel * anomaly_factor

        for _ in range(nb_tx):
            ratio = random.uniform(0.1, 0.6)
            montant = Decimal(str(round(budget_mensuel * ratio / 500) * 500))
            montant = max(Decimal("1000"), montant)
            type_op = random.choices(TYPES_OP, weights=[40, 30, 20, 10])[0]
            days_ago = month * 30 + random.randint(1, 28)

            dest = None
            if type_op == "VIREMENT" and random.random() < 0.15:
                dest = random.choice(ref.pays_border + [ref.bj])

            _create_transaction(
                db,
                account,
                montant=montant,
                type_op=type_op,
                days_ago=days_ago,
                canal=random.choice(CANAUX),
                destination_pays=dest,
                accumulator=accumulator,  # PERF: propagé
            )


def _generate_smurfing_transactions(
    db: Session,
    account: CustomerAccount,
    destination_country: Country,
    *,
    nb_tx: int = 6,
    accumulator: Optional[list] = None,  # PERF: propagé
) -> None:
    for i in range(nb_tx):
        base = random.randrange(400_000, 490_001, 10_000)
        montant = Decimal(str(base))

        _create_transaction(
            db,
            account,
            montant=montant,
            type_op="VIREMENT",
            days_ago=random.randint(1, 45),
            canal=random.choice(["INTERNET", "MOBILE"]),
            destination_pays=destination_country,
            destination_txt=f"Compte suspect — {destination_country.name}",
            accumulator=accumulator,  # PERF: propagé
        )


# ══════════════════════════════════════════════════════════════════════════
# 7. SCÉNARIOS OBLIGATOIRES
# Note : les scénarios (3 clients) gardent le comportement original
# (pas d'accumulateur) — leur volume est négligeable.
# ══════════════════════════════════════════════════════════════════════════


def create_scenario_amelie_soglo(db: Session, ref: Referentiels) -> Customer:
    print("   🟢 Scénario A : Amélie SOGLO (risque FAIBLE)...")

    zone = ref.zone_par_nom("CAPITALE")
    country = ref.bj

    customer = _create_customer(
        db,
        ref,
        nom="SOGLO",
        prenom="Amélie",
        profession_code="FONCT_PUBL",
        profession_name="Institutrice / Fonctionnaire public",
        profession_risk="LOW",
        revenus=Decimal("185000"),
        zone=zone,
        country=country,
        statut_pep=False,
        kyc_completion=95,
        kyc_level="LOW",
        date_creation=datetime.now(timezone.utc) - timedelta(days=4 * 365 + 120),
        phone="+22966110001",
        email="amelie.soglo@imf-test.bj",
        status="ACTIVE",
        city="Cotonou",
        region="Littoral",
    )

    account = _create_account(
        db,
        customer,
        type_compte="EPARGNE",
        solde_moyen=Decimal("550000"),
        date_ouverture=date.today() - timedelta(days=4 * 365),
    )

    _create_doc(db, customer, type_doc="CNI", expiration_delta_days=900)
    _create_doc(db, customer, type_doc="PASSEPORT", expiration_delta_days=1500)

    for month in range(3):
        for tx_data in [
            (80_000, "DEPOT", "GUICHET", 5),
            (50_000, "RETRAIT", "ATM", 10),
            (30_000, "PAIEMENT", "MOBILE", 15),
            (40_000, "VIREMENT", "INTERNET", 20),
        ]:
            montant, type_op, canal, day_offset = tx_data
            _create_transaction(
                db,
                account,
                montant=Decimal(str(montant)),
                type_op=type_op,
                days_ago=month * 30 + day_offset,
                canal=canal,
                destination_pays=ref.bj if type_op == "VIREMENT" else None,
                # accumulator=None → db.add() direct (comportement original)
            )

    print(f"      ✓ Client id={customer.id}")
    return customer


def create_scenario_koffi_biaou(db: Session, ref: Referentiels) -> Customer:
    print("   🟡 Scénario B : Koffi BIAOU (risque MOYEN)...")

    zone = ref.zone_par_nom("FRONTIERE")
    country = ref.bj

    customer = _create_customer(
        db,
        ref,
        nom="BIAOU",
        prenom="Koffi",
        profession_code="COMMER_TRANSFR",
        profession_name="Commerçant transfrontalier",
        profession_risk="HIGH",
        revenus=Decimal("350000"),
        zone=zone,
        country=country,
        statut_pep=False,
        kyc_completion=65,
        kyc_level="MEDIUM",
        date_creation=datetime.now(timezone.utc) - timedelta(days=2 * 365 + 45),
        phone="+22966110002",
        email="koffi.biaou@imf-test.bj",
        status="ACTIVE",
        city="Malanville",
        region="Alibori",
    )

    account = _create_account(
        db,
        customer,
        type_compte="COURANT",
        solde_moyen=Decimal("1250000"),
        date_ouverture=date.today() - timedelta(days=2 * 365),
    )

    _create_doc(db, customer, type_doc="CNI", expiration_delta_days=800)
    _create_doc(db, customer, type_doc="PASSEPORT", expiration_delta_days=20)

    _generate_regular_transactions(
        db, account, customer, ref, nb_months=3, anomaly_factor=2.5
    )

    for _ in range(3):
        dest = random.choice([ref.ng, ref.tg])
        _create_transaction(
            db,
            account,
            montant=Decimal(str(random.randrange(200_000, 600_000, 50_000))),
            type_op="VIREMENT",
            days_ago=random.randint(5, 60),
            canal="INTERNET",
            destination_pays=dest,
            destination_txt=f"Fournisseur {dest.name}",
        )

    for i in range(7):
        _create_transaction(
            db,
            account,
            montant=Decimal(str(random.randrange(100_000, 300_000, 25_000))),
            type_op="RETRAIT",
            days_ago=random.randint(1, 80),
            canal="GUICHET",
        )

    print(f"      ✓ Client id={customer.id}")
    return customer


def create_scenario_fatima_ouedraogo(db: Session, ref: Referentiels) -> Customer:
    print("   🔴 Scénario C : Fatima OUÉDRAOGO (risque ÉLEVÉ)...")

    zone = ref.zone_par_nom("FRONTIERE")
    country = ref.bj

    customer = _create_customer(
        db,
        ref,
        nom="OUEDRAOGO",
        prenom="Fatima",
        profession_code="CHANGEUR",
        profession_name="Changeur de devises / Bureau de change informel",
        profession_risk="HIGH",
        revenus=Decimal("120000"),
        zone=zone,
        country=country,
        statut_pep=True,
        kyc_completion=25,
        kyc_level="HIGH",
        date_creation=datetime.now(timezone.utc) - timedelta(days=45),
        phone="+22966110003",
        email="fatima.ouedraogo@imf-test.bj",
        status="ACTIVE",
        city="Malanville",
        region="Alibori",
    )

    _add_to_pep_list(
        db,
        customer,
        country,
        fonction="Épouse de Ministre de l'Économie — Bénin",
        source="CENTIF",
    )

    account = _create_account(
        db,
        customer,
        type_compte="COURANT",
        solde_moyen=Decimal("5000000"),
        date_ouverture=date.today() - timedelta(days=40),
    )

    _create_doc(db, customer, type_doc="CNI", expiration_delta_days=-10)
    _create_doc(db, customer, type_doc="PASSEPORT", expiration_delta_days=-30)

    _generate_smurfing_transactions(db, account, destination_country=ref.ng, nb_tx=6)

    for _ in range(3):
        _create_transaction(
            db,
            account,
            montant=Decimal(str(random.randrange(450_000, 490_001, 10_000))),
            type_op="VIREMENT",
            days_ago=random.randint(2, 30),
            canal="INTERNET",
            destination_pays=ref.ly,
            destination_txt="Compte Tripoli — Libye",
        )

    for i in range(5):
        _create_transaction(
            db,
            account,
            montant=Decimal(str(random.randrange(300_000, 490_001, 50_000))),
            type_op="RETRAIT",
            days_ago=random.randint(1, 40),
            canal="GUICHET",
        )

    print(f"      ✓ Client id={customer.id}")
    return customer


# ══════════════════════════════════════════════════════════════════════════
# 8. GÉNÉRATION DES 497 CLIENTS ALÉATOIRES
# ══════════════════════════════════════════════════════════════════════════


def _pick_zone_for_risk(risk: str, ref: Referentiels) -> RiskZone:
    if risk == "LOW":
        pool = ref.zones_faible or list(ref.zones.values())
    elif risk == "MEDIUM":
        pool = ref.zones_moyen or ref.zones_faible
    else:
        pool = ref.zones_eleve or ref.zones_moyen or list(ref.zones.values())
    return random.choice(pool)


def _pick_country_for_zone(zone: RiskZone, ref: Referentiels) -> Country:
    if zone.risk_level in ("ELEVE", "TRES_ELEVE") and random.random() < 0.3:
        candidates = [ref.ng, ref.tg, ref.bf] + [ref.bj]
        return random.choice(candidates)
    return random.choice([ref.bj] * 7 + list(ref.pays.values()))


def _kyc_profile(profession_risk: str) -> tuple[int, str]:
    if profession_risk == "LOW":
        completion = random.randint(70, 100)
        level = "LOW" if completion >= 85 else "MEDIUM"
    elif profession_risk == "MEDIUM":
        completion = random.randint(40, 90)
        level = "MEDIUM"
    else:
        completion = random.randint(10, 70)
        level = "HIGH" if completion < 50 else "MEDIUM"
    return completion, level


def _doc_profile(profession_risk: str, kyc_completion: int) -> list[dict]:
    docs = []
    if kyc_completion >= 80:
        docs.append(
            {"type_doc": "CNI", "expiration_delta_days": random.randint(300, 1500)}
        )
        if random.random() < 0.6:
            docs.append(
                {
                    "type_doc": "PASSEPORT",
                    "expiration_delta_days": random.randint(200, 1800),
                }
            )
    elif kyc_completion >= 50:
        docs.append(
            {"type_doc": "CNI", "expiration_delta_days": random.randint(30, 900)}
        )
        if random.random() < 0.4:
            docs.append(
                {
                    "type_doc": random.choice(TYPES_DOC),
                    "expiration_delta_days": random.randint(-60, 60),
                }
            )
    elif kyc_completion >= 25:
        valide = random.random() > 0.4
        delta = random.randint(30, 180) if valide else random.randint(-180, -1)
        docs.append({"type_doc": "CNI", "expiration_delta_days": delta})
    else:
        docs.append(
            {"type_doc": "CNI", "expiration_delta_days": random.randint(-365, -1)}
        )
    return docs


def generate_random_clients(
    db: Session,
    ref: Referentiels,
    total: int = TOTAL_CLIENTS,
) -> list[Customer]:
    print(f"\n👥 Génération de {total} clients aléatoires...")
    t0 = time.perf_counter()

    pep_indices = set(random.sample(range(total), max(1, int(total * 0.02))))

    fonctions_pep = [
        "Député à l'Assemblée Nationale",
        "Conseiller du Président de la République",
        "Directeur Général du Trésor",
        "Préfet de département",
        "Ambassadeur plénipotentiaire",
        "Général de Brigade",
        "Haut Commissaire",
        "Directeur de cabinet ministériel",
        "Magistrat à la Cour Suprême",
        "Président de Chambre consulaire",
    ]

    clients: list[Customer] = []
    phones_used: set[str] = SCENARIO_PHONES.copy()

    # PERF: accumulateur de transactions pour le batch courant.
    # Toutes les transactions d'un batch BATCH_SIZE sont collectées ici,
    # puis insérées en une seule fois via db.add_all() au moment du commit.
    # Économie : ~9 500 db.add()+flush() → ~5 db.add_all() (1 par batch).
    tx_batch: list[Transaction] = []

    for i in range(total):
        prof_code, prof_name, prof_risk, rev_min, rev_max = _pick_profession()
        zone = _pick_zone_for_risk(prof_risk, ref)
        country = _pick_country_for_zone(zone, ref)
        revenus = _random_revenu(rev_min, rev_max, prof_risk)
        kyc_completion, kyc_level = _kyc_profile(prof_risk)
        is_pep = i in pep_indices

        if prof_risk == "LOW":
            date_creation = _random_date_creation(0.5, 8.0)
        elif prof_risk == "MEDIUM":
            date_creation = _random_date_creation(0.3, 5.0)
        else:
            date_creation = _random_date_creation(0.1, 4.0)

        phone = _random_phone()
        while phone in phones_used:
            phone = _random_phone()
        phones_used.add(phone)

        # ── Création client + compte + docs (pas de flush grâce aux UUIDs) ──
        customer = _create_customer(
            db,
            ref,
            nom=_random_nom(),
            prenom=_random_prenom(),
            profession_code=prof_code,
            profession_name=prof_name,
            profession_risk=prof_risk,
            revenus=revenus,
            zone=zone,
            country=country,
            statut_pep=is_pep,
            kyc_completion=kyc_completion,
            kyc_level=kyc_level,
            date_creation=date_creation,
            phone=phone,
            city=_random_city(),
            region=_random_region(),
        )

        if is_pep:
            _add_to_pep_list(
                db,
                customer,
                country,
                fonction=random.choice(fonctions_pep),
                source=random.choice(["GIABA", "CENTIF", "ONU"]),
            )

        type_compte = random.choice(["COURANT", "EPARGNE"])
        account = _create_account(db, customer, type_compte=type_compte)

        for doc_kwargs in _doc_profile(prof_risk, kyc_completion):
            _create_doc(db, customer, **doc_kwargs)

        # ── Transactions → dans l'accumulateur batch ──────────────────
        if prof_risk == "HIGH" and random.random() < 0.15:
            _generate_smurfing_transactions(
                db,
                account,
                destination_country=random.choice(ref.pays_fatf + ref.pays_border),
                nb_tx=random.randint(3, 5),
                accumulator=tx_batch,  # PERF
            )
        else:
            anomaly = 1.0
            if prof_risk == "HIGH":
                anomaly = random.uniform(1.5, 4.0)
            elif prof_risk == "MEDIUM":
                anomaly = random.uniform(1.0, 2.0)

            _generate_regular_transactions(
                db,
                account,
                customer,
                ref,
                nb_months=random.randint(1, 6),
                anomaly_factor=anomaly,
                accumulator=tx_batch,  # PERF
            )

        clients.append(customer)

        # ── Commit par batch ──────────────────────────────────────────
        if (i + 1) % BATCH_SIZE == 0:
            n_tx = len(tx_batch)
            db.add_all(tx_batch)
            tx_batch.clear()
            db.commit()
            elapsed = time.perf_counter() - t0
            print(
                f"   ⏳ {i + 1:>4}/{total} clients  |  {n_tx:>5} tx  |  {elapsed:>6.1f}s"
            )

    # ── Flush du dernier batch (potentiellement < BATCH_SIZE) ─────────
    if tx_batch:
        db.add_all(tx_batch)
        tx_batch.clear()

    db.commit()

    elapsed = time.perf_counter() - t0
    print(
        f"\n   ✅ {total} clients générés en {elapsed:.1f}s  "
        f"({elapsed / total * 1000:.0f} ms/client)\n"
    )

    return clients


# ══════════════════════════════════════════════════════════════════════════
# 9. STATISTIQUES POST-GÉNÉRATION
# ══════════════════════════════════════════════════════════════════════════


def print_stats(db: Session) -> None:
    total_clients = db.query(Customer).count()
    total_comptes = db.query(CustomerAccount).count()
    total_docs = db.query(CustomerDoc).count()
    total_tx = db.query(Transaction).count()
    total_pep = (
        db.query(Customer).filter(Customer.statut_pep == True).count()
    )  # noqa: E712
    total_pep_list = db.query(PepEntry).count()

    docs_invalides = (
        db.query(CustomerDoc).filter(CustomerDoc.date_expiration < date.today()).count()
    )

    from sqlalchemy import select, exists

    clients_sans_doc = (
        db.query(Customer)
        .filter(
            ~exists(select(CustomerDoc.id).where(CustomerDoc.client_id == Customer.id))
        )
        .count()
    )

    print("\n" + "═" * 55)
    print("📊  STATISTIQUES DES DONNÉES GÉNÉRÉES")
    print("═" * 55)
    print(f"   Clients            : {total_clients:>6}")
    print(f"   Comptes            : {total_comptes:>6}")
    print(f"   Documents KYC      : {total_docs:>6}")
    print(f"     dont invalides   : {docs_invalides:>6}")
    print(f"     clients sans doc : {clients_sans_doc:>6}  ← doit être 0")
    print(f"   Transactions       : {total_tx:>6}")
    print(f"   Clients PEP        : {total_pep:>6}")
    print(f"   Entrées PEP list   : {total_pep_list:>6}")
    print("═" * 55)

    from sqlalchemy import func as sqlfunc

    repartition = (
        db.query(Customer.profession_risk, sqlfunc.count(Customer.id))
        .group_by(Customer.profession_risk)
        .all()
    )
    print("   Répartition professions :")
    for risk, count in sorted(repartition, key=lambda x: x[0] or ""):
        print(f"     {(risk or 'N/A'):<10} : {count:>4} clients")

    print("\n   Scénarios obligatoires :")
    for nom, prenom in [
        ("SOGLO", "Amélie"),
        ("BIAOU", "Koffi"),
        ("OUEDRAOGO", "Fatima"),
    ]:
        c = (
            db.query(Customer)
            .filter(Customer.nom == nom, Customer.prenom == prenom)
            .first()
        )
        if c:
            print(f"     ✓ {prenom} {nom} — id={c.id}")
        else:
            print(f"     ✗ {prenom} {nom} — INTROUVABLE !")

    print("═" * 55 + "\n")

    if clients_sans_doc > 0:
        print(
            f"⚠️  ATTENTION : {clients_sans_doc} client(s) sans document KYC détecté(s) !"
        )


# ══════════════════════════════════════════════════════════════════════════
# 10. POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════════════


def main(dry_run: bool = False) -> None:
    print("\n" + "═" * 55)
    print("🚀  RiskGuard — Générateur de données de test v1.1")
    print("    500 clients béninois + 3 scénarios LBC/FT")
    print("═" * 55)

    if dry_run:
        print("\n⚠️  MODE DRY-RUN — aucune donnée ne sera écrite.\n")
        return

    t_global = time.perf_counter()
    db = SessionLocal()
    try:
        ref = Referentiels(db)
        cleanup_magloire_tables(db)

        print("🎭 Création des scénarios obligatoires...")
        t_sc = time.perf_counter()
        create_scenario_amelie_soglo(db, ref)
        create_scenario_koffi_biaou(db, ref)
        create_scenario_fatima_ouedraogo(db, ref)
        db.commit()
        print(f"   ✅ 3 scénarios créés en {time.perf_counter() - t_sc:.2f}s\n")

        generate_random_clients(db, ref, total=497)

        print_stats(db)

        total_elapsed = time.perf_counter() - t_global
        print(f"⏱  Durée totale : {total_elapsed:.1f}s")
        print("✅  Génération terminée avec succès !")
        print("    Tu peux maintenant tester le moteur de scoring.")
        print("    Voir : docs/TESTING_GUIDE.md\n")

    except RuntimeError as exc:
        print(f"\n{exc}\n")
        sys.exit(1)
    except Exception as exc:
        db.rollback()
        print(f"\n❌ Erreur inattendue : {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Génère 500 clients de test pour RiskGuard (v1.1)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche le plan sans écrire en base",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
