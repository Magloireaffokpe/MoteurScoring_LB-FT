// src/services/alertService.js
import api from "./api";

export const alertService = {
  /**
   * GET /api/alerts?status=OPEN&skip=0&limit=25
   * Retourne { items: [...], total }
   * Champs Alert (alerts.py) : type_alerte, statut, sar_declare, date_creation
   */
  list: (params, config = {}) => api.get("/api/alerts", { params, ...config }).then((r) => r.data),

  /**
   * GET /api/alerts/{alert_id}
   * Retourne le détail complet d'une alerte
   */
  getById: (id) => api.get(`/api/alerts/${id}`).then((r) => r.data),

  /**
   * PUT /api/alerts/{alert_id}
   * Body : { statut, decision, sar_declare }
   * Champs alignés avec Alert (alerts.py) :
   *   statut     : 'OPEN' | 'UNDER_REVIEW' | 'CLOSED'
   *   decision   : texte libre (motif de clôture)
   *   sar_declare: boolean (SAR déclarée à la CENTIF)
   */
  update: (id, body) => api.put(`/api/alerts/${id}`, body).then((r) => r.data),

  /**
   * POST /api/alerts
   * Body aligné avec Alert (alerts.py) :
   *   { client_id, type_alerte, description }
   *   type_alerte : 'SCORE_ELEVE' | 'KYC_INCOMPLET' | 'PEP_DETECTE'
   *   NB : le model a client_id (pas customer_id), type_alerte (pas alert_type),
   *        statut (pas status) — pas de champ risk_level dans le model
   */
  create: (body) => api.post("/api/alerts", body).then((r) => r.data),

  /**
   * GET /api/alerts/groupements/beneficiaire
   * Liste des bénéficiaires suspects groupés
   */
  listGroupements: () =>
    api.get("/api/alerts/groupements/beneficiaire").then((r) => r.data),

  /**
   * GET /api/alerts/groupements/beneficiaire/{nom}
   * Détail d'un groupement : alertes pour ce bénéficiaire
   */
  getGroupementDetail: (nom) =>
    api.get(`/api/alerts/groupements/beneficiaire/${encodeURIComponent(nom)}`).then((r) => r.data),
};
