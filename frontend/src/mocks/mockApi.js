// src/mocks/mockApi.js
// ══════════════════════════════════════════════════════════════════
// Intercepteur Axios — simule TOUTES les réponses backend
// Activer : mettre VITE_USE_MOCKS=true dans .env
// ══════════════════════════════════════════════════════════════════

import { api } from "../services/api";

// ── Données fictives ───────────────────────────────────────────────

const MOCK_USER_ADMIN = {
  access_token: "mock-jwt-admin-token",
  token_type: "bearer",
  user_id: "usr-admin-0001",
  role: "admin",
};

const MOCK_USER_COMPLIANCE = {
  access_token: "mock-jwt-compliance-token",
  token_type: "bearer",
  user_id: "usr-co-0002",
  role: "compliance_officer",
};

const MOCK_CLIENTS = [
  {
    id: "c-001",
    nom: "BIAOU",
    prenom: "Koffi",
    phone: "+22966110001",
    email: "koffi@test.bj",
    profession_name: "Commerçant transfrontalier",
    profession_risk: "HIGH",
    revenus_declares: 350000,
    city: "Malanville",
    kyc_completion: 65,
    kyc_level: "MEDIUM",
    statut_pep: false,
    status: "ACTIVE",
    zone_geo_classification: "FRONTIERE",
    date_creation: "2024-01-15T10:00:00Z",
    current_score: 46,
    risk_category: "MOYEN",
    accounts: [
      {
        id: "a-001",
        type_compte: "COURANT",
        solde_moyen: 1250000,
        status: "ACTIF",
      },
    ],
    documents: [
      {
        id: "d-001",
        type_doc: "CNI",
        numero: "B123456",
        date_expiration: "2027-12-31",
        valide: true,
      },
    ],
  },
  {
    id: "c-002",
    nom: "SOGLO",
    prenom: "Amélie",
    phone: "+22966110002",
    email: "amelie@test.bj",
    profession_name: "Fonctionnaire public",
    profession_risk: "LOW",
    revenus_declares: 185000,
    city: "Cotonou",
    kyc_completion: 95,
    kyc_level: "LOW",
    statut_pep: false,
    status: "ACTIVE",
    zone_geo_classification: "CAPITALE",
    date_creation: "2022-06-01T08:00:00Z",
    current_score: 9,
    risk_category: "FAIBLE",
    accounts: [
      {
        id: "a-002",
        type_compte: "EPARGNE",
        solde_moyen: 550000,
        status: "ACTIF",
      },
    ],
    documents: [
      {
        id: "d-002",
        type_doc: "CNI",
        numero: "A987654",
        date_expiration: "2028-06-30",
        valide: true,
      },
      {
        id: "d-003",
        type_doc: "PASSEPORT",
        numero: "P123456",
        date_expiration: "2029-01-15",
        valide: true,
      },
    ],
  },
  {
    id: "c-003",
    nom: "OUEDRAOGO",
    prenom: "Fatima",
    phone: "+22966110003",
    email: "fatima@test.bj",
    profession_name: "Changeur de devises",
    profession_risk: "HIGH",
    revenus_declares: 120000,
    city: "Cotonou",
    kyc_completion: 25,
    kyc_level: "HIGH",
    statut_pep: true,
    status: "ACTIVE",
    zone_geo_classification: "FRONTIERE",
    date_creation: "2026-03-10T14:00:00Z",
    current_score: 78,
    risk_category: "ÉLEVÉ",
    accounts: [
      {
        id: "a-003",
        type_compte: "COURANT",
        solde_moyen: 5000000,
        status: "ACTIF",
      },
    ],
    documents: [
      {
        id: "d-004",
        type_doc: "CNI",
        numero: "X999999",
        date_expiration: "2025-01-01",
        valide: false,
      },
    ],
  },
  {
    id: "c-004",
    nom: "DOSSOU",
    prenom: "Narcisse",
    phone: "+22966110004",
    email: "narcisse@test.bj",
    profession_name: "Agriculteur maraîcher",
    profession_risk: "LOW",
    revenus_declares: 80000,
    city: "Bohicon",
    kyc_completion: 70,
    kyc_level: "LOW",
    statut_pep: false,
    status: "ACTIVE",
    zone_geo_classification: "RURALE",
    date_creation: "2023-03-20T09:00:00Z",
    current_score: 18,
    risk_category: "FAIBLE",
    accounts: [],
    documents: [],
  },
  {
    id: "c-005",
    nom: "AGBODJAN",
    prenom: "Sylvestre",
    phone: "+22966110005",
    email: null,
    profession_name: "Transporteur international",
    profession_risk: "HIGH",
    revenus_declares: 500000,
    city: "Parakou",
    kyc_completion: 50,
    kyc_level: "MEDIUM",
    statut_pep: false,
    status: "ACTIVE",
    zone_geo_classification: "SEMI_URBAINE",
    date_creation: "2024-08-01T11:00:00Z",
    current_score: 55,
    risk_category: "MOYEN",
    accounts: [],
    documents: [],
  },
];

