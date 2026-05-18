"""
scripts/generate_fake_data.py
==============================
Générateur de données de test — RiskGuard (IMF béninoises)
Produit exactement 500 clients avec profils variés + 3 scénarios obligatoires.

Auteur  : Dev B — BATAMOUSSI Marcos
Version : 1.0 — Mai 2026

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
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

# ── Permet de lancer depuis n'importe quel répertoire ─────────────────────
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faker import Faker
from sqlalchemy.orm import Session

from app.db.session import SessionLocal

# FIX: imports complets — Score, Alert, AuditLog nécessaires pour le cleanup
# (FK vers customers.id sans cascade pour Score et AuditLog → erreur à la suppression)
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
random.seed(42)          # reproductibilité
Faker.seed(42)

TOTAL_CLIENTS = 500      # nombre total à générer (hors 3 scénarios)

# ── Listes anthroponymiques béninoises ────────────────────────────────────
PRENOMS_BENINOIS = [
    "Adjovi", "Akossiwa", "Akoua", "Amenan", "Amidath",
    "Assogba", "Béatrice", "Bénédicte", "Cécile", "Clarisse",
    "Dossou", "Edwige", "Evelyne", "Fatima", "Fatoumata",
    "Félicité", "Fiacre", "Firmin", "Flore", "Gbèdji",
    "Gilles", "Grâce", "Henriette", "Hervé", "Honoré",
    "Huguette", "Idrissou", "Innocent", "Irène", "Isidore",
    "Jean-Baptiste", "Joël", "Jonas", "Joséphine", "Justine",
    "Koffi", "Kossi", "Latifa", "Lionel", "Luc",
    "Madeleine", "Marcel", "Marcelline", "Mariam", "Marie-Claire",
    "Mathieu", "Maxime", "Médard", "Modeste", "Monique",
    "Nadège", "Narcisse", "Nicaise", "Nicolas", "Norbert",
    "Odette", "Olivia", "Omar", "Onésime", "Oswald",
    "Pascal", "Patrice", "Paul", "Pauline", "Pélagie",
    "Raïmi", "Raphaël", "Regina", "René", "Richard",
    "Rosalie", "Rosine", "Rufin", "Sébastien", "Séraphin",
    "Simone", "Sipho", "Sodji", "Soumaïla", "Stanislas",
    "Sylvain", "Sylvestre", "Théodore", "Thierry", "Thomas",
    "Urbain", "Valentin", "Victor", "Victorin", "Vincent",
    "Viviane", "Xavier", "Yves", "Zacharie", "Zénab",
]

NOMS_BENINOIS = [
    "Adjagba", "Adjaï", "Adjanohoun", "Agbodjan", "Agossou",
    "Ahouandjinou", "Aïkpé", "Akindes", "Akognon", "Alagnon",
    "Alapini", "Alassane", "Alidou", "Alokpo", "Amouzou",
    "Anago", "Anonrin", "Assogba", "Azonkpon", "Biaou",
    "Bio", "Bocco", "Bossou", "Chabi", "Codjo",
    "Dako", "Dansou", "Dèdèwanou", "Dégbélo", "Dessouassi",
    "Djinadou", "Djossou", "Dossou", "Dougnon", "Dovonou",
    "Edou", "Elegbede", "Faïnou", "Fandohan", "Fassinou",
    "Ganfon", "Gbaguidi", "Gbèssémèhou", "Gbodogbe", "Gnonlonfoun",
    "Gnimassoun", "Gossou", "Gouvon", "Guèdègbé", "Hachimou",
    "Hinkati", "Houngbédji", "Hounto", "Hounyovi", "Hunlédé",
    "Igue", "Kassa", "Kérékou", "Kiki", "Klotchéou",
    "Kossou", "Kouagou", "Kpatchavi", "Kpessou", "Kpoton",
    "Lafia", "Lagnide", "Lalèyè", "Lawson", "Lédégan",
    "Lokossou", "Mawuégnon", "Medenou", "Metonnou", "Mikponhoué",
    "Montcho", "Noudéhouenou", "Ogoudèlè", "Olaniyi", "Olodo",
    "Ouédraogo", "Padonou", "Pognon", "Quenum", "Sagbohan",
    "Saka", "Sinzogan", "Soglo", "Sohouénou", "Sossou",
    "Tamou", "Tchibozo", "Tchobo", "Togbadja", "Totin",
    "Vigan", "Vodounou", "Winsou", "Yarou", "Zinsou",
]

# FIX: villes et départements béninois — fake.city() / fake.department()
# retournent des données françaises, incompatibles avec la localisation BJ
VILLES_BENINOISE = [
    "Cotonou", "Porto-Novo", "Parakou", "Abomey-Calavi", "Djougou",
    "Bohicon", "Kandi", "Lokossa", "Ouidah", "Malanville",
    "Natitingou", "Abomey", "Savalou", "Savè", "Nikki",
    "Comè", "Pobè", "Aplahoué", "Dassa-Zoumé", "Bassila",
    "Tanguiéta", "Bembèrèkè", "Tchaourou", "Dogbo", "Sèmè-Kpodji",
    "Glazoué", "Azovè", "Cové", "Zagnanado", "Allada",
    "Zogbodomè", "Toffo", "Lalo", "Athiémé", "Kétou",
    "Adja-Ouèrè", "Ifangni", "Sakété", "Kalale", "Pèrèrè",
]

DEPARTEMENTS_BENIN = [
    "Alibori", "Atacora", "Atlantique", "Borgou",
    "Collines", "Couffo", "Donga", "Littoral",
    "Mono", "Ouémé", "Plateau", "Zou",
]

# ── Professions avec leur niveau de risque ────────────────────────────────
PROFESSIONS = [
    # (code, nom, risk_level, revenu_min, revenu_max)
    ("FONCT_PUBL",    "Fonctionnaire public",              "LOW",    80_000,   350_000),
    ("SALARIE_PRIV",  "Salarié secteur privé formel",      "LOW",    70_000,   400_000),
    ("ENSEIGNANT",    "Enseignant",                        "LOW",    60_000,   200_000),
    ("INFIRMIER",     "Infirmier / Agent de santé",        "LOW",    75_000,   250_000),
    ("MILITAIRE",     "Militaire / Gendarme",              "LOW",    90_000,   300_000),
    ("AGRI_MARAICH",  "Agriculteur maraîcher",             "LOW",    30_000,   120_000),
    ("AGRI_VIVRIER",  "Agriculteur vivrier",               "LOW",    20_000,    80_000),
    ("PECHEUR",       "Pêcheur",                           "LOW",    25_000,    90_000),
    ("COMMER_LOCAL",  "Commerçant local",                  "MEDIUM", 60_000,   300_000),
    ("ARTISAN",       "Artisan / Menuisier / Couturier",   "MEDIUM", 40_000,   180_000),
    ("MOTO_TAXI",     "Conducteur zémidjan (moto-taxi)",   "MEDIUM", 35_000,   100_000),
    ("REVENDEUR",     "Revendeur informel",                "MEDIUM", 30_000,   150_000),
    ("ELEV_ANIMAL",   "Éleveur",                           "MEDIUM", 50_000,   200_000),
    ("COMMER_TRANSFR","Commerçant transfrontalier",        "HIGH",  100_000,   800_000),
    ("CHANGEUR",      "Changeur de devises / Bureau",      "HIGH",  200_000, 1_500_000),
    ("TRANSPORTEUR",  "Transporteur international",        "HIGH",  150_000,   900_000),
    ("IMPORT_EXPORT", "Importateur / Exportateur",         "HIGH",  200_000, 2_000_000),
    ("CASINO_JEU",    "Gérant casino / Parieur",           "HIGH",  300_000, 3_000_000),
    ("INCONNU",       "Activité non déclarée",             "HIGH",        0,    50_000),
]

# ── Canaux de transaction ─────────────────────────────────────────────────
CANAUX = ["MOBILE", "GUICHET", "INTERNET", "ATM"]

# ── Types d'opérations ────────────────────────────────────────────────────
TYPES_OP = ["DEPOT", "RETRAIT", "VIREMENT", "PAIEMENT"]

# ── Types de documents KYC ────────────────────────────────────────────────
TYPES_DOC = ["CNI", "PASSEPORT", "CARTE_RESIDENT", "PERMIS_CONDUIRE"]


# ══════════════════════════════════════════════════════════════════════════
# 2. CHARGEMENT DES RÉFÉRENCES (jamais hardcodé)
# ══════════════════════════════════════════════════════════════════════════

class Referentiels:
    """
    Charge et expose tous les IDs de référence depuis la DB.
    Lève une RuntimeError si une table de référence est vide
    (seed_db.py doit avoir été exécuté avant).
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._load()

    def _load(self) -> None:
        print("  📥 Chargement des référentiels...")

        # ── Pays (index par code_iso) ──────────────────────────────────
        pays_rows = self.db.query(Country).all()
        if not pays_rows:
            raise RuntimeError(
                "❌ Table 'countries' vide — exécute d'abord : python scripts/seed_db.py"
            )
        self.pays: dict[str, Country] = {p.code_iso: p for p in pays_rows}

        # Raccourcis utiles
        self.bj  = self._get_pays("BJ")   # Bénin
        self.ng  = self._get_pays("NG")   # Nigeria (frontalier)
        self.bf  = self._get_pays("BF")   # Burkina Faso (FATF)
        self.tg  = self._get_pays("TG")   # Togo (frontalier)
        self.ly  = self._get_pays("LY")   # Libye (FATF)
        self.kp  = self._get_pays("KP")   # Corée du Nord (FATF)

        # Pays FATF pour le smurfing
        self.pays_fatf: list[Country] = [
            p for p in pays_rows if p.is_fatf
        ]
        # Pays frontaliers (hors Bénin)
        self.pays_border: list[Country] = [
            p for p in pays_rows if p.is_border and p.code_iso != "BJ"
        ]

        # ── Zones de risque (index par name) ──────────────────────────
        zone_rows = self.db.query(RiskZone).all()
        if not zone_rows:
            raise RuntimeError(
                "❌ Table 'risk_zones' vide — exécute d'abord : python scripts/seed_db.py"
            )
        self.zones: dict[str, RiskZone] = {z.name: z for z in zone_rows}

        # Zones regroupées par niveau
        self.zones_faible = [
            z for z in zone_rows if z.risk_level == "FAIBLE"
        ]
        self.zones_moyen = [
            z for z in zone_rows if z.risk_level == "MOYEN"
        ]
        self.zones_eleve = [
            z for z in zone_rows if z.risk_level in ("ELEVE", "TRES_ELEVE")
        ]

        print(
            f"     ✓ {len(pays_rows)} pays  |  {len(zone_rows)} zones  chargés"
        )

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
            # Fallback : première zone disponible du niveau le plus proche
            zone = next(iter(self.zones.values()))
        return zone


