// src/services/scoringService.js
import api from "./api";

export const scoringService = {
  /**
   * POST /api/scoring
   * Body : { customer_id: "uuid" }
   * Retourne : { id, customer_id, global_score, risk_category, detail_json,
   *              is_current, scored_by, scored_at }
   */
  score: (customer_id) =>
    api.post("/api/scoring", { customer_id }).then((r) => r.data),

  /**
   * POST /api/scoring/rescore
   * Même format que score()
   */
  rescore: (customer_id) =>
    api.post("/api/scoring/rescore", { customer_id }).then((r) => r.data),

  /**
   * GET /api/scores/{score_id}
   */
  getById: (score_id) => api.get(`/api/scores/${score_id}`).then((r) => r.data),

  /**
   * POST /api/scoring/rescore-all
   */
  rescoreAll: () => api.post("/api/scoring/rescore-all").then((r) => r.data),
};
