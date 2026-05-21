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
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Vérifie si une session existe via le cookie httpOnly
  useEffect(() => {
    authService
      .me()
      .then((data) => {
        setUser({ id: data.id, role: data.role, login: data.login });
      })
      .catch(() => {
        setUser(null);
        setToken(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async ({ login, password }) => {
    const data = await authService.login({ login, password });
    const sessionUser = { id: data.user_id, role: data.role, login };
    setUser(sessionUser);
    setToken(data.access_token);
    return data;
  }, []);

  const logout = useCallback(() => {
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
