// src/services/alertService.js
import api from "./api";

export const alertService = {
  /**
   * GET /api/alerts?status=OPEN&risk_level=HIGH&skip=0&limit=25
   * Retourne { items: [...], total }
   */
  list: (params) => api.get("/api/alerts", { params }).then((r) => r.data),

  /**
   * PUT /api/alerts/{id}
   * Body : { status, action_taken, action_notes, sar_filed }
   */
  update: (id, body) => api.put(`/api/alerts/${id}`, body).then((r) => r.data),

  /**
   * POST /api/alerts
   * Body : { customer_id, alert_type, risk_level, description }
   */
  create: (body) => api.post("/api/alerts", body).then((r) => r.data),
};
