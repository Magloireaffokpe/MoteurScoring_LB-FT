// src/context/AuthContext.jsx
import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import { authService } from "../services/authService";
import { setAuthToken, clearAuthToken } from "../services/api";

const AuthContext = createContext(null);

const STORAGE_KEY = "riskguard_token";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  const restoreFromStorage = useCallback(async () => {
    const savedToken = localStorage.getItem(STORAGE_KEY);
    if (!savedToken) {
      setLoading(false);
      return;
    }
    setAuthToken(savedToken);
    try {
      const data = await authService.me();
      setUser({ id: data.id, role: data.role, login: data.login });
      setToken(savedToken);
    } catch {
      localStorage.removeItem(STORAGE_KEY);
      clearAuthToken();
      setUser(null);
      setToken(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    restoreFromStorage();
  }, [restoreFromStorage]);

  const login = useCallback(async ({ login, password }) => {
    const data = await authService.login({ login, password });
    const sessionUser = { id: data.user_id, role: data.role, login };
    localStorage.setItem(STORAGE_KEY, data.access_token);
    setAuthToken(data.access_token);
    setUser(sessionUser);
    setToken(data.access_token);
    return data;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    clearAuthToken();
    setUser(null);
    setToken(null);
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
