// src/services/adminService.js
// NB : ce fichier n'était pas dans la structure initiale — ajouté car requis par AdminPage
import api from "./api";

export const adminService = {
  // ── Critères de scoring ──────────────────────────────────────────────────
  /** GET /api/admin/scoring-criteria → { items: [{id, code, name, weight, description}] } */
  getCriteria: () => api.get("/api/admin/scoring-criteria").then((r) => r.data),

  /** PUT /api/admin/scoring-criteria/{id} — Body : { weight: number } */
  updateCriteria: (id, body) =>
    api.put(`/api/admin/scoring-criteria/${id}`, body).then((r) => r.data),

  // ── Seuils de risque ─────────────────────────────────────────────────────
  /** GET /api/admin/risk-thresholds → { items: [{id, category, score_min, score_max, required_action}] } */
  getThresholds: () =>
    api.get("/api/admin/risk-thresholds").then((r) => r.data),

  /** PUT /api/admin/risk-thresholds/{id} */
  updateThreshold: (id, body) =>
    api.put(`/api/admin/risk-thresholds/${id}`, body).then((r) => r.data),

  // ── Gestion PEP ───────────────────────────────────────────────────────────
  /**
   * POST /api/admin/pep-list/import
   * Body : FormData avec fichier CSV
   * Retourne : { imported: number, skipped: number, message: string }
   */
  importPep: (formData) =>
    api
      .post("/api/admin/pep-list/import", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data),

  /**
   * POST /api/admin/pep-list
   * Body : { nom, prenom, fonction, pays (int FK), source, date_debut, date_fin, active }
   * Champs synchronisés avec PepEntry SQLAlchemy (pep_list.py de Marcos)
   */
  addPep: (body) => api.post("/api/admin/pep-list", body).then((r) => r.data),

  // ── Utilisateurs ──────────────────────────────────────────────────────────
  /** GET /api/admin/users → liste des utilisateurs */
  getUsers: () => api.get("/api/admin/users").then((r) => r.data),

  /** PUT /api/admin/users/{id} */
  updateUser: (id, body) =>
    api.put(`/api/admin/users/${id}`, body).then((r) => r.data),

  // ── Audit logs ────────────────────────────────────────────────────────────
  /**
   * GET /api/admin/audit-logs?user_id=&action=&skip=0&limit=50
   * Retourne { items: [{id, user_id, action, resource_type, resource_id, timestamp, ip_address}], total }
   */
  getAuditLogs: (params) =>
    api.get("/api/admin/audit-logs", { params }).then((r) => r.data),
};
