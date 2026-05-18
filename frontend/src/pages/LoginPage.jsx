// src/pages/LoginPage.jsx
import { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { Eye, EyeOff, Lock, User } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { Button } from "../components/Button";
import { validateLoginForm } from "../utils/validators";
import toast from "react-hot-toast";
import { clsx } from "clsx";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/dashboard";

  const [form, setForm] = useState({ login: "", password: "" });
  const [errors, setErrors] = useState({});
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
    if (errors[name]) setErrors((er) => ({ ...er, [name]: "" }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = validateLoginForm(form);
    if (Object.keys(errs).length) {
      setErrors(errs);
      return;
    }

    setLoading(true);
    try {
      await login({ login: form.login.trim(), password: form.password });
      toast.success("Connexion réussie");
      navigate(from, { replace: true });
    } catch (err) {
      if (err.response?.status === 401) {
        setErrors({ password: "Identifiant ou mot de passe incorrect" });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* ── Panneau gauche — branding ── */}
      <div
        className="hidden lg:flex lg:w-1/2 flex-col items-center justify-center p-12 relative overflow-hidden"
        style={{
          background:
            "linear-gradient(155deg, #1B2A6B 0%, #1E3A8A 55%, #2D4FA8 100%)",
        }}
      >
        {/* Décorations de fond */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2 pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-[#10B981]/10 rounded-full translate-y-1/3 -translate-x-1/3 pointer-events-none" />

        <div className="relative z-10 text-center max-w-sm">
          {/* Logo PNG */}
          <div className="flex items-center justify-center mb-10">
            <Link
              to="/"
              className="transition-transform duration-200 hover:scale-105 active:scale-95 block"
            >
              <img
                src="/logo.png"
                alt="RiskGuard"
                className="w-80 h-auto object-contain"
                style={{ mixBlendMode: "screen" }}
              />
            </Link>
          </div>

          <p className="text-white/65 text-[15px] leading-relaxed mb-8">
            Plateforme de scoring LBC/FT pour institutions de microfinance
            béninoises. Conformité{" "}
            <strong className="text-white/90">GIABA · FATF · CENTIF</strong>.
          </p>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { v: "500+", l: "Clients scorés" },
              { v: "6", l: "Critères" },
              { v: "100%", l: "CENTIF" },
            ].map(({ v, l }) => (
              <div
                key={l}
                className="bg-white/10 rounded-xl py-3 px-2 text-center"
              >
                <p className="text-white font-extrabold text-xl font-display">
                  {v}
                </p>
                <p className="text-white/45 text-[11px] mt-0.5">{l}</p>
              </div>
            ))}
          </div>

          {/* Subtag */}
          <p className="text-white/30 text-[11px] mt-8 tracking-wider uppercase">
            Protéger · Contrôler · Conformer
          </p>
        </div>
      </div>

      {/* ── Panneau droit — formulaire ── */}
      <div className="w-full lg:w-1/2 flex items-center justify-center bg-[#F9FAFB] p-6">
        <div className="w-full max-w-sm">
          {/* Logo mobile */}
          <div className="lg:hidden flex items-center justify-center mb-8">
            <Link to="/">
              <img
                src="/logo.png"
                alt="RiskGuard"
                className="w-56 h-auto object-contain"
              />
            </Link>
          </div>

          {/* Card formulaire */}
          <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-lg p-7">
            <div className="text-center mb-6">
              <div className="w-12 h-12 bg-[#EEF2FF] rounded-xl flex items-center justify-center mx-auto mb-3">
                <Lock className="w-5 h-5 text-[#1E3A8A]" />
              </div>
              <h2 className="font-display font-bold text-2xl text-[#111827]">
                Connexion
              </h2>
              <p className="text-sm font-normal font-sans text-[#4B5563] mt-1">
                Accès réservé aux agents autorisés
              </p>
            </div>

            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              {/* Login */}
              <div>
                <label className="text-sm font-medium text-[#374151] font-sans block mb-1.5">
                  Nom d&apos;utilisateur
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9CA3AF]" />
                  <input
                    name="login"
                    type="text"
                    autoComplete="username"
                    autoFocus
                    placeholder="agent_01"
                    value={form.login}
                    onChange={handleChange}
                    className={clsx(
                      "w-full pl-9 pr-3 py-2.5 rounded-xl border text-sm bg-white",
                      "text-[#111827] placeholder-[#9CA3AF]",
                      "focus:outline-none focus:ring-2 transition-all duration-200",
                      errors.login
                        ? "border-[#EF4444] focus:ring-[#EF4444]/30"
                        : "border-[#E5E7EB] focus:ring-[#1E3A8A]/30 focus:border-[#1E3A8A]",
                    )}
                  />
                </div>
                {errors.login && (
                  <p className="text-xs text-[#EF4444] mt-1">{errors.login}</p>
                )}
              </div>

              {/* Password */}
              <div>
                <label className="text-sm font-medium text-[#374151] font-sans block mb-1.5">
                  Mot de passe
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9CA3AF]" />
                  <input
                    name="password"
                    type={showPwd ? "text" : "password"}
                    autoComplete="current-password"
                    placeholder="••••••••"
                    value={form.password}
                    onChange={handleChange}
                    className={clsx(
                      "w-full pl-9 pr-10 py-2.5 rounded-xl border text-sm bg-white",
                      "text-[#111827] placeholder-[#9CA3AF]",
                      "focus:outline-none focus:ring-2 transition-all duration-200",
                      errors.password
                        ? "border-[#EF4444] focus:ring-[#EF4444]/30"
                        : "border-[#E5E7EB] focus:ring-[#1E3A8A]/30 focus:border-[#1E3A8A]",
                    )}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPwd((s) => !s)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]
                               hover:text-[#6B7280] transition-colors"
                    aria-label={showPwd ? "Masquer" : "Afficher"}
                  >
                    {showPwd ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
                {errors.password && (
                  <p className="text-xs text-[#EF4444] mt-1">
                    {errors.password}
                  </p>
                )}
              </div>

              <Button
                type="submit"
                loading={loading}
                fullWidth
                size="lg"
                className="mt-2"
              >
                Se connecter
              </Button>
            </form>

            <p className="text-center text-xs font-normal font-sans text-[#9CA3AF] mt-5 pt-4 border-t border-[#F3F4F6]">
              Microfinance Béninoise SA — Système LBC/FT v1.2
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
