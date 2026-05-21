// src/components/Layout.jsx
import { useState, useEffect, useRef, useCallback } from "react";
import { NavLink, useNavigate, Link } from "react-router-dom";
import { clsx } from "clsx";
import {
  LayoutDashboard,
  Users,
  Bell,
  Download,
  Settings,
  LogOut,
  Shield,
  Menu,
  X,
  ChevronRight,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { useAppContext } from "../context/AppContext";
import { getInitials, formatDatetime } from "../utils/formatters";
import { alertService } from "../services/alertService";

const NAV_ITEMS = [
  {
    to: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    roles: ["admin", "compliance_officer"],
  },
  {
    to: "/clients",
    label: "Clients",
    icon: Users,
    roles: ["admin", "compliance_officer"],
  },
  {
    to: "/alerts",
    label: "Alertes",
    icon: Bell,
    roles: ["admin", "compliance_officer"],
  },
  {
    to: "/exports",
    label: "Exports",
    icon: Download,
    roles: ["admin", "compliance_officer"],
  },
  { to: "/admin", label: "Administration", icon: Settings, roles: ["admin"] },
];
function LogoMark() {
  return (
    <div className="px-5 py-6 mb-1 flex justify-center">
      <Link
        to="/dashboard"
        className="block transition-transform duration-200 hover:scale-[1.02] active:scale-[0.98]"
      >
        <img
          src="/logo.png"
          alt="RiskGuard"
          className="w-44 h-auto object-contain mx-auto"
          style={{ mixBlendMode: "screen" }}
        />
      </Link>
    </div>
  );
}

/* ── Sidebar content ──────────────────────────────────────────────── */
function SidebarContent({ onLinkClick }) {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const visibleNav = NAV_ITEMS.filter((item) =>
    item.roles.includes(user?.role),
  );

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="flex flex-col h-full">
      <LogoMark />
      <div className="h-px bg-white/10 mx-4 mb-4" />

      {/* Navigation */}
      <nav className="flex-1 px-3 space-y-0.5 overflow-y-auto">
        {visibleNav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onLinkClick}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3.5 px-3 py-3 rounded-xl text-sm font-medium font-sans",
                "transition-all duration-150 group",
                isActive
                  ? "bg-white/15 text-white border-l-[3px] border-[#10B981] pl-[9px]"
                  : "text-white/80 hover:text-white hover:bg-white/10",
              )
            }
          >
            <Icon className="w-5 h-5 flex-shrink-0" />
            <span className="flex-1">{label}</span>
            <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-60 transition-opacity" />
          </NavLink>
        ))}
      </nav>

      {/* User block */}
      <div className="px-3 pb-4 pt-3 border-t border-white/10 mt-2 space-y-1">
        <div className="flex items-center gap-3 px-3 py-2 rounded-xl">
          <div className="w-8 h-8 rounded-full bg-[#10B981] flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            {getInitials(user?.login || user?.full_name || "U")}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-white text-xs font-semibold truncate">
              {user?.full_name || user?.login || "Utilisateur"}
            </p>
            <p className="text-white/40 text-[10px] capitalize truncate">
              {user?.role?.replace("_", " ")}
            </p>
          </div>
          {isAdmin && (
            <Shield className="w-3 h-3 text-[#10B981] flex-shrink-0" />
          )}
        </div>

        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium
                     text-red-300 hover:text-red-200 hover:bg-red-500/20 transition-all duration-150"
        >
          <LogOut className="w-4 h-4" />
          Déconnexion
        </button>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────
   Composant Cloche de Notifications
