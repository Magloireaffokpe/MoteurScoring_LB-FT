// src/utils/constants.js
// Constantes synchronisées avec generate_fake_data.py (Dev B — Marcos)

// ── Professions exactes du fake_data ─────────────────────────────────────
// Format : { code, name, risk, revenu_min, revenu_max }
export const PROFESSIONS = [
  {
    code: "FONCT_PUBL",
    name: "Fonctionnaire public",
    risk: "LOW",
    min: 80_000,
    max: 350_000,
  },
  {
    code: "SALARIE_PRIV",
    name: "Salarié secteur privé formel",
    risk: "LOW",
    min: 70_000,
    max: 400_000,
  },
  {
    code: "ENSEIGNANT",
    name: "Enseignant",
    risk: "LOW",
    min: 60_000,
    max: 200_000,
  },
  {
    code: "INFIRMIER",
    name: "Infirmier / Agent de santé",
    risk: "LOW",
    min: 75_000,
    max: 250_000,
  },
  {
    code: "MILITAIRE",
    name: "Militaire / Gendarme",
    risk: "LOW",
    min: 90_000,
    max: 300_000,
  },
  {
    code: "AGRI_MARAICH",
    name: "Agriculteur maraîcher",
    risk: "LOW",
    min: 30_000,
    max: 120_000,
  },
  {
    code: "AGRI_VIVRIER",
    name: "Agriculteur vivrier",
    risk: "LOW",
    min: 20_000,
    max: 80_000,
  },
  { code: "PECHEUR", name: "Pêcheur", risk: "LOW", min: 25_000, max: 90_000 },
  {
    code: "COMMER_LOCAL",
    name: "Commerçant local",
    risk: "MEDIUM",
    min: 60_000,
    max: 300_000,
  },
  {
    code: "ARTISAN",
    name: "Artisan / Menuisier / Couturier",
    risk: "MEDIUM",
    min: 40_000,
    max: 180_000,
  },
  {
    code: "MOTO_TAXI",
    name: "Conducteur zémidjan (moto-taxi)",
    risk: "MEDIUM",
    min: 35_000,
    max: 100_000,
  },
  {
    code: "REVENDEUR",
    name: "Revendeur informel",
    risk: "MEDIUM",
    min: 30_000,
    max: 150_000,
  },
  {
    code: "ELEV_ANIMAL",
    name: "Éleveur",
    risk: "MEDIUM",
    min: 50_000,
    max: 200_000,
  },
  {
    code: "COMMER_TRANSFR",
    name: "Commerçant transfrontalier",
    risk: "HIGH",
    min: 100_000,
    max: 800_000,
  },
  {
    code: "CHANGEUR",
    name: "Changeur de devises / Bureau",
    risk: "HIGH",
    min: 200_000,
    max: 1_500_000,
  },
  {
    code: "TRANSPORTEUR",
    name: "Transporteur international",
    risk: "HIGH",
    min: 150_000,
    max: 900_000,
  },
  {
    code: "IMPORT_EXPORT",
    name: "Importateur / Exportateur",
    risk: "HIGH",
    min: 200_000,
    max: 2_000_000,
  },
  {
    code: "CASINO_JEU",
    name: "Gérant casino / Parieur",
    risk: "HIGH",
    min: 300_000,
    max: 3_000_000,
  },
  {
    code: "INCONNU",
    name: "Activité non déclarée",
    risk: "HIGH",
    min: 0,
    max: 50_000,
  },
];

// ── Types de documents KYC (exactement ceux de fake_data) ─────────────────
export const TYPES_DOC = [
  "CNI",
  "PASSEPORT",
  "CARTE_RESIDENT",
  "PERMIS_CONDUIRE",
];

// ── Types de comptes (CustomerAccount.type_compte) ────────────────────────
export const TYPES_COMPTE = ["COURANT", "EPARGNE"];

// ── Statuts compte (CustomerAccount.status) ────────────────────────────────
export const STATUTS_COMPTE = ["ACTIF", "BLOQUE"];

// ── Statuts client (Customer.status) ──────────────────────────────────────
export const STATUTS_CLIENT = ["ACTIVE", "INACTIVE", "SUSPENDED"];

// ── Niveaux KYC (Customer.kyc_level) ─────────────────────────────────────
export const KYC_LEVELS = ["LOW", "MEDIUM", "HIGH"];

// ── Niveaux de risque profession (Customer.profession_risk) ───────────────
export const PROFESSION_RISKS = ["LOW", "MEDIUM", "HIGH"];

// ── Canaux de transaction ─────────────────────────────────────────────────
export const CANAUX = ["MOBILE", "GUICHET", "INTERNET", "ATM"];

// ── Types d'opération (Transaction.type_op) ────────────────────────────────
export const TYPES_OP = ["DEPOT", "RETRAIT", "VIREMENT", "PAIEMENT"];

// ── Sources PEP (PepEntry.source) ─────────────────────────────────────────
export const PEP_SOURCES = ["CENTIF", "GIABA", "ONU", "FATF", "AUTRE"];

