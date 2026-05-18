// src/App.jsx
import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import { Loader } from "./components/Loader";

/* ── Lazy loading de toutes les pages ─────────────────────────────── */
const LoginPage = lazy(() => import("./pages/LoginPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const ClientsListPage = lazy(() => import("./pages/ClientsListPage"));
const ClientDetailPage = lazy(() => import("./pages/ClientDetailPage"));
const AddClientPage = lazy(() => import("./pages/AddClientPage"));
const AlertsPage = lazy(() => import("./pages/AlertsPage"));
const ExportsPage = lazy(() => import("./pages/ExportsPage"));
const ScorePage = lazy(() => import("./pages/ScorePage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));

/* ── ProtectedRoute inline ────────────────────────────────────────── */
function ProtectedRoute({ children, adminOnly = false }) {
  const { user, loading } = useAuth();

  if (loading) return <Loader full text="Vérification de la session…" />;

  if (!user) return <Navigate to="/login" replace />;

  if (adminOnly && user.role !== "admin") {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

const PageLoader = () => <Loader full text="Chargement de la page…" />;

export default function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        {/* ── Public ── */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* ── Protégées : compliance_officer + admin ── */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/clients"
          element={
            <ProtectedRoute>
              <ClientsListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/clients/new"
          element={
            <ProtectedRoute>
              <AddClientPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/clients/:id"
          element={
            <ProtectedRoute>
              <ClientDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/alerts"
          element={
            <ProtectedRoute>
              <AlertsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/exports"
          element={
            <ProtectedRoute>
              <ExportsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/score/:scoreId"
          element={
            <ProtectedRoute>
              <ScorePage />
            </ProtectedRoute>
          }
        />

        {/* ── Protégée : admin seulement ── */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute adminOnly>
              <AdminPage />
            </ProtectedRoute>
          }
        />

        {/* ── Fallback ── */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}
