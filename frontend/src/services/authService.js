// src/services/authService.js
import api from "./api";

export const authService = {
  /** POST /auth/login → { access_token, token_type, user_id, role } */
  login: (credentials) =>
    api.post("/auth/login", credentials).then((r) => r.data),
  /** GET /auth/me → { id, login, full_name, email, role, is_active } */
  me: () => api.get("/auth/me").then((r) => r.data),
};
