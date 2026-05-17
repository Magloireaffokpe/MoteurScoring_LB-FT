// src/hooks/useAuth.js
// Hook wrapper sur AuthContext — usage : const { user, login, logout } = useAuth()
import { useAuthContext } from "../context/AuthContext";
export function useAuth() {
  return useAuthContext();
}