// ── Pays référentiels (mock — utilisé si GET /api/countries absent) ──
// Synchronisé avec seed_db.py → seed_countries()
export const MOCK_COUNTRIES = [
  {
    id: 1,
    code_iso: "BJ",
    name: "Bénin",
    is_uemoa: true,
    is_border: false,
    is_fatf: false,
  },
  {
    id: 2,
    code_iso: "SN",
    name: "Sénégal",
    is_uemoa: true,
    is_border: false,
    is_fatf: false,
  },
  {
    id: 3,
    code_iso: "ML",
    name: "Mali",
    is_uemoa: true,
    is_border: false,
    is_fatf: true,
  },
  {
    id: 4,
    code_iso: "BF",
    name: "Burkina Faso",
    is_uemoa: true,
    is_border: true,
    is_fatf: true,
  },
  {
    id: 5,
    code_iso: "CI",
    name: "Côte d'Ivoire",
    is_uemoa: true,
    is_border: false,
    is_fatf: false,
  },
  {
    id: 6,
    code_iso: "TG",
    name: "Togo",
    is_uemoa: true,
    is_border: true,
    is_fatf: false,
  },
  {
    id: 7,
    code_iso: "NE",
    name: "Niger",
    is_uemoa: true,
    is_border: true,
    is_fatf: false,
  },
  {
    id: 8,
    code_iso: "GW",
    name: "Guinée-Bissau",
    is_uemoa: true,
    is_border: false,
    is_fatf: false,
  },
  {
    id: 9,
    code_iso: "NG",
    name: "Nigeria",
    is_uemoa: false,
    is_border: true,
    is_fatf: false,
  },
  {
    id: 10,
    code_iso: "LY",
    name: "Libye",
    is_uemoa: false,
    is_border: false,
    is_fatf: true,
  },
  {
    id: 11,
    code_iso: "IR",
    name: "Iran",
    is_uemoa: false,
    is_border: false,
    is_fatf: true,
  },
  {
    id: 12,
    code_iso: "KP",
    name: "Corée du Nord",
    is_uemoa: false,
    is_border: false,
    is_fatf: true,
  },
  {
    id: 13,
    code_iso: "GH",
    name: "Ghana",
    is_uemoa: false,
    is_border: false,
    is_fatf: false,
  },
  {
    id: 14,
    code_iso: "FR",
    name: "France",
    is_uemoa: false,
    is_border: false,
    is_fatf: false,
  },
  {
    id: 15,
    code_iso: "CN",
    name: "Chine",
    is_uemoa: false,
    is_border: false,
    is_fatf: false,
  },
];

// ── Zones de risque (mock — synchronisé avec seed_db.py → seed_risk_zones) ──
export const MOCK_RISK_ZONES = [
  {
    id: 1,
    name: "CAPITALE",
    risk_level: "FAIBLE",
    description: "Zone urbaine centrale, infrastructure bancaire développée",
  },
  {
    id: 2,
    name: "URBAINE",
    risk_level: "FAIBLE",
    description: "Zone urbaine stable, accès aux services financiers",
  },
  {
    id: 3,
    name: "SEMI_URBAINE",
    risk_level: "MOYEN",
    description: "Zone périphérique, traçabilité partielle des flux",
  },
  {
    id: 4,
    name: "RURALE",
    risk_level: "MOYEN",
    description: "Zone rurale, faible bancarisation",
  },
  {
    id: 5,
    name: "FRONTIERE",
    risk_level: "ELEVE",
    description: "Zone frontalière à risque (Nigeria, Togo, Burkina)",
  },
  {
    id: 6,
    name: "CONFLIT",
    risk_level: "TRES_ELEVE",
    description: "Zone de conflit actif ou sans infrastructure bancaire",
  },
];

// ── Fonctions PEP (synchronisé avec generate_fake_data.py fonctions_pep) ──
export const FONCTIONS_PEP = [
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
];

// ── Critères de scoring (mock — si GET /api/admin/scoring-criteria absent) ──
// Synchronisé avec seed_db.py → seed_scoring_criteria()
export const MOCK_CRITERIA = [
  {
    id: 1,
    code: "C1",
    name: "Profil professionnel",
    weight: 20,
    description: "Évaluation du risque lié à la profession",
  },
  {
    id: 2,
    code: "C2",
    name: "Zone géographique",
    weight: 20,
    description: "Risque lié à la localisation du client",
  },
  {
    id: 3,
    code: "C3",
    name: "Historique transactionnel",
    weight: 25,
    description: "Analyse des patterns de transactions",
  },
  {
    id: 4,
    code: "C4",
    name: "Ancienneté et fidélité",
    weight: 10,
    description: "Durée de la relation client avec l'IMF",
  },
  {
    id: 5,
    code: "C5",
    name: "Statut PEP",
    weight: 15,
    description: "Personne Politiquement Exposée",
  },
  {
    id: 6,
    code: "C6",
    name: "Cohérence KYC",
    weight: 10,
    description: "Complétude et cohérence du dossier KYC",
  },
];

// ── Seuils de risque (mock — synchronisé avec seed_db.py → seed_risk_thresholds) ──
export const MOCK_THRESHOLDS = [
  {
    id: 1,
    category: "FAIBLE",
    score_min: 0,
    score_max: 33,
    required_action: "Vigilance standard. Révision annuelle du score.",
  },
  {
    id: 2,
    category: "MOYEN",
    score_min: 34,
    score_max: 66,
    required_action: "Vigilance renforcée. Révision semestrielle obligatoire.",
  },
  {
    id: 3,
    category: "ELEVE",
    score_min: 67,
    score_max: 100,
    required_action:
      "Vigilance maximale. Déclaration de Soupçon (SAR) à la CENTIF.",
  },
];

// ── Statistiques par défaut du Dashboard (mock) ───────────────────────────
export const MOCK_DASHBOARD_STATS = {
  total_clients: 500,
  clients_by_kyc_level: { LOW: 150, MEDIUM: 250, HIGH: 100 },
  clients_by_risk_category: { FAIBLE: 300, MOYEN: 150, ÉLEVÉ: 50 },
  open_alerts_count: 12,
  transactions_last_30d: { count: 2450, total_amount: 125_000_000 },
};

