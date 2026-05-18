// src/pages/DashboardPage.jsx
import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Users,
  AlertTriangle,
  TrendingUp,
  RefreshCw,
  Plus,
  ArrowRight,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";

import { Layout } from "../components/Layout";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Loader } from "../components/Loader";
import { Badge } from "../components/Badge";
import { Table } from "../components/Table";

import { dashboardService } from "../services/dashboardService";
import { scoringService } from "../services/scoringService";
import { useFetch } from "../hooks/useFetch";

import {
  formatDatetime,
  formatAmount,
  normalizeCategory,
} from "../utils/formatters";
import { MOCK_DASHBOARD_STATS } from "../utils/constants";

import toast from "react-hot-toast";
import { clsx } from "clsx";

/* ── Couleurs catégories ────────────────────────────────────────────── */
const PIE_COLORS = {
  FAIBLE: "#10B981",
  MOYEN: "#F59E0B",
  ÉLEVÉ: "#EF4444",
  ELEVE: "#EF4444",
};

/* ── Tooltip personnalisé ─────────────────────────────────────────── */
function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { name, value } = payload[0];
  return (
    <div className="bg-white border border-[#E5E7EB] rounded-xl px-3 py-2 shadow-lg text-xs font-medium">
      {name} : <span className="font-bold">{value}</span>
    </div>
  );
}

/* ── Carte KPI ───────────────────────────────────────────────────── */
function KpiCard({ label, value, icon: Icon, color, sub }) {
  const styles = {
    primary: { bg: "bg-[#EEF2FF]", text: "text-[#1E3A8A]" },
    secondary: { bg: "bg-[#ECFDF5]", text: "text-[#10B981]" },
    danger: { bg: "bg-[#FEF2F2]", text: "text-[#EF4444]" },
    accent: { bg: "bg-[#FFFBEB]", text: "text-[#F59E0B]" },
  }[color] || { bg: "bg-[#EEF2FF]", text: "text-[#1E3A8A]" };

  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] shadow-sm p-5 flex items-start gap-4">
      <div
        className={clsx("p-3 rounded-xl flex-shrink-0", styles.bg, styles.text)}
      >
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <p className="text-[13px] font-medium font-sans text-[#6B7280] uppercase tracking-wider">
          {label}
        </p>
        <p className="text-3xl font-bold font-display text-[#1E3A8A] mt-0.5">
          {value ?? "—"}
        </p>
        {sub && (
          <p className="text-xs font-normal font-sans text-[#9CA3AF] mt-0.5 truncate">
            {sub}
          </p>
        )}
      </div>
    </div>
  );
}

/* ── Colonnes tableau alertes ────────────────────────────────────── */
const ALERT_COLS = (navigate) => [
  {
    key: "customer_name",
    label: "Client",
    render: (v, r) => (
      <span className="text-sm font-normal text-[#111827] font-sans">
        {v || r.client_id?.slice(0, 12) + "…"}
      </span>
    ),
  },
  {
    key: "type_alerte",
    label: "Type",
    render: (v) => (
      <span className="font-mono text-[11px] font-medium bg-[#F3F4F6] text-[#374151] px-2 py-0.5 rounded">
        {v}
      </span>
    ),
  },
  { key: "date_creation", label: "Date", render: (v) => formatDatetime(v) },
  {
    key: "statut",
    label: "Statut",
    render: (v) => (
      <Badge type={v}>
        {v === "OPEN" ? "Ouvert" : v === "UNDER_REVIEW" ? "En cours" : "Fermé"}
      </Badge>
    ),
  },
  {
    key: "niveau",
    label: "Niveau",
    render: (_, r) => {
      const cat =
        r.type_alerte === "SCORE_ELEVE" ? "ÉLEVÉ" : r.type_alerte === "PEP_DETECTE" ? "ÉLEVÉ" : "MOYEN";
      return <Badge type={cat}>{cat}</Badge>;
    },
  },
  {
    key: "id",
    label: "",
    render: () => (
      <Button variant="ghost" size="sm" onClick={() => navigate("/alerts")}>
        Gérer <ArrowRight className="w-3 h-3" />
      </Button>
    ),
  },
];

