// src/services/dashboardService.js
import api from "./api";

export const dashboardService = {
  /** GET /api/dashboard/stats */
  stats: () => api.get("/api/dashboard/stats").then((r) => r.data),

  /** GET /api/dashboard/alerts → 5 dernières alertes ouvertes */
  recentAlerts: () => api.get("/api/dashboard/alerts").then((r) => r.data),

  /** GET /api/dashboard/pep → clients marqués PEP */
  pepClients: () => api.get("/api/dashboard/pep").then((r) => r.data),
};
