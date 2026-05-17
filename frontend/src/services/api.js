// src/services/api.js
import axios from "axios";
import toast from "react-hot-toast";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// ── Injecte le JWT automatiquement dans chaque requête ────────────────────
api.interceptors.request.use((config) => {
  try {
    const stored = localStorage.getItem("rg_session");
    if (stored) {
      const { token } = JSON.parse(stored);
      if (token) config.headers.Authorization = `Bearer ${token}`;
    }
  } catch {
    /* silently ignore */
  }
  return config;
});

// ── Gestion globale des erreurs HTTP ──────────────────────────────────────
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    const detail = err.response?.data?.detail;

    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || d.message).join(", ")
          : err.message || "Erreur réseau";

    if (status === 401) {
      localStorage.removeItem("rg_session");
      window.location.href = "/login";
      toast.error("Session expirée, veuillez vous reconnecter.");
    } else if (status === 403) {
      toast.error("Accès refusé — droits insuffisants.");
    } else if (status === 422) {
      toast.error(`Validation : ${message}`);
    } else if (status >= 500) {
      toast.error("Erreur serveur. Réessayez dans quelques instants.");
    }
    // 404 est géré localement dans chaque composant

    return Promise.reject(err);
  },
);

export default api;
