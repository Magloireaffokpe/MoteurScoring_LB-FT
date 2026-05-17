// src/services/customerService.js
// Synchronisé avec app/models/customers.py et API_CONTRACT_v1.0
import api from "./api";
import { MOCK_COUNTRIES, MOCK_RISK_ZONES } from "../utils/constants";

export const customerService = {
  /**
   * GET /api/clients?skip=0&limit=25&search=&kyc_level=&status=
   * Retourne { items: [...], total, skip, limit }
   */
  list: (params) => api.get("/api/clients", { params }).then((r) => r.data),

  /**
   * GET /api/clients/{id}
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
   * NB : les champs du modèle Customer (backend) sont :
   *   prenom, nom, date_naissance, phone, email,
   *   pays (FK id), profession_code, profession_name, profession_risk,
   *   revenus_declares, city, region, zone_geo (FK id)
   * Le mapping est fait par le backend (routeur customers de Marcos)
   */
  create: (body) => api.post("/api/clients", body).then((r) => r.data),

  /**
   * PUT /api/clients/{id}
   */
  update: (id, body) => api.put(`/api/clients/${id}`, body).then((r) => r.data),

  /**
   * GET /api/customers/{id}/scores?skip=0&limit=10
   * Retourne { items: [{ id, global_score, risk_category, is_current, scored_at }], total }
   */
  getScores: (id, params) =>
    api.get(`/api/customers/${id}/scores`, { params }).then((r) => r.data),

  /**
   * GET /api/customers/{id}/alerts
   * Retourne { items: [...], total }
   */
  getAlerts: (id, params) =>
    api.get(`/api/customers/${id}/alerts`, { params }).then((r) => r.data),
};

/**
 * Service référentiels (pays, zones) avec fallback mock
 * si les endpoints /api/referentials/* ne sont pas encore implémentés par Marcos
 */
export const referentialService = {
  /**
   * GET /api/referentials/countries
   * Retourne liste de { id, code_iso, name, is_uemoa, is_border, is_fatf }
   * Fallback : MOCK_COUNTRIES de constants.js (synchronisé avec seed_db.py)
   */
  countries: () =>
    api
      .get("/api/referentials/countries")
      .then((r) => r.data)
      .catch(() => MOCK_COUNTRIES),

  /**
   * GET /api/referentials/risk-zones
   * Retourne liste de { id, name, risk_level, description }
   * Fallback : MOCK_RISK_ZONES de constants.js (synchronisé avec seed_db.py)
   */
  riskZones: () =>
    api
      .get("/api/referentials/risk-zones")
      .then((r) => r.data)
      .catch(() => MOCK_RISK_ZONES),
};