const MOCK_SCORES = {
  "c-001": [
    {
      id: "s-001",
      client_id: "c-001",
      global_score: 46,
      risk_category: "MOYEN",
      detail_json: { C1: 13.0, C2: 13.0, C3: 12.5, C4: 3.5, C5: 0.0, C6: 4.0 },
      is_current: true,
      scored_by: "AUTOMATED",
      scored_at: "2026-05-10T08:00:00Z",
      calcule_par: "AUTOMATED",
    },
    {
      id: "s-002",
      client_id: "c-001",
      global_score: 42,
      risk_category: "MOYEN",
      detail_json: { C1: 13.0, C2: 13.0, C3: 10.0, C4: 3.5, C5: 0.0, C6: 3.0 },
      is_current: false,
      scored_by: "AUTOMATED",
      scored_at: "2026-04-01T08:00:00Z",
      calcule_par: "AUTOMATED",
    },
  ],
  "c-002": [
    {
      id: "s-003",
      client_id: "c-002",
      global_score: 9,
      risk_category: "FAIBLE",
      detail_json: { C1: 2.0, C2: 2.0, C3: 2.5, C4: 1.0, C5: 0.0, C6: 1.0 },
      is_current: true,
      scored_by: "AUTOMATED",
      scored_at: "2026-05-08T10:00:00Z",
      calcule_par: "AUTOMATED",
    },
  ],
  "c-003": [
    {
      id: "s-004",
      client_id: "c-003",
      global_score: 78,
      risk_category: "ÉLEVÉ",
      detail_json: {
        C1: 13.0,
        C2: 13.0,
        C3: 21.25,
        C4: 7.5,
        C5: 15.0,
        C6: 8.5,
      },
      is_current: true,
      scored_by: "AUTOMATED",
      scored_at: "2026-05-11T14:00:00Z",
      calcule_par: "AUTOMATED",
    },
  ],
  "c-004": [
    {
      id: "s-005",
      client_id: "c-004",
      global_score: 18,
      risk_category: "FAIBLE",
      detail_json: { C1: 2.0, C2: 3.5, C3: 2.5, C4: 3.5, C5: 0.0, C6: 4.0 },
      is_current: true,
      scored_by: "AUTOMATED",
      scored_at: "2026-05-09T09:00:00Z",
      calcule_par: "AUTOMATED",
    },
  ],
  "c-005": [
    {
      id: "s-006",
      client_id: "c-005",
      global_score: 55,
      risk_category: "MOYEN",
      detail_json: { C1: 13.0, C2: 7.0, C3: 15.0, C4: 6.0, C5: 0.0, C6: 8.0 },
      is_current: true,
      scored_by: "AUTOMATED",
      scored_at: "2026-05-07T11:00:00Z",
      calcule_par: "AUTOMATED",
    },
  ],
};

let MOCK_TRANSACTIONS = {
  "c-001": [
    {
      id: "tx-001",
      compte_id: "a-001",
      montant: 500000.0,
      devise: "XOF",
      type_op: "DEPOT",
      date_op: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
      canal: "GUICHET",
      origine: "BIAOU Koffi",
      destination: "Compte Courant",
      origine_pays_id: 1,
      destination_pays_id: 1,
    },
    {
      id: "tx-002",
      compte_id: "a-001",
      montant: 120000.0,
      devise: "XOF",
      type_op: "RETRAIT",
      date_op: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
      canal: "ATM",
      origine: "Compte Courant",
      destination: "ATM Malanville",
      origine_pays_id: 1,
      destination_pays_id: 1,
    }
  ],
  "c-002": [
    {
      id: "tx-003",
      compte_id: "a-002",
      montant: 85000.0,
      devise: "XOF",
      type_op: "DEPOT",
      date_op: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
      canal: "MOBILE",
      origine: "SOGLO Amélie",
      destination: "Compte Épargne",
      origine_pays_id: 1,
      destination_pays_id: 1,
    }
  ],
  "c-003": [
    {
      id: "tx-004",
      compte_id: "a-003",
      montant: 1500000.0,
      devise: "XOF",
      type_op: "VIREMENT",
      date_op: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
      canal: "INTERNET",
      origine: "Société X",
      destination: "OUEDRAOGO Fatima",
      origine_pays_id: 2,
      destination_pays_id: 1,
    }
  ],
  "c-004": [],
  "c-005": [],
};