# ══════════════════════════════════════════════════════════════════════════
# 3. NETTOYAGE (tables de Magloire uniquement)
# ══════════════════════════════════════════════════════════════════════════

def cleanup_magloire_tables(db: Session) -> None:
    """
    Supprime les données des tables générées (ordre FK respecté).
    Ne touche JAMAIS aux tables de référence (countries, risk_zones,
    scoring_criteria, risk_thresholds, user_roles, users).

    FIX: Ordre de suppression corrigé pour respecter les contraintes FK :
      - Score.client_id  → FK vers customers.id SANS cascade → doit être supprimé avant customers
      - Alert.client_id  → FK vers customers.id AVEC cascade → OK mais mieux explicitement
      - AuditLog.client_id → FK vers customers.id SANS cascade, nullable=True
        → les lignes non nulles bloquent la suppression des customers en PostgreSQL

    Ordre correct : audit_logs → scores → alerts → transactions → customer_docs
                    → customer_accounts → pep_list → customers
    """
    print("\n🧹 Nettoyage des tables de test...")

    counts = {
        "audit_logs (client_id non null)": db.query(AuditLog)
            .filter(AuditLog.client_id.isnot(None)).count(),
        "scores":              db.query(Score).count(),
        "alerts":              db.query(Alert).count(),
        "transactions":        db.query(Transaction).count(),
        "customer_docs":       db.query(CustomerDoc).count(),
        "customer_accounts":   db.query(CustomerAccount).count(),
        "pep_list":            db.query(PepEntry).count(),
        "customers":           db.query(Customer).count(),
    }

    # FIX: audit_logs référencent customers.id (nullable, mais PostgreSQL bloque
    # si la valeur est non nulle et que la ligne customers est supprimée).
    # On null-ise client_id dans audit_logs plutôt que de supprimer des logs utilisateur.
    from sqlalchemy import update
    db.execute(update(AuditLog).values(client_id=None))

    # FIX: scores SANS cascade → supprimer avant customers
    db.query(Score).delete(synchronize_session=False)

    # alerts AVEC cascade → la suppression clients la déclencherait automatiquement,
    # mais on supprime explicitement pour être sûr et tracer le count
    db.query(Alert).delete(synchronize_session=False)

    # Reste de la cascade standard
    db.query(Transaction).delete(synchronize_session=False)
    db.query(CustomerDoc).delete(synchronize_session=False)
    db.query(CustomerAccount).delete(synchronize_session=False)
    db.query(PepEntry).delete(synchronize_session=False)
    db.query(Customer).delete(synchronize_session=False)
    db.commit()

    for table, count in counts.items():
        print(f"   🗑  {table:<40} {count:>5} ligne(s)")

    print("   ✅ Nettoyage terminé\n")


