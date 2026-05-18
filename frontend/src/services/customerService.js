// src/services/customerService.js
// Synchronisé avec les models SQLAlchemy et api_routes_backend.md
import api from "./api";
import { MOCK_COUNTRIES, MOCK_RISK_ZONES } from "../utils/constants";

export const customerService = {
  // ── Clients ───────────────────────────────────────────────────────────────

  /**
   * GET /api/clients?skip=0&limit=25&search=&kyc_level=&status=
   * Retourne { items: [...], total, skip, limit }
   */
  list: (params) => api.get("/api/clients", { params }).then((r) => r.data),

  /**
   * GET /api/clients/{customer_id}
   * Retourne le client complet avec accounts et documents
   */
  get: (id) => api.get(`/api/clients/${id}`).then((r) => r.data),

  /**
   * POST /api/clients
   * Body conforme au contrat API :
   * {
   *   first_name, last_name, date_of_birth, phone, email,
   *   nationality_id, profession_code, profession_name,
   *   profession_risk_category, monthly_income,
   *   city, region, zone_geo_classification, latitude, longitude
   * }
   * NB : le routeur backend (customers.py de Marcos) mappe vers les champs Customer :
   *   prenom, nom, date_naissance, phone, email,
   *   pays (FK int → countries.id), profession_code, profession_name,
   *   profession_risk ('LOW'|'MEDIUM'|'HIGH'), revenus_declares,
   *   city, region, zone_geo (FK int → risk_zones.id), latitude, longitude
   */
  create: (body) => api.post("/api/clients", body).then((r) => r.data),

  /**
   * PUT /api/clients/{customer_id}
   */
  update: (id, body) => api.put(`/api/clients/${id}`, body).then((r) => r.data),

  // ── Comptes bancaires (sous-ressource) ───────────────────────────────────

  /**
   * GET /api/customers/{customer_id}/accounts
   * Retourne { items: [{ id, client_id, type_compte, solde_moyen,
   *                       date_ouverture, status, created_at }], total }
   * Champs alignés avec CustomerAccount (customer_accounts.py) :
   *   type_compte : 'COURANT' | 'EPARGNE'
   *   status      : 'ACTIF' | 'BLOQUE'
   */
  getAccounts: (customerId, params) =>
    api
      .get(`/api/customers/${customerId}/accounts`, { params })
      .then((r) => r.data),

  /**
   * GET /api/accounts/{account_id}
   * Retourne le détail d'un compte avec ses transactions
   */
  getAccountById: (accountId) =>
    api.get(`/api/accounts/${accountId}`).then((r) => r.data),

  // ── Documents KYC (sous-ressource) ───────────────────────────────────────

  /**
   * GET /api/customers/{customer_id}/documents
   * Retourne { items: [{ id, client_id, type_doc, numero,
   *                       date_expiration, valide, created_at }], total }
   * Champs alignés avec CustomerDoc (customer_docs.py) :
   *   type_doc : 'CNI' | 'PASSEPORT' | ...
   *   valide   : boolean
   */
  getDocuments: (customerId, params) =>
    api
      .get(`/api/customers/${customerId}/documents`, { params })
      .then((r) => r.data),

  /**
   * GET /api/documents/{doc_id}
   * Retourne le détail d'un document KYC
   */
  getDocumentById: (docId) =>
    api.get(`/api/documents/${docId}`).then((r) => r.data),

  // ── Transactions (sous-ressource) ────────────────────────────────────────

  /**
   * GET /api/customers/{customer_id}/transactions?skip=0&limit=50&days=90
   * Retourne { items: [{ id, compte_id, montant, devise, type_op,
   *                       date_op, canal, origine, destination,
   *                       origine_pays_id, destination_pays_id }], total }
   * Champs alignés avec Transaction (transactions.py) :
   *   type_op : 'DEPOT' | 'RETRAIT' | 'VIREMENT' | 'PAIEMENT'
   *   canal   : 'MOBILE' | 'GUICHET' | 'INTERNET' | 'ATM'
   *   devise  : 'XOF' | 'USD' | 'EUR' ...
   */
  getTransactions: (customerId, params) =>
    api
      .get(`/api/customers/${customerId}/transactions`, { params })
      .then((r) => r.data),

  /**
   * GET /api/transactions/{transaction_id}
   * Retourne le détail d'une transaction
   */
  getTransactionById: (transactionId) =>
    api.get(`/api/transactions/${transactionId}`).then((r) => r.data),

  // ── Scores (sous-ressource) ───────────────────────────────────────────────

  /**
   * GET /api/customers/{customer_id}/scores?skip=0&limit=10
   * Retourne { items: [{ id, global_score, risk_category, is_current, scored_at }], total }
   * Champs alignés avec Score (scores.py) :
   *   global_score  : int 0-100  (score_global en DB)
   *   risk_category : 'FAIBLE' | 'MOYEN' | 'ÉLEVÉ'  (categorie en DB)
   *   is_current    : boolean
   *   scored_at     : datetime  (date_calcul en DB)
   */
  getScores: (id, params) =>
    api.get(`/api/customers/${id}/scores`, { params }).then((r) => r.data),

  // ── Alertes (sous-ressource) ──────────────────────────────────────────────

  /**
   * GET /api/customers/{customer_id}/alerts
   * Retourne { items: [...], total }
   * Champs Alert (alerts.py) : type_alerte, statut, sar_declare, date_creation
   *   type_alerte : 'SCORE_ELEVE' | 'KYC_INCOMPLET' | 'PEP_DETECTE'
   *   statut      : 'OPEN' | 'UNDER_REVIEW' | 'CLOSED'
   */
  getAlerts: (id, params) =>
    api.get(`/api/customers/${id}/alerts`, { params }).then((r) => r.data),
};

// ── Référentiels ────────────────────────────────────────────────────────────
/**
 * Service référentiels (pays, zones) avec fallback mock
 * si les endpoints /api/referentials/* ne sont pas encore implémentés.
 */
export const referentialService = {
  /**
   * GET /api/referentials/countries
   * Champs alignés avec Country (countries.py) :
   *   { id, code_iso, name, is_uemoa, is_border, is_fatf }
   * Fallback : MOCK_COUNTRIES (synchronisé avec seed_db.py de Marcos)
   */
  countries: () =>
    api
      .get("/api/referentials/countries")
      .then((r) => r.data)
      .catch(() => MOCK_COUNTRIES),

  /**
   * GET /api/referentials/risk-zones
   * Champs alignés avec RiskZone (risk_zones.py) :
   *   { id, name, risk_level, description }
   *   risk_level : 'FAIBLE' | 'MOYEN' | 'ELEVE' | 'TRES_ELEVE'
   * Fallback : MOCK_RISK_ZONES (synchronisé avec seed_db.py de Marcos)
   */
  riskZones: () =>
    api
      .get("/api/referentials/risk-zones")
      .then((r) => r.data)
      .catch(() => MOCK_RISK_ZONES),
};