/* ── Page principale ─────────────────────────────────────────────── */
export default function DashboardPage() {
  const navigate = useNavigate();
  const [rescoreId, setRescoreId] = useState("");
  const [rescoring, setRescoring] = useState(false);

  /* Chargement stats */
  const {
    data: stats,
    loading: loadingStats,
    refetch,
  } = useFetch(
    () => dashboardService.stats().catch(() => MOCK_DASHBOARD_STATS),
    [],
  );

  /* Chargement alertes récentes */
  const { data: alertsData, loading: loadingAlerts } = useFetch(
    () => dashboardService.recentAlerts().catch(() => ({ items: [] })),
    [],
  );
  const recentAlerts = alertsData?.items || alertsData || [];

  /* Pie data */
  const pieData = stats
    ? Object.entries(stats.clients_by_risk_category || {}).map(
        ([name, value]) => ({
          name: normalizeCategory(name),
          value,
        }),
      )
    : [];

  /* Rescore rapide */
  const handleRescore = async (e) => {
    e.preventDefault();
    if (!rescoreId.trim()) {
      toast.error("Entrez un UUID client valide");
      return;
    }
    setRescoring(true);
    try {
      const r = await scoringService.rescore(rescoreId.trim());
      toast.success(
        `Score : ${r.global_score}/100 — ${normalizeCategory(r.risk_category)}`,
      );
      setRescoreId("");
      refetch();
    } catch {
      toast.error("Rescore échoué. Vérifiez l'UUID.");
    } finally {
      setRescoring(false);
    }
  };

  if (loadingStats)
    return (
      <Layout pageTitle="Dashboard">
        <Loader />
      </Layout>
    );

  return (
    <Layout pageTitle="Dashboard">
      <div className="space-y-6">
        {/* ── KPI ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <KpiCard
            label="Total clients"
            value={stats?.total_clients?.toLocaleString("fr-FR")}
            icon={Users}
            color="primary"
            sub="Portefeuille IMF"
          />
          <KpiCard
            label="Risque élevé"
            value={
              stats?.clients_by_risk_category?.["ÉLEVÉ"] ??
              stats?.clients_by_risk_category?.ELEVE ??
              0
            }
            icon={AlertTriangle}
            color="danger"
            sub="Score ≥ 67 pts"
          />
          <KpiCard
            label="Alertes ouvertes"
            value={stats?.open_alerts_count}
            icon={AlertTriangle}
            color="accent"
            sub="Nécessitent une action"
          />
          <KpiCard
            label="Transactions (30j)"
            value={stats?.transactions_last_30d?.count?.toLocaleString("fr-FR")}
            icon={TrendingUp}
            color="secondary"
            sub={formatAmount(stats?.transactions_last_30d?.total_amount)}
          />
        </div>

        {/* ── Row 2 : Pie + actions ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {/* Pie chart */}
          <Card title="Répartition du risque" className="lg:col-span-1">
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={210}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {pieData.map(({ name }) => (
                      <Cell key={name} fill={PIE_COLORS[name] || "#9CA3AF"} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                  <Legend
                    iconSize={10}
                    iconType="circle"
                    formatter={(v) => (
                      <span className="text-xs text-[#6B7280]">{v}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-40 text-[#9CA3AF] text-sm">
                Aucune donnée
              </div>
            )}
          </Card>

          {/* Actions rapides + Rescore */}
          <div className="lg:col-span-2 space-y-4">
            <Card title="Actions rapides">
              <div className="flex flex-col sm:flex-row gap-3">
                <Button
                  onClick={() => navigate("/clients/new")}
                  className="flex-1 justify-center"
                >
                  <Plus className="w-4 h-4" /> Nouveau client
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => navigate("/alerts")}
                  className="flex-1 justify-center"
                >
                  <AlertTriangle className="w-4 h-4" /> Gérer les alertes
                </Button>
              </div>
            </Card>

            <Card title="Rescore rapide">
              <form
                onSubmit={handleRescore}
                className="flex flex-col sm:flex-row gap-2"
              >
                <input
                  className="flex-1 min-w-0 px-3 py-2.5 rounded-xl border border-[#E5E7EB] text-sm
                             focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]/30 focus:border-[#1E3A8A]"
                  placeholder="UUID du client à rescorer…"
                  value={rescoreId}
                  onChange={(e) => setRescoreId(e.target.value)}
                />
                <Button
                  type="submit"
                  variant="secondary"
                  loading={rescoring}
                  className="w-full sm:w-auto flex-shrink-0 justify-center"
                >
                  <RefreshCw className="w-4 h-4" /> Scorer
                </Button>
              </form>
              <p className="text-xs text-[#9CA3AF] mt-2">
                Entrez l&apos;UUID du client pour lancer un recalcul immédiat du
                score LBC/FT.
              </p>
            </Card>
          </div>
        </div>

        {/* ── 5 dernières alertes ── */}
        <Card
          title="5 dernières alertes"
          action={
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/alerts")}
            >
              Voir tout <ArrowRight className="w-3 h-3" />
            </Button>
          }
          noPad
        >
          <Table
            columns={ALERT_COLS(navigate)}
            data={recentAlerts.slice(0, 5)}
            loading={loadingAlerts}
            emptyText="Aucune alerte récente"
          />
        </Card>
      </div>
    </Layout>
  );
}