# ══════════════════════════════════════════════════════════════════════════
# 4. HELPERS GÉNÉRIQUES
# ══════════════════════════════════════════════════════════════════════════

def _random_phone() -> str:
    """Génère un numéro béninois unique au format +229XXXXXXXX."""
    return f"+229{random.randint(60_000_000, 99_999_999)}"


def _random_date_creation(min_years: float = 0.1, max_years: float = 8.0) -> datetime:
    """Date d'ouverture aléatoire entre min et max années dans le passé."""
    days = int(random.uniform(min_years * 365, max_years * 365))
    return datetime.utcnow() - timedelta(days=days)


def _random_prenom() -> str:
    return random.choice(PRENOMS_BENINOIS)


def _random_nom() -> str:
    return random.choice(NOMS_BENINOIS).upper()


def _pick_profession() -> tuple[str, str, str, int, int]:
    return random.choice(PROFESSIONS)


def _random_revenu(rev_min: int, rev_max: int, profession_risk: str) -> Decimal:
    """Revenu cohérent avec la profession + légère dispersion."""
    base = random.randint(rev_min, rev_max)
    # Légère variation (+/- 10%)
    variation = random.uniform(0.90, 1.10)
    return Decimal(str(round(base * variation / 1000) * 1000))  # arrondi au millier