───────────────────────────────────────────────────────────────────── */
function NotificationBell() {
  const [alerts, setAlerts] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  const fetchHighRiskAlerts = useCallback(() => {
    if (!alertService || typeof alertService.list !== "function") {
      return;
    }
    const promise = alertService.list({ limit: 50, statut: "OPEN" }, { silent: true });
    if (!promise || typeof promise.then !== "function") {
      return;
    }
    promise
      .then((d) => {
        const items = d?.items || d || [];
        const highRisk = items.filter(
          (a) => a.type_alerte === "SCORE_ELEVE" || a.type_alerte === "PEP_DETECTE",
        );
        setAlerts(highRisk);
      })
      .catch((err) => {
        console.error("Erreur de récupération des alertes pour la cloche", err);
      });
  }, []);

  useEffect(() => {
    fetchHighRiskAlerts();
    const interval = setInterval(fetchHighRiskAlerts, 15000);
    return () => clearInterval(interval);
  }, [fetchHighRiskAlerts]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleAlertClick = (alert) => {
    setIsOpen(false);
    navigate(`/clients/${alert.client_id}`);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-1.5 rounded-lg text-[#6B7280] hover:text-[#1E3A8A] hover:bg-[#F3F4F6] transition-colors focus:outline-none"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5" />
        {alerts.length > 0 && (
          <span className="absolute top-0 right-0 transform translate-x-1/3 -translate-y-1/3 flex h-5 w-5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-5 w-5 bg-[#EF4444] text-[10px] font-bold text-white items-center justify-center">
              {alerts.length}
            </span>
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2.5 w-80 bg-white rounded-xl border border-[#E5E7EB] shadow-xl z-50 overflow-hidden py-1">
          <div className="px-4 py-2.5 bg-[#F9FAFB] border-b border-[#E5E7EB] flex items-center justify-between">
            <span className="text-xs font-bold text-[#1E3A8A] font-sans">
              ALERTES RISQUE CRITIQUE
            </span>
            <span className="bg-[#FEF2F2] text-[#EF4444] text-[10px] font-bold px-2 py-0.5 rounded-full">
              {alerts.length} en cours
            </span>
          </div>

          <div className="max-h-64 overflow-y-auto divide-y divide-[#F3F4F6]">
            {alerts.length > 0 ? (
              alerts.map((a) => (
                <button
                  key={a.id}
                  onClick={() => handleAlertClick(a)}
                  className="w-full text-left px-4 py-3 hover:bg-[#F9FAFB] transition-all flex flex-col gap-1 focus:outline-none"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-bold text-[#111827] font-sans truncate">
                      {a.customer_name || `Client ${a.client_id?.slice(0, 8)}...`}
                    </span>
                    <span className="bg-[#FEF2F2] text-[#EF4444] text-[9px] font-bold px-1.5 py-0.5 rounded">
                      ÉLEVÉ
                    </span>
                  </div>
                  <p className="text-[11px] text-[#6B7280] font-sans leading-relaxed">
                    {a.description || "Un score de risque élevé a été calculé pour ce client."}
                  </p>
                  <span className="text-[10px] text-[#9CA3AF] font-sans">
                    {formatDatetime(a.date_creation)}
                  </span>
                </button>
              ))
            ) : (
              <div className="py-8 px-4 text-center text-[#9CA3AF] text-xs font-sans">
                Aucune alerte de risque critique en cours.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Layout principal ─────────────────────────────────────────────── */
/**
 * @param {string}    pageTitle - Titre affiché dans le header
 * @param {ReactNode} children  - Contenu de la page
 */
export function Layout({ pageTitle, children }) {
  const { sidebarOpen, toggleSidebar, closeSidebar } = useAppContext();
  const { user, isAdmin } = useAuth();

  return (
    <div className="min-h-screen flex bg-[#F9FAFB]">
      {/* ── Sidebar desktop ── */}
      <aside
        className="hidden lg:flex flex-col w-[260px] flex-shrink-0 fixed inset-y-0 left-0 z-30"
        style={{
          background:
            "linear-gradient(160deg, #1B2A6B 0%, #1E3A8A 60%, #2D4FA8 100%)",
        }}
      >
        <SidebarContent onLinkClick={() => {}} />
      </aside>

      {/* ── Sidebar mobile (overlay) ── */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-40 flex">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={closeSidebar}
            aria-hidden="true"
          />
          <aside
            className="relative w-[260px] flex flex-col z-50"
            style={{
              background:
                "linear-gradient(160deg, #1B2A6B 0%, #1E3A8A 60%, #2D4FA8 100%)",
            }}
          >
            <SidebarContent onLinkClick={closeSidebar} />
          </aside>
        </div>
      )}

      {/* ── Main area ── */}
      <div className="flex-1 min-w-0 lg:ml-[260px] flex flex-col min-h-screen">
        {/* Header */}
        <header className="sticky top-0 z-20 bg-white border-b border-[#E5E7EB] h-14 flex items-center gap-4 px-4 lg:px-8 shadow-sm">
          {/* Burger mobile */}
          <button
            className="lg:hidden p-1.5 rounded-lg hover:bg-[#F3F4F6] transition-colors"
            onClick={toggleSidebar}
            aria-label="Menu"
          >
            {sidebarOpen ? (
              <X className="w-5 h-5" />
            ) : (
              <Menu className="w-5 h-5" />
            )}
          </button>

          {/* Page title */}
          <h1 className="flex-1 min-w-0 truncate font-display font-bold text-2xl text-[#111827]">
            {pageTitle}
          </h1>

          {/* Right */}
          <div className="flex items-center gap-3">
            {isAdmin && (
              <span
                className="hidden sm:flex items-center gap-1 px-2 py-0.5 rounded-full
                               bg-[#EEF2FF] text-[#1E3A8A] text-[10px] font-semibold"
              >
                <Shield className="w-3 h-3" /> Admin
              </span>
            )}
            <NotificationBell />
            <div
              className="w-8 h-8 rounded-full bg-[#1E3A8A] flex items-center justify-center
                            text-white text-xs font-bold flex-shrink-0"
            >
              {getInitials(user?.login || "U")}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