const MOCK_ALERTS = [
  {
    id: "al-001",
    client_id: "c-003",
    customer_name: "Fatima OUEDRAOGO",
    type_alerte: "SCORE_ELEVE",
    risk_level: "HIGH",
    statut: "OPEN",
    description: "Score de risque élevé (78/100) — seuil ÉLEVÉ atteint",
    date_creation: "2026-05-11T14:01:00Z",
    sar_declare: false,
    action_taken: null,
    action_notes: null,
  },
  {
    id: "al-002",
    client_id: "c-001",
    customer_name: "Koffi BIAOU",
    type_alerte: "KYC_INCOMPLET",
    risk_level: "MEDIUM",
    statut: "UNDER_REVIEW",
    description: "Document expirant dans 30 jours",
    date_creation: "2026-05-08T10:00:00Z",
    sar_declare: false,
    action_taken: "CONDITIONAL_APPROVAL",
    action_notes: "Justificatif fourni",
  },
  {
    id: "al-003",
    client_id: "c-005",
    customer_name: "Sylvestre AGBODJAN",
    type_alerte: "SCORE_ELEVE",
    risk_level: "MEDIUM",
    statut: "CLOSED",
    description: "Score modéré surveillé",
    date_creation: "2026-04-20T08:00:00Z",
    sar_declare: false,
    action_taken: "NO_ACTION",
    action_notes: "Situation normale",
  },
];

const MOCK_DASHBOARD_STATS = {
  total_clients: 500,
  clients_by_kyc_level: { LOW: 150, MEDIUM: 250, HIGH: 100 },
  clients_by_risk_category: { FAIBLE: 300, MOYEN: 150, ÉLEVÉ: 50 },
  open_alerts_count: 12,
  transactions_last_30d: { count: 2450, total_amount: 125_000_000 },
};

const MOCK_AUDIT_LOGS = [
  {
    id: "log-001",
    user_id: "usr-admin-0001",
    action: "SCORING_CALCULATE",
    resource_type: "customer",
    resource_id: "c-003",
    timestamp: "2026-05-11T14:00:00Z",
    ip_address: "192.168.1.10",
  },
  {
    id: "log-002",
    user_id: "usr-co-0002",
    action: "EXPORT_CUSTOMER_PDF",
    resource_type: "customer",
    resource_id: "c-001",
    timestamp: "2026-05-10T09:30:00Z",
    ip_address: "192.168.1.11",
  },
  {
    id: "log-003",
    user_id: "usr-admin-0001",
    action: "SCORING_RESCORE",
    resource_type: "customer",
    resource_id: "c-002",
    timestamp: "2026-05-09T15:00:00Z",
    ip_address: "192.168.1.10",
  },
  {
    id: "log-004",
    user_id: "usr-co-0002",
    action: "VIEW_CUSTOMER",
    resource_type: "customer",
    resource_id: "c-003",
    timestamp: "2026-05-08T11:00:00Z",
    ip_address: "192.168.1.12",
  },
];

const MOCK_CRITERIA = [
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
    description: "Personne Politiquement Exposée — GIABA",
  },
  {
    id: 6,
    code: "C6",
    name: "Cohérence KYC",
    weight: 10,
    description: "Complétude et cohérence du dossier KYC",
  },
];

const MOCK_THRESHOLDS = [
  {
    id: 1,
    category: "FAIBLE",
    score_min: 0,
    score_max: 33,
    required_action: "Vigilance standard. Révision annuelle.",
  },
  {
    id: 2,
    category: "MOYEN",
    score_min: 34,
    score_max: 66,
    required_action: "Vigilance renforcée. Révision semestrielle.",
  },
  {
    id: 3,
    category: "ELEVE",
    score_min: 67,
    score_max: 100,
    required_action: "Déclaration CENTIF obligatoire.",
  },
];

// ── Helpers ────────────────────────────────────────────────────────
function delay(ms = 300) {
  return new Promise((r) => setTimeout(r, ms));
}

function paginate(items, skip = 0, limit = 25) {
  const sliced = items.slice(skip, skip + limit);
  return { items: sliced, total: items.length, skip, limit };
}