# FIX: helpers géographiques béninois
def _random_city() -> str:
    """Retourne une vraie ville béninoise (pas fake.city() qui donne des villes françaises)."""
    return random.choice(VILLES_BENINOISE)


def _random_region() -> str:
    """Retourne un vrai département béninois (pas fake.department() → données françaises)."""
    return random.choice(DEPARTEMENTS_BENIN)


# ══════════════════════════════════════════════════════════════════════════
# 5. CRÉATION DES ENTITÉS
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
    """
    Crée et flush un Customer sans commit.

    FIX: city et region utilisent maintenant des données béninoises
    via _random_city() / _random_region() au lieu de fake.city() / fake.department()
    (qui retournent des villes et départements français).
    Les champs correspondent exactement au modèle Customer.
    """
    customer = Customer(
        nom=nom,
        prenom=prenom,
        date_naissance=fake.date_of_birth(minimum_age=18, maximum_age=70),
        phone=phone or _random_phone(),
        email=email,
        profession_code=profession_code,
        profession_name=profession_name,
        profession_risk=profession_risk,
        revenus_declares=revenus,
        # FIX: ville et région béninoises
        city=city or _random_city(),
        region=region or _random_region(),
        latitude=str(round(random.uniform(6.2, 12.4), 4)),   # bbox Bénin
        longitude=str(round(random.uniform(0.8, 3.8), 4)),
        # FIX: zone_geo et pays → Integer FK vers risk_zones.id et countries.id ✓
        zone_geo=zone.id,
        pays=country.id,
        statut_pep=statut_pep,
        kyc_completion=kyc_completion,
        kyc_level=kyc_level,
        status=status,
        date_creation=date_creation or _random_date_creation(),
    )
    db.add(customer)
    db.flush()
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
    """
    Crée un compte bancaire pour le client.
    Champs : client_id, type_compte, solde_moyen, date_ouverture, status ✓
    """
    if solde_moyen is None:
        rev = float(customer.revenus_declares or 0)
        solde_moyen = Decimal(str(round(rev * random.uniform(0.5, 3.0) / 1000) * 1000))

    account = CustomerAccount(
        client_id=customer.id,
        type_compte=type_compte,
        solde_moyen=solde_moyen,
        date_ouverture=date_ouverture or (
            customer.date_creation.date() + timedelta(days=random.randint(1, 30))
        ),
        status=status,
    )
    db.add(account)
    db.flush()
    return account


def _create_doc(
    db: Session,
    customer: Customer,
    *,
    type_doc: str = "CNI",
    valide: bool = True,
    expiration_delta_days: int = 730,   # +2 ans par défaut
) -> CustomerDoc:
    """
    Crée un document KYC.
    Champs : client_id, type_doc, numero, date_expiration, valide ✓
    expiration_delta_days négatif → document expiré (date passée) — intentionnel.
    """
    doc = CustomerDoc(
        client_id=customer.id,
        type_doc=type_doc,
        numero=f"{type_doc[:2]}{fake.bothify('??########').upper()}",
        date_expiration=date.today() + timedelta(days=expiration_delta_days),
        valide=valide,
    )
    db.add(doc)
    db.flush()
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
) -> Transaction:
    """
    Crée une transaction financière.
    Champs : compte_id, montant, devise, type_op, date_op, canal,
             origine, destination, origine_pays_id, destination_pays_id ✓
    """
    tx = Transaction(
        compte_id=account.id,
        montant=montant,
        devise="XOF",
        type_op=type_op,
        date_op=datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23)),
        canal=canal,
        origine=origine_txt,
        destination=destination_txt,
        origine_pays_id=origine_pays.id if origine_pays else None,
        destination_pays_id=destination_pays.id if destination_pays else None,
    )
    db.add(tx)
    db.flush()
    return tx


def _add_to_pep_list(
    db: Session,
    customer: Customer,
    country: Country,
    *,
    fonction: str = "Personnalité politique",
    source: str = "GIABA",
) -> PepEntry:
    """
    Ajoute une entrée dans la liste PEP pour un client marqué PEP.
    Champs : nom, prenom, fonction, date_debut, date_fin, source, active, pays ✓
    """
    entry = PepEntry(
        nom=customer.nom,
        prenom=customer.prenom,
        fonction=fonction,
        date_debut=date.today() - timedelta(days=random.randint(180, 2000)),
        date_fin=None,   # toujours en fonction
        source=source,
        active=True,
        pays=country.id,
    )
    db.add(entry)
    db.flush()
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
    anomaly_factor: float = 1.0,   # 1.0 = normal, >1 = pics
) -> None:
    """
    Génère des transactions cohérentes avec le revenu mensuel.
    anomaly_factor > 1 permet de créer des pics pour les profils à risque moyen.
    """
    rev_mensuel = float(customer.revenus_declares or 50_000)

    for month in range(nb_months):
        # Entre 3 et 8 transactions par mois
        nb_tx = random.randint(3, 8)
        budget_mensuel = rev_mensuel * anomaly_factor

        for _ in range(nb_tx):
            ratio = random.uniform(0.1, 0.6)
            montant = Decimal(str(round(budget_mensuel * ratio / 500) * 500))
            montant = max(Decimal("1000"), montant)

            type_op = random.choices(
                TYPES_OP, weights=[40, 30, 20, 10]
            )[0]

            days_ago = month * 30 + random.randint(1, 28)

            # Pays source/destination : majoritairement Bénin
            dest = None
            if type_op == "VIREMENT" and random.random() < 0.15:
                dest = random.choice(ref.pays_border + [ref.bj])

            _create_transaction(
                db, account,
                montant=montant,
                type_op=type_op,
                days_ago=days_ago,
                canal=random.choice(CANAUX),
                destination_pays=dest,
            )


