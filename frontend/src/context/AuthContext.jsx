// src/context/AuthContext.jsx
import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import { authService } from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // { id, role, login?, full_name? }
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Rehydratation depuis localStorage au montage
  useEffect(() => {
    try {
      const stored = localStorage.getItem("rg_session");
      if (stored) {
        const { user: u, token: t } = JSON.parse(stored);
        setUser(u);
        setToken(t);
      }
    } catch {
      localStorage.removeItem("rg_session");
    } finally {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async ({ login, password }) => {
    const data = await authService.login({ login, password });
    // data = { access_token, token_type, user_id, role }
    const sessionUser = { id: data.user_id, role: data.role, login };
    setUser(sessionUser);
    setToken(data.access_token);
    localStorage.setItem(
      "rg_session",
      JSON.stringify({
        user: sessionUser,
        token: data.access_token,
      }),
    );
    return data;
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    localStorage.removeItem("rg_session");
  }, []);

  // Helpers de rôle
  const isAdmin = user?.role === "admin";
  const isComplianceOfficer = user?.role === "compliance_officer" || isAdmin;

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        logout,
        isAdmin,
        isComplianceOfficer,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuthContext = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext must be inside AuthProvider");
  return ctx;
};

export { AuthContext };
