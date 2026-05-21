// src/services/api.js
import axios from "axios";
import toast from "react-hot-toast";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
  withCredentials: true,
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

    if (err.config?.silent) {
      return Promise.reject(err);
    }

    if (!status) {
      toast.error("Erreur de connexion au serveur. Vérifiez votre réseau.");
    } else if (status === 401) {
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
        toast.error("Session expirée, veuillez vous reconnecter.");
      }
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