def _generate_smurfing_transactions(
    db: Session,
    account: CustomerAccount,
    destination_country: Country,
    *,
    nb_tx: int = 6,
) -> None:
    """
    Génère des transactions de fractionnement (smurfing).
    Montants ronds entre 400 000 et 490 000 XOF vers un pays à risque.
    """
    for i in range(nb_tx):
        # Montant rond multiple de 10 000, juste sous le seuil de 500 000
        base = random.randrange(400_000, 490_001, 10_000)
        montant = Decimal(str(base))

        _create_transaction(
            db, account,
            montant=montant,
            type_op="VIREMENT",
            days_ago=random.randint(1, 45),
            canal=random.choice(["INTERNET", "MOBILE"]),
            destination_pays=destination_country,
            destination_txt=f"Compte suspect — {destination_country.name}",
        )


# ══════════════════════════════════════════════════════════════════════════
# 7. SCÉNARIOS OBLIGATOIRES
# ══════════════════════════════════════════════════════════════════════════

def create_scenario_amelie_soglo(db: Session, ref: Referentiels) -> Customer:
    """
    SCÉNARIO A — Amélie SOGLO
    Profil FAIBLE : salarié public, zone urbaine Cotonou, KYC complet,
    transactions régulières modestes, pas PEP, relation de 4 ans.
    Score attendu : FAIBLE (< 34).
    """
    print("   🟢 Scénario A : Amélie SOGLO (risque FAIBLE)...")

    zone    = ref.zone_par_nom("CAPITALE")
    country = ref.bj

    customer = _create_customer(
        db, ref,
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
        date_creation=datetime.utcnow() - timedelta(days=4 * 365 + 120),
        phone="+22966110001",
        email="amelie.soglo@imf-test.bj",
        status="ACTIVE",
        city="Cotonou",
        region="Littoral",
    )

    # Compte épargne
    account = _create_account(
        db, customer,
        type_compte="EPARGNE",
        solde_moyen=Decimal("550000"),
        date_ouverture=date.today() - timedelta(days=4 * 365),
    )

    # 2 documents valides, loin d'expirer
    _create_doc(db, customer, type_doc="CNI",       valide=True, expiration_delta_days=900)
    _create_doc(db, customer, type_doc="PASSEPORT", valide=True, expiration_delta_days=1500)

    # Transactions régulières sur 3 mois (cohérentes avec 185 000 FCFA/mois)
    for month in range(3):
        for tx_data in [
            (80_000,  "DEPOT",    "GUICHET",  5),
            (50_000,  "RETRAIT",  "ATM",     10),
            (30_000,  "PAIEMENT", "MOBILE",  15),
            (40_000,  "VIREMENT", "INTERNET", 20),
        ]:
            montant, type_op, canal, day_offset = tx_data
            days_ago = month * 30 + day_offset
            _create_transaction(
                db, account,
                montant=Decimal(str(montant)),
                type_op=type_op,
                days_ago=days_ago,
                canal=canal,
                destination_pays=ref.bj if type_op == "VIREMENT" else None,
            )

    print(f"      ✓ Client id={customer.id}")
    return customer