// ── Intercepteur principal ─────────────────────────────────────────
export function setupMocks() {
  api.interceptors.request.use(async (config) => {
    await delay(200); // simule latence réseau

    const method = config.method?.toUpperCase();
    const url = config.url || "";
    const params = config.params || {};

    // ── Auth ──────────────────────────────────────────────────────
    if (method === "POST" && url === "/auth/login") {
      const body = typeof config.data === "string" ? JSON.parse(config.data || "{}") : (config.data || {});
      // admin / admin1234  ou  agent01 / password123
      const isAdmin = body.login === "admin";
      config.adapter = async () => ({
        data: isAdmin ? MOCK_USER_ADMIN : MOCK_USER_COMPLIANCE,
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    if (method === "GET" && url === "/auth/me") {
      config.adapter = async () => ({
        data: {
          id: "usr-admin-0001",
          login: "admin",
          full_name: "Admin RiskGuard",
          email: "admin@imf.bj",
          role: "admin",
          is_active: true,
        },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    // ── Dashboard ─────────────────────────────────────────────────
    if (method === "GET" && url === "/api/dashboard/stats") {
      config.adapter = async () => ({
        data: MOCK_DASHBOARD_STATS,
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }
    if (method === "GET" && url === "/api/dashboard/alerts") {
      config.adapter = async () => ({
        data: { items: MOCK_ALERTS.slice(0, 5) },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }
    if (method === "GET" && url === "/api/dashboard/pep") {
      const pepClients = MOCK_CLIENTS.filter((c) => c.statut_pep);
      config.adapter = async () => ({
        data: { items: pepClients, total: pepClients.length },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    // ── Clients ───────────────────────────────────────────────────
    if (method === "GET" && url === "/api/clients") {
      let filtered = [...MOCK_CLIENTS];
      if (params.search)
        filtered = filtered.filter(
          (c) =>
            c.nom.toLowerCase().includes(params.search.toLowerCase()) ||
            c.prenom.toLowerCase().includes(params.search.toLowerCase()),
        );
      if (params.kyc_level)
        filtered = filtered.filter((c) => c.kyc_level === params.kyc_level);
      if (params.statut_pep !== undefined)
        filtered = filtered.filter(
          (c) => String(c.statut_pep) === params.statut_pep,
        );
      const result = paginate(filtered, params.skip || 0, params.limit || 25);
      config.adapter = async () => ({
        data: result,
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    if (
      method === "GET" &&
      url.match(/^\/api\/clients\/[^/]+$/) &&
      !url.includes("/scores") &&
      !url.includes("/alerts")
    ) {
      const id = url.split("/").pop();
      const client = MOCK_CLIENTS.find((c) => c.id === id) || MOCK_CLIENTS[0];
      config.adapter = async () => ({
        data: client,
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    if (method === "POST" && url === "/api/clients") {
      const body = typeof config.data === "string" ? JSON.parse(config.data || "{}") : (config.data || {});
      const newClient = {
        id: `c-new-${Date.now()}`,
        nom: body.nom || "NOUVEAU",
        prenom: body.prenom || "Client",
        phone: body.phone || null,
        email: body.email || null,
        profession_code: body.profession_code || null,
        profession_name: body.profession_name || null,
        profession_risk: body.profession_risk || "LOW",
        revenus_declares: body.revenus_declares || 0,
        city: body.city || null,
        region: body.region || null,
        zone_geo: body.zone_geo || null,
        pays: body.pays || null,
        statut_pep: body.statut_pep || false,
        status: "ACTIVE",
        date_creation: new Date().toISOString(),
        kyc_completion: 0,
        kyc_level: "LOW",
      };
      config.adapter = async () => ({
        data: newClient,
        status: 201,
        statusText: "Created",
        headers: {},
        config,
      });
      return config;
    }

    // ── Transactions ──────────────────────────────────────────────
    if (method === "GET" && url.match(/^\/api\/customers\/[^/]+\/transactions$/)) {
      const clientId = url.split("/")[3];
      const txs = MOCK_TRANSACTIONS[clientId] || [];
      config.adapter = async () => ({
        data: { items: txs, total: txs.length, skip: 0, limit: 100 },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    if (method === "POST" && url.match(/^\/api\/customers\/[^/]+\/transactions$/)) {
      const clientId = url.split("/")[3];
      const body = typeof config.data === "string" ? JSON.parse(config.data || "{}") : (config.data || {});
      const newTx = {
        id: `tx-${Date.now()}`,
        compte_id: body.compte_id || `acc-${Date.now()}`,
        montant: Number(body.montant || 0),
        devise: body.devise || "XOF",
        type_op: body.type_op || "DEPOT",
        date_op: body.date_op || new Date().toISOString(),
        canal: body.canal || "GUICHET",
        origine: body.origine || "Client",
        destination: body.destination || "Compte",
        origine_pays_id: Number(body.origine_pays_id || 1),
        destination_pays_id: Number(body.destination_pays_id || 1),
      };
      if (!MOCK_TRANSACTIONS[clientId]) {
        MOCK_TRANSACTIONS[clientId] = [];
      }
      MOCK_TRANSACTIONS[clientId].unshift(newTx);

      config.adapter = async () => ({
        data: newTx,
        status: 201,
        statusText: "Created",
        headers: {},
        config,
      });
      return config;
    }

    // ── Scores ────────────────────────────────────────────────────
    if (method === "GET" && url.match(/^\/api\/customers\/[^/]+\/scores$/)) {
      const clientId = url.split("/")[3];
      const scores = MOCK_SCORES[clientId] || [];
      config.adapter = async () => ({
        data: { items: scores, total: scores.length },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    if (method === "POST" && url === "/api/scoring") {
      const body = typeof config.data === "string" ? JSON.parse(config.data || "{}") : (config.data || {});
      const existing = Object.values(MOCK_SCORES)
        .flat()
        .find((s) => s.client_id === body.customer_id);
      const result = existing || {
        id: `s-new-${Date.now()}`,
        customer_id: body.customer_id,
        global_score: Math.floor(Math.random() * 60) + 10,
        risk_category: "MOYEN",
        is_current: true,
        detail_json: { C1: 9, C2: 10, C3: 12, C4: 3.5, C5: 0, C6: 4 },
        scored_by: "AUTOMATED",
        scored_at: new Date().toISOString(),
      };
      config.adapter = async () => ({
        data: result,
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    if (method === "POST" && url === "/api/scoring/rescore") {
      const body = typeof config.data === "string" ? JSON.parse(config.data || "{}") : (config.data || {});
      const newScore = Math.floor(Math.random() * 80) + 10;
      const cat =
        newScore >= 67 ? "ÉLEVÉ" : newScore >= 34 ? "MOYEN" : "FAIBLE";
      config.adapter = async () => ({
        data: {
          id: `s-rescore-${Date.now()}`,
          customer_id: body.customer_id,
          global_score: newScore,
          risk_category: cat,
          is_current: true,
          detail_json: {
            C1: +(newScore * 0.2).toFixed(2),
            C2: +(newScore * 0.2).toFixed(2),
            C3: +(newScore * 0.25).toFixed(2),
            C4: +(newScore * 0.1).toFixed(2),
            C5: 0,
            C6: +(newScore * 0.1).toFixed(2),
          },
          scored_by: "AUTOMATED",
          scored_at: new Date().toISOString(),
        },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    if (method === "POST" && url === "/api/scoring/rescore-all") {
      config.adapter = async () => ({
        data: {
          message: "Rescoring global terminé",
          rescored: 5,
          critical: 1,
        },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    if (method === "GET" && url.match(/^\/api\/scores\//)) {
      const id = url.split("/").pop();
      const score =
        Object.values(MOCK_SCORES)
          .flat()
          .find((s) => s.id === id) || Object.values(MOCK_SCORES).flat()[0];
      config.adapter = async () => ({
        data: score,
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    // ── Alertes ───────────────────────────────────────────────────
    if (method === "GET" && url === "/api/alerts") {
      let filtered = [...MOCK_ALERTS];
      if (params.statut)
        filtered = filtered.filter((a) => a.statut === params.statut);
      if (params.risk_level)
        filtered = filtered.filter((a) => a.risk_level === params.risk_level);
      config.adapter = async () => ({
        data: paginate(filtered, params.skip || 0, params.limit || 25),
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    if (method === "GET" && url.match(/^\/api\/customers\/[^/]+\/alerts$/)) {
      const clientId = url.split("/")[3];
      const alerts = MOCK_ALERTS.filter((a) => a.client_id === clientId);
      config.adapter = async () => ({
        data: { items: alerts, total: alerts.length },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    if (method === "PUT" && url.match(/^\/api\/alerts\//)) {
      const body = typeof config.data === "string" ? JSON.parse(config.data || "{}") : (config.data || {});
      config.adapter = async () => ({
        data: {
          id: url.split("/").pop(),
          ...body,
          action_date: new Date().toISOString(),
        },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    if (method === "POST" && url === "/api/alerts") {
      const body = typeof config.data === "string" ? JSON.parse(config.data || "{}") : (config.data || {});
      config.adapter = async () => ({
        data: {
          id: `al-new-${Date.now()}`,
          ...body,
          statut: "OPEN",
          date_creation: new Date().toISOString(),
        },
        status: 201,
        statusText: "Created",
        headers: {},
        config,
      });
      return config;
    }

    // ── Exports ───────────────────────────────────────────────────
    if (method === "GET" && url.match(/\/pdf$|\/csv$/)) {
      const isPdf = url.endsWith(".pdf") || url.includes("/pdf");
      const fakeContent = isPdf
        ? "%PDF-1.4 1 0 obj Mock PDF RiskGuard endobj"
        : "Date;Montant;Devise;Type\n2026-05-01;150000;XOF;DEPOT\n2026-04-15;80000;XOF;RETRAIT";
      const blob = new Blob([fakeContent], {
        type: isPdf ? "application/pdf" : "text/csv",
      });
      config.adapter = async () => ({
        data: blob,
        status: 200,
        statusText: "OK",
        headers: { "content-type": isPdf ? "application/pdf" : "text/csv" },
        config,
      });
      return config;
    }

    // ── Référentiels ──────────────────────────────────────────────
    if (method === "GET" && url === "/api/referentials/countries") {
      const countries = [
        {
          id: 1,
          code_iso: "BJ",
          name: "Bénin",
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
          id: 4,
          code_iso: "BF",
          name: "Burkina Faso",
          is_uemoa: true,
          is_border: true,
          is_fatf: true,
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
      ];
      config.adapter = async () => ({
        data: countries,
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    if (method === "GET" && url === "/api/referentials/risk-zones") {
      const zones = [
        {
          id: 1,
          name: "CAPITALE",
          risk_level: "FAIBLE",
          description: "Zone urbaine centrale",
        },
        {
          id: 2,
          name: "URBAINE",
          risk_level: "FAIBLE",
          description: "Zone urbaine stable",
        },
        {
          id: 3,
          name: "SEMI_URBAINE",
          risk_level: "MOYEN",
          description: "Zone périphérique",
        },
        {
          id: 4,
          name: "RURALE",
          risk_level: "MOYEN",
          description: "Zone rurale",
        },
        {
          id: 5,
          name: "FRONTIERE",
          risk_level: "ELEVE",
          description: "Zone frontalière à risque",
        },
        {
          id: 6,
          name: "CONFLIT",
          risk_level: "TRES_ELEVE",
          description: "Zone de conflit actif",
        },
      ];
      config.adapter = async () => ({
        data: zones,
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    // ── Admin ─────────────────────────────────────────────────────
    if (method === "GET" && url === "/api/admin/scoring-criteria") {
      config.adapter = async () => ({
        data: { items: MOCK_CRITERIA },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }
    if (method === "PUT" && url.match(/^\/api\/admin\/scoring-criteria\//)) {
      config.adapter = async () => ({
        data: { success: true },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }
    if (method === "GET" && url === "/api/admin/risk-thresholds") {
      config.adapter = async () => ({
        data: { items: MOCK_THRESHOLDS },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }
    if (method === "PUT" && url.match(/^\/api\/admin\/risk-thresholds\//)) {
      config.adapter = async () => ({
        data: { success: true },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }
    if (method === "POST" && url === "/api/admin/pep-list/import") {
      config.adapter = async () => ({
        data: { imported: 42, skipped: 3, message: "Import mock réussi" },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }
    if (method === "POST" && url === "/api/admin/pep-list") {
      config.adapter = async () => ({
        data: { id: `pep-${Date.now()}`, active: true },
        status: 201,
        statusText: "Created",
        headers: {},
        config,
      });
      return config;
    }
    if (method === "GET" && url === "/api/admin/audit-logs") {
      config.adapter = async () => ({
        data: { items: MOCK_AUDIT_LOGS, total: MOCK_AUDIT_LOGS.length },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      });
      return config;
    }

    return config;
  });

  console.log(
    "%c[RiskGuard] MODE MOCK ACTIVÉ — aucun backend requis",
    "color:#10B981;font-weight:bold;font-size:13px",
  );
  console.log(
    "%cComptes de test :\n  admin / admin1234 (admin)\n  agent01 / password123 (compliance_officer)",
    "color:#1E3A8A",
  );
}
