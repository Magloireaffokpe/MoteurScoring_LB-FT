// src/services/adminService.js
import api from "./api";

export const adminService = {
  // ── Critères de scoring ──────────────────────────────────────────────────
  /**
   * GET /api/admin/scoring-criteria
   * Retourne { items: [{ id, code, name, weight, description }] }
   * Champs alignés avec ScoringCriteria (scoring_criteria.py) :
   *   weight : valeur entière en % (ex. 20, 25…)
   */
  getCriteria: () => api.get("/api/admin/scoring-criteria").then((r) => r.data),

  /**
   * PUT /api/admin/scoring-criteria/{criteria_id}
   * Body : { weight: number }
   */
  updateCriteria: (id, body) =>
    api.put(`/api/admin/scoring-criteria/${id}`, body).then((r) => r.data),

  // ── Seuils de risque ─────────────────────────────────────────────────────
  /**
   * GET /api/admin/risk-thresholds
   * Retourne { items: [{ id, category, score_min, score_max, action }] }
   * Champs alignés avec RiskThreshold (risk_thresholds.py) :
   *   score_min / score_max / action  (pas min_score / max_score / required_action)
   *   category : 'FAIBLE' | 'MOYEN' | 'ELEVE'
   */
  getThresholds: () =>
    api.get("/api/admin/risk-thresholds").then((r) => r.data),

  /**
   * PUT /api/admin/risk-thresholds/{id}
   * Body : { score_min, score_max, action }
   * NB : route non listée dans api_routes_backend.md — à confirmer avec Marcos
   */
  updateThreshold: (id, body) =>
    api.put(`/api/admin/risk-thresholds/${id}`, body).then((r) => r.data),

  // ── Gestion PEP ───────────────────────────────────────────────────────────
  /**
   * POST /api/admin/pep-list/import
   * Body : FormData avec fichier CSV
   * Retourne : { message: string }
   */
  importPep: (formData) =>
    api
      .post("/api/admin/pep-list/import", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data),

  /**
   * POST /api/admin/pep-list
   * Body aligné avec le routeur backend :
   *   { nom, prenom, fonction, pays, source, date_debut, date_fin }
   */
  addPep: (body) => api.post("/api/admin/pep-list", body).then((r) => r.data),

  // ── Utilisateurs ──────────────────────────────────────────────────────────
  /**
   * GET /api/admin/users
   * Retourne liste des utilisateurs
   */
  getUsers: () => api.get("/api/admin/users").then((r) => r.data),

  /**
   * POST /api/admin/users
   * Body : { login, password, role_name }
   * Champs alignés avec le routeur backend :
   *   role_name doit être 'admin' ou 'compliance_officer'
   */
  createUser: (body) => api.post("/api/admin/users", body).then((r) => r.data),

  /**
   * PUT /api/admin/users/{user_id}/reset-password
   * Body : { new_password: string }
   */
  resetUserPassword: (id, newPassword) =>
    api
      .put(`/api/admin/users/${id}/reset-password`, { new_password: newPassword })
      .then((r) => r.data),

  /**
   * PUT /api/admin/users/{user_id}/toggle-active
   * Active ou désactive un compte utilisateur
   */
  toggleUserActive: (id) =>
    api.put(`/api/admin/users/${id}/toggle-active`).then((r) => r.data),

  // ── Audit logs ────────────────────────────────────────────────────────────
  /**
   * GET /api/admin/audit-logs?user_id=&action=&skip=0&limit=50
   * Champs alignés avec AuditLog (audit_logs.py) :
   *   Retourne { items: [{ id, user_id, client_id, action, timestamp, ip_address }], total }
   *   NB : le model a client_id (pas resource_id / resource_type)
   */
  getAuditLogs: (params) =>
    api.get("/api/admin/audit-logs", { params }).then((r) => r.data),

  // ── Référentiels (Pays & Zones) ───────────────────────────────────────────
  /**
   * POST /api/countries
   * Body : { code_iso, name, is_uemoa?, is_border?, is_fatf? }
   * Champs alignés avec Country (countries.py)
   */
  createCountry: (body) =>
    api.post("/api/countries", body).then((r) => r.data),

  /**
   * POST /api/risk-zones
   * Body : { name, risk_level, description? }
   * Champs alignés avec RiskZone (risk_zones.py)
   */
  createRiskZone: (body) =>
    api.post("/api/risk-zones", body).then((r) => r.data),
};