def create_scenario_koffi_biaou(db: Session, ref: Referentiels) -> Customer:
    """
    SCÉNARIO B — Koffi BIAOU
    Profil MOYEN : commerçant transfrontalier, zone frontalière (Malanville),
    transactions avec pics non justifiés, pas PEP, relation 2 ans.
    Score attendu : MOYEN (34-66).
    """
    print("   🟡 Scénario B : Koffi BIAOU (risque MOYEN)...")

    zone    = ref.zone_par_nom("FRONTIERE")
    country = ref.bj

    customer = _create_customer(
        db, ref,
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
        date_creation=datetime.utcnow() - timedelta(days=2 * 365 + 45),
        phone="+22966110002",
        email="koffi.biaou@imf-test.bj",
        status="ACTIVE",
        city="Malanville",
        region="Alibori",
    )

    account = _create_account(
        db, customer,
        type_compte="COURANT",
        solde_moyen=Decimal("1250000"),
        date_ouverture=date.today() - timedelta(days=2 * 365),
    )

    # 1 document valide, 1 expirant dans 20 jours (C6 pénalisé)
    _create_doc(db, customer, type_doc="CNI",       valide=True, expiration_delta_days=800)
    _create_doc(db, customer, type_doc="PASSEPORT", valide=True, expiration_delta_days=20)

    # Transactions normales + pics (anomaly_factor=2.5)
    _generate_regular_transactions(db, account, customer, ref, nb_months=3, anomaly_factor=2.5)

    # Quelques virements vers pays frontaliers (Togo, Nigeria)
    for _ in range(3):
        dest = random.choice([ref.ng, ref.tg])
        _create_transaction(
            db, account,
            montant=Decimal(str(random.randrange(200_000, 600_000, 50_000))),
            type_op="VIREMENT",
            days_ago=random.randint(5, 60),
            canal="INTERNET",
            destination_pays=dest,
            destination_txt=f"Fournisseur {dest.name}",
        )

    # Plusieurs retraits cash répétés
    for i in range(7):
        _create_transaction(
            db, account,
            montant=Decimal(str(random.randrange(100_000, 300_000, 25_000))),
            type_op="RETRAIT",
            days_ago=random.randint(1, 80),
            canal="GUICHET",
        )

    print(f"      ✓ Client id={customer.id}")
    return customer


def create_scenario_fatima_ouedraogo(db: Session, ref: Referentiels) -> Customer:
    """
    SCÉNARIO C — Fatima OUÉDRAOGO
    Profil ÉLEVÉ : PEP avérée (épouse de ministre), changeur de devises,
    zone frontalière, KYC incomplet (doc invalide), smurfing vers Nigeria (FATF).
    Score attendu : ÉLEVÉ (≥ 67).
    """
    print("   🔴 Scénario C : Fatima OUÉDRAOGO (risque ÉLEVÉ)...")

    zone    = ref.zone_par_nom("FRONTIERE")
    country = ref.bj

    customer = _create_customer(
        db, ref,
        nom="OUEDRAOGO",
        prenom="Fatima",
        profession_code="CHANGEUR",
        profession_name="Changeur de devises / Bureau de change informel",
        profession_risk="HIGH",
        revenus=Decimal("120000"),    # revenus déclarés très bas vs transactions réelles
        zone=zone,
        country=country,
        statut_pep=True,              # PEP avérée
        kyc_completion=25,            # KYC très incomplet
        kyc_level="HIGH",
        date_creation=datetime.utcnow() - timedelta(days=45),  # cliente récente
        phone="+22966110003",
        email="fatima.ouedraogo@imf-test.bj",
        status="ACTIVE",
        city="Malanville",
        region="Alibori",
    )

    # Entrée dans la liste PEP
    _add_to_pep_list(
        db, customer, country,
        fonction="Épouse de Ministre de l'Économie — Bénin",
        source="CENTIF",
    )

    account = _create_account(
        db, customer,
        type_compte="COURANT",
        solde_moyen=Decimal("5000000"),
        date_ouverture=date.today() - timedelta(days=40),
    )

    # Document invalide + document expiré → C6 maximal
    _create_doc(db, customer, type_doc="CNI",
                valide=False,                 # INVALIDE
                expiration_delta_days=200)
    _create_doc(db, customer, type_doc="PASSEPORT",
                valide=True,
                expiration_delta_days=-30)    # EXPIRÉ depuis 30 jours

    # ── Smurfing : 6 transactions vers Nigeria (pays frontalier) ──────
    _generate_smurfing_transactions(
        db, account,
        destination_country=ref.ng,
        nb_tx=6,
    )

    # Quelques transactions vers Libye (FATF)
    for _ in range(3):
        _create_transaction(
            db, account,
            montant=Decimal(str(random.randrange(450_000, 490_001, 10_000))),
            type_op="VIREMENT",
            days_ago=random.randint(2, 30),
            canal="INTERNET",
            destination_pays=ref.ly,
            destination_txt="Compte Tripoli — Libye",
        )

    # Retraits cash massifs
    for i in range(5):
        _create_transaction(
            db, account,
            montant=Decimal(str(random.randrange(300_000, 490_001, 50_000))),
            type_op="RETRAIT",
            days_ago=random.randint(1, 40),
            canal="GUICHET",
        )

    print(f"      ✓ Client id={customer.id}")
    return customer


# ══════════════════════════════════════════════════════════════════════════
# 8. GÉNÉRATION DES 500 CLIENTS ALÉATOIRES
# ══════════════════════════════════════════════════════════════════════════

def _pick_zone_for_risk(risk: str, ref: Referentiels) -> RiskZone:
    """Choisit une zone géographique cohérente avec le niveau de risque profession."""
    if risk == "LOW":
        pool = ref.zones_faible or list(ref.zones.values())
    elif risk == "MEDIUM":
        pool = ref.zones_moyen or ref.zones_faible
    else:  # HIGH
        pool = ref.zones_eleve or ref.zones_moyen or list(ref.zones.values())

    return random.choice(pool)


