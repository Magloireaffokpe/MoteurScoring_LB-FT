// src/components/Layout.jsx
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
import { getInitials } from "../utils/formatters";

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