def _pick_country_for_zone(zone: RiskZone, ref: Referentiels) -> Country:
    """Choisit un pays cohérent avec le niveau de risque de la zone."""
    if zone.risk_level in ("ELEVE", "TRES_ELEVE") and random.random() < 0.3:
        # 30% de chance d'être dans un pays frontalier
        candidates = [ref.ng, ref.tg, ref.bf] + [ref.bj]
        return random.choice(candidates)
    # Majorité béninois
    return random.choice([ref.bj] * 7 + list(ref.pays.values()))


def _kyc_profile(profession_risk: str) -> tuple[int, str]:
    """Retourne (kyc_completion, kyc_level) selon le risque professionnel."""
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
    """
    Retourne la liste des docs à créer avec leurs attributs.
    Plus le KYC est incomplet, plus les docs sont invalides/expirés.

    FIX: kyc_completion < 25 retournait [] → certains clients n'avaient AUCUN document.
    Le modèle CustomerDoc n'impose pas de document minimum, mais la règle métier
    exige qu'au moins un document soit toujours enregistré pour tout client,
    même si ce document est invalide/expiré (dossier ultra-incomplet).
    """
    docs = []

    if kyc_completion >= 80:
        # Dossier solide : 2 documents valides
        docs.append({"type_doc": "CNI", "valide": True,
                     "expiration_delta_days": random.randint(300, 1500)})
        if random.random() < 0.6:
            docs.append({"type_doc": "PASSEPORT", "valide": True,
                         "expiration_delta_days": random.randint(200, 1800)})

    elif kyc_completion >= 50:
        # Dossier partiel : 1 doc valide + éventuellement 1 expirant
        docs.append({"type_doc": "CNI", "valide": True,
                     "expiration_delta_days": random.randint(30, 900)})
        if random.random() < 0.4:
            docs.append({"type_doc": random.choice(TYPES_DOC), "valide": True,
                         "expiration_delta_days": random.randint(-60, 60)})  # expirant/expiré

    elif kyc_completion >= 25:
        # Dossier incomplet : 1 doc possiblement invalide
        valide = random.random() > 0.4
        docs.append({"type_doc": "CNI", "valide": valide,
                     "expiration_delta_days": random.randint(-180, 180)})

    else:
        # FIX: kyc_completion < 25 — dossier quasi-vide mais on crée quand même
        # au moins 1 document invalide ou expiré pour que customer_docs soit toujours rempli.
        # valide=False + date expirée → C6 (cohérence KYC) fortement pénalisé, ce qui est correct.
        docs.append({
            "type_doc": "CNI",
            "valide": False,
            "expiration_delta_days": random.randint(-365, -1),  # expiré
        })

    return docs


def generate_random_clients(
    db: Session,
    ref: Referentiels,
    total: int = TOTAL_CLIENTS,
) -> list[Customer]:
    """Génère `total` clients aléatoires avec profils variés."""

    print(f"\n👥 Génération de {total} clients aléatoires...")

    # Pré-calcul : ~2% de PEP parmi les aléatoires
    pep_indices = set(random.sample(range(total), max(1, int(total * 0.02))))

    # Professions à risque HIGH pour les PEP
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
    phones_used: set[str] = set()

    BATCH_SIZE = 50
    for i in range(total):

        # ── Profession ────────────────────────────────────────────────
        prof_code, prof_name, prof_risk, rev_min, rev_max = _pick_profession()

        # ── Zone & Pays ───────────────────────────────────────────────
        zone    = _pick_zone_for_risk(prof_risk, ref)
        country = _pick_country_for_zone(zone, ref)

        # ── Revenus ───────────────────────────────────────────────────
        revenus = _random_revenu(rev_min, rev_max, prof_risk)

        # ── KYC ───────────────────────────────────────────────────────
        kyc_completion, kyc_level = _kyc_profile(prof_risk)

        # ── PEP ? ─────────────────────────────────────────────────────
        is_pep = i in pep_indices

        # ── Ancienneté cohérente avec le profil ───────────────────────
        if prof_risk == "LOW":
            date_creation = _random_date_creation(0.5, 8.0)
        elif prof_risk == "MEDIUM":
            date_creation = _random_date_creation(0.3, 5.0)
        else:
            date_creation = _random_date_creation(0.1, 4.0)

        # ── Téléphone unique ──────────────────────────────────────────
        phone = _random_phone()
        while phone in phones_used:
            phone = _random_phone()
        phones_used.add(phone)

        # ── Création client ───────────────────────────────────────────
        customer = _create_customer(
            db, ref,
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
            # FIX: ville et région béninoises via les helpers corrigés
            city=_random_city(),
            region=_random_region(),
        )

        # ── PEP list ──────────────────────────────────────────────────
        if is_pep:
            _add_to_pep_list(
                db, customer, country,
                fonction=random.choice(fonctions_pep),
                source=random.choice(["GIABA", "CENTIF", "ONU"]),
            )

        # ── Compte bancaire ───────────────────────────────────────────
        type_compte = random.choice(["COURANT", "EPARGNE"])
        account = _create_account(db, customer, type_compte=type_compte)

        # ── Documents KYC ─────────────────────────────────────────────
        # FIX: _doc_profile garantit maintenant toujours au moins 1 doc
        for doc_kwargs in _doc_profile(prof_risk, kyc_completion):
            _create_doc(db, customer, **doc_kwargs)

        # ── Transactions ──────────────────────────────────────────────
        if prof_risk == "HIGH" and random.random() < 0.15:
            # 15% des HIGH → smurfing léger
            _generate_smurfing_transactions(
                db, account,
                destination_country=random.choice(ref.pays_fatf + ref.pays_border),
                nb_tx=random.randint(3, 5),
            )
        else:
            anomaly = 1.0
            if prof_risk == "HIGH":
                anomaly = random.uniform(1.5, 4.0)
            elif prof_risk == "MEDIUM":
                anomaly = random.uniform(1.0, 2.0)

            _generate_regular_transactions(
                db, account, customer, ref,
                nb_months=random.randint(1, 6),
                anomaly_factor=anomaly,
            )

        clients.append(customer)

        # ── Commit par batch pour performance ─────────────────────────
        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"   ⏳ {i + 1}/{total} clients créés...")

    db.commit()
    return clients


# ══════════════════════════════════════════════════════════════════════════
# 9. STATISTIQUES POST-GÉNÉRATION
# ══════════════════════════════════════════════════════════════════════════

def print_stats(db: Session) -> None:
    """Affiche un résumé des données générées."""
    total_clients  = db.query(Customer).count()
    total_comptes  = db.query(CustomerAccount).count()
    total_docs     = db.query(CustomerDoc).count()
    total_tx       = db.query(Transaction).count()
    total_pep      = db.query(Customer).filter(Customer.statut_pep == True).count()  # noqa: E712
    total_pep_list = db.query(PepEntry).count()

    # FIX: CustomerDoc.valide (pas CustomerDoc.valide == False en tant que champ booléen)
    # Docs invalides = valide=False OU date_expiration passée
    docs_invalides = db.query(CustomerDoc).filter(
        (CustomerDoc.valide == False) |  # noqa: E712
        (CustomerDoc.date_expiration < date.today())
    ).count()

    # FIX: clients sans aucun document (doit être 0 après correction _doc_profile)
    from sqlalchemy import select, exists
    clients_sans_doc = db.query(Customer).filter(
        ~exists(
            select(CustomerDoc.id).where(CustomerDoc.client_id == Customer.id)
        )
    ).count()

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

    # Répartition par profession_risk
    from sqlalchemy import func as sqlfunc
    repartition = (
        db.query(Customer.profession_risk, sqlfunc.count(Customer.id))
        .group_by(Customer.profession_risk)
        .all()
    )
    print("   Répartition professions :")
    for risk, count in sorted(repartition, key=lambda x: x[0] or ""):
        print(f"     {(risk or 'N/A'):<10} : {count:>4} clients")

    # Scénarios obligatoires
    print("\n   Scénarios obligatoires :")
    for nom, prenom in [("SOGLO", "Amélie"), ("BIAOU", "Koffi"), ("OUEDRAOGO", "Fatima")]:
        c = db.query(Customer).filter(
            Customer.nom == nom, Customer.prenom == prenom
        ).first()
        if c:
            print(f"     ✓ {prenom} {nom} — id={c.id}")
        else:
            print(f"     ✗ {prenom} {nom} — INTROUVABLE !")

    print("═" * 55 + "\n")

    if clients_sans_doc > 0:
        print(f"⚠️  ATTENTION : {clients_sans_doc} client(s) sans document KYC détecté(s) !")


# ══════════════════════════════════════════════════════════════════════════
# 10. POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════════════

def main(dry_run: bool = False) -> None:
    print("\n" + "═" * 55)
    print("🚀  RiskGuard — Générateur de données de test")
    print("    500 clients béninois + 3 scénarios LBC/FT")
    print("═" * 55)

    if dry_run:
        print("\n⚠️  MODE DRY-RUN — aucune donnée ne sera écrite.\n")
        return

    db = SessionLocal()
    try:
        # 1. Charger les référentiels
        ref = Referentiels(db)

        # 2. Nettoyer uniquement les tables de Magloire (ordre FK corrigé)
        cleanup_magloire_tables(db)

        # 3. Créer les 3 scénarios obligatoires en premier
        print("🎭 Création des scénarios obligatoires...")
        create_scenario_amelie_soglo(db, ref)
        create_scenario_koffi_biaou(db, ref)
        create_scenario_fatima_ouedraogo(db, ref)
        db.commit()
        print("   ✅ 3 scénarios créés\n")

        # 4. Générer les 497 clients restants (500 - 3 scénarios)
        generate_random_clients(db, ref, total=497)

        # 5. Statistiques finales
        print_stats(db)

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
        description="Génère 500 clients de test pour RiskGuard"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche le plan sans écrire en base",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
