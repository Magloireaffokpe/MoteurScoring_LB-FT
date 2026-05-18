// src/pages/ClientDetailPage.jsx
import { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  RefreshCw,
  FileText,
  Download,
  User,
  AlertTriangle,
  Clock,
  FileCheck,
} from "lucide-react";

import { Layout } from "../components/Layout";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Badge } from "../components/Badge";
import { Loader } from "../components/Loader";
import { Table } from "../components/Table";
import { ScorePanel } from "../components/ScorePanel";

import { customerService } from "../services/customerService";
import { scoringService } from "../services/scoringService";
import { exportService } from "../services/exportService";
import { useFetch } from "../hooks/useFetch";

import {
  formatDate,
  formatDatetime,
  formatAmount,
  normalizeCategory,
  formatPep,
  getInitials,
  formatName,
} from "../utils/formatters";
import { scoreColor } from "../utils/helpers";

import { clsx } from "clsx";
import toast from "react-hot-toast";

const TABS = [
  { id: "kyc", label: "Informations KYC", icon: User },
  { id: "scoring", label: "Scoring & Historique", icon: RefreshCw },
  { id: "alerts", label: "Alertes", icon: AlertTriangle },
];

function InfoRow({ label, value, highlight, danger }) {
  return (
    <div className="flex gap-3 py-2.5 border-b border-[#F3F4F6] last:border-0">
      <span className="text-xs font-normal font-sans text-[#9CA3AF] w-40 flex-shrink-0 pt-0.5">
        {label}
      </span>
      <span
        className={clsx(
          "text-sm flex-1 font-sans",
          highlight && "font-semibold",
          danger ? "text-[#DC2626] font-semibold" : "text-[#111827]",
        )}
      >
        {value ?? "—"}
      </span>
    </div>
  );
}

export default function ClientDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [tab, setTab] = useState("kyc");
  const [rescoring, setRescoring] = useState(false);
  const [exporting, setExporting] = useState(null);

  // Chargement données client
  const {
    data: client,
    loading,
    error,
    refetch,
  } = useFetch(() => customerService.get(id), [id]);
  const { data: scoresData, refetch: refetchScores } = useFetch(
    () => customerService.getScores(id, { limit: 10 }),
    [id],
  );
  const { data: alertsData } = useFetch(
    () => customerService.getAlerts(id),
    [id],
  );

  const scores = scoresData?.items || [];
  const alerts = alertsData?.items || [];
  const currentScore = scores.find((s) => s.is_current) || scores[0];

  const handleRescore = async () => {
    setRescoring(true);
    try {
      const r = await scoringService.rescore(id);
      toast.success(
        `Score mis à jour : ${r.global_score}/100 — ${normalizeCategory(r.risk_category)}`,
      );
      refetchScores();
      setTab("scoring");
    } catch {
      toast.error("Rescore échoué");
    } finally {
      setRescoring(false);
    }
  };

  const handleExport = async (type) => {
    setExporting(type);
    try {
      if (type === "pdf") await exportService.customerPdf(id);
      else await exportService.transactionsCsv(id);
      toast.success(`Export ${type.toUpperCase()} téléchargé`);
    } catch {
      toast.error(`Erreur export ${type.toUpperCase()}`);
    } finally {
      setExporting(null);
    }
  };

  if (loading)
    return (
      <Layout pageTitle="Fiche client">
        <Loader />
      </Layout>
    );
  if (error || !client) {
    toast.error("Client introuvable");
    navigate("/clients");
    return null;
  }

  const fullName = formatName(client);
  const isPep = client.statut_pep;
  const kycCompletion = client.kyc_completion || 0;
  const kycColor =
    kycCompletion >= 80
      ? "#10B981"
      : kycCompletion >= 50
        ? "#F59E0B"
        : "#EF4444";

  /* Colonnes historique scores */
  const scoreCols = [
    { key: "scored_at", label: "Date", render: (v) => formatDatetime(v) },
    {
      key: "global_score",
      label: "Score",
      render: (v) => <span className="font-bold font-mono">{v}/100</span>,
    },
    {
      key: "risk_category",
      label: "Catégorie",
      render: (v) => (
        <Badge type={normalizeCategory(v)}>{normalizeCategory(v)}</Badge>
      ),
    },
    {
      key: "is_current",
      label: "Courant",
      render: (v) =>
        v ? (
          <span className="text-[#10B981] font-semibold text-xs">✓ Actuel</span>
        ) : (
          <span className="text-[#9CA3AF] text-xs">Archivé</span>
        ),
    },
    {
      key: "scored_by",
      label: "Par",
      render: (v) => (
        <span className="text-xs text-[#9CA3AF]">{v || "AUTOMATED"}</span>
      ),
    },
  ];

  /* Colonnes alertes */
  const alertCols = [
    {
      key: "type_alerte",
      label: "Type",
      render: (v) => <span className="font-mono text-xs">{v}</span>,
    },
    { key: "date_creation", label: "Date", render: (v) => formatDatetime(v) },
    {
      key: "statut",
      label: "Statut",
      render: (v) => (
        <Badge type={v}>
          {v === "OPEN"
            ? "Ouvert"
            : v === "UNDER_REVIEW"
              ? "En cours"
              : "Fermé"}
        </Badge>
      ),
    },
    {
      key: "type_alerte",
      label: "Niveau",
      render: (v) => (
        <Badge
          type={
            v === "SCORE_ELEVE"
              ? "ÉLEVÉ"
              : v === "PEP_DETECTE"
                ? "ÉLEVÉ"
                : "MOYEN"
          }
        >
          {v}
        </Badge>
      ),
    },
    {
      key: "id",
      label: "SAR",
      render: (alertId, row) =>
        row.sar_declare ? (
          <span className="text-xs text-[#10B981] font-semibold">Déposé</span>
        ) : (
          <Button
            size="sm"
            variant="ghost"
            onClick={async () => {
              try {
                await exportService.sarPdf(alertId);
                toast.success("SAR généré");
              } catch {
                toast.error("Erreur SAR");
              }
            }}
          >
            <FileText className="w-3 h-3" /> SAR
          </Button>
        ),
    },
  ];

  return (
    <Layout pageTitle="Fiche client">
      <div className="max-w-5xl mx-auto space-y-5">
        {/* Header navigation */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <button
            onClick={() => navigate("/clients")}
            className="flex items-center gap-2 text-sm text-[#6B7280] hover:text-[#111827] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Retour à la liste
          </button>
          <div className="flex-1" />
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              variant="ghost"
              size="sm"
              loading={rescoring}
              onClick={handleRescore}
            >
              <RefreshCw className="w-4 h-4" /> Rescoring
            </Button>
            <Button
              variant="ghost"
              size="sm"
              loading={exporting === "pdf"}
              onClick={() => handleExport("pdf")}
            >
              <FileText className="w-4 h-4" /> Exporter PDF
            </Button>
            <Button
              variant="ghost"
              size="sm"
              loading={exporting === "csv"}
              onClick={() => handleExport("csv")}
            >
              <Download className="w-4 h-4" /> Exporter CSV
            </Button>
          </div>
        </div>

        {/* Carte identité */}
        <Card>
          <div className="flex flex-col sm:flex-row gap-5 items-start">
            {/* Avatar */}
            <div
              className="w-16 h-16 rounded-2xl bg-[#1E3A8A] flex items-center justify-center
                            text-white text-xl font-bold font-display flex-shrink-0"
            >
              {getInitials(fullName)}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <h2 className="text-xl font-bold font-display text-[#111827]">
                  {fullName}
                </h2>
                {isPep && <Badge type="PEP">PEP</Badge>}
                {client.status && (
                  <Badge type={client.status}>{client.status}</Badge>
                )}
              </div>
              <p className="text-sm text-[#6B7280]">
                {client.profession_name || "—"}
              </p>
              <p className="text-xs text-[#9CA3AF] mt-0.5 font-mono">
                ID : {id}
              </p>
            </div>

            {/* Score badge */}
            {currentScore && (
              <div className="text-center flex-shrink-0">
                <div
                  className="w-16 h-16 rounded-full border-4 flex items-center justify-center
                             font-bold text-xl font-display"
                  style={{
                    borderColor: scoreColor(currentScore.global_score),
                    color: scoreColor(currentScore.global_score),
                  }}
                >
                  {currentScore.global_score}
                </div>
                <p className="text-[13px] font-medium font-sans text-[#6B7280] mt-1">
                  {normalizeCategory(currentScore.risk_category)}
                </p>
              </div>
            )}
          </div>

          {/* Barre KYC */}
          <div className="mt-4 pt-4 border-t border-[#F3F4F6]">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-[#9CA3AF]">
                Complétion KYC
              </span>
              <span className="text-xs font-bold text-[#111827]">
                {kycCompletion} %
              </span>
            </div>
            <div className="h-2 bg-[#F3F4F6] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${kycCompletion}%`,
                  backgroundColor: kycColor,
                }}
              />
            </div>
          </div>
        </Card>

        {/* Onglets */}
        <div className="flex gap-1 bg-[#F3F4F6] p-1 rounded-xl w-fit overflow-x-auto">
          {TABS.map(({ id: tid, label, icon: Icon }) => (
            <button
              key={tid}
              onClick={() => setTab(tid)}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all",
                tab === tid
                  ? "bg-white text-[#1E3A8A] shadow-sm"
                  : "text-[#6B7280] hover:text-[#111827]",
              )}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>

        {/* Contenu onglets */}
        {tab === "kyc" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <Card title="Identité">
              <InfoRow label="Nom complet" value={fullName} highlight />
              <InfoRow
                label="Date naissance"
                value={formatDate(client.date_naissance)}
              />
              <InfoRow label="Téléphone" value={client.phone} />
              <InfoRow label="Email" value={client.email} />
              <InfoRow
                label="Adhésion"
                value={formatDatetime(client.date_creation)}
              />
            </Card>

            <Card title="Profession & Revenus">
              <InfoRow
                label="Profession"
                value={client.profession_name}
                highlight
              />
              <InfoRow label="Code métier" value={client.profession_code} />
              <InfoRow
                label="Risque profession"
                value={client.profession_risk}
              />
              <InfoRow
                label="Revenus déclarés"
                value={formatAmount(client.revenus_declares)}
              />
              <InfoRow
                label="Zone géo."
                value={
                  client.city && client.region
                    ? `${client.city}, ${client.region}`
                    : client.zone_geo
                      ? `Zone #${client.zone_geo}`
                      : "—"
                }
              />
              <InfoRow
                label="Statut PEP"
                value={isPep ? "⚠ OUI — Vigilance maximale" : "Non"}
                danger={isPep}
              />
            </Card>

            {client.accounts?.length > 0 && (
              <Card title="Comptes bancaires">
                {client.accounts.map((acc) => (
                  <div
                    key={acc.id}
                    className="flex items-center justify-between py-2.5 border-b border-[#F3F4F6] last:border-0"
                  >
                    <div>
                      <p className="text-sm font-medium">{acc.type_compte}</p>
                      <p className="text-xs text-[#9CA3AF] font-mono">
                        {acc.id?.slice(0, 12)}…
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold">
                        {formatAmount(acc.solde_moyen)}
                      </p>
                      <Badge
                        type={acc.status === "ACTIF" ? "FAIBLE" : "CLOSED"}
                      >
                        {acc.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </Card>
            )}

            {client.documents?.length > 0 && (
              <Card title="Documents KYC">
                {client.documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-start gap-3 py-2.5 border-b border-[#F3F4F6] last:border-0"
                  >
                    <FileCheck className="w-4 h-4 text-[#1E3A8A] mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm font-medium">{doc.type_doc}</p>
                      <p className="text-xs text-[#9CA3AF]">
                        N° {doc.numero || "—"}
                      </p>
                      <p className="text-xs text-[#9CA3AF]">
                        Exp. : {formatDate(doc.date_expiration)}
                      </p>
                    </div>
                    <Badge type={doc.valide ? "FAIBLE" : "ÉLEVÉ"}>
                      {doc.valide ? "Valide" : "Invalide"}
                    </Badge>
                  </div>
                ))}
              </Card>
            )}
          </div>
        )}

        {tab === "scoring" && (
          <div className="space-y-5">
            {currentScore ? (
              <ScorePanel
                score={currentScore.global_score}
                riskCategory={currentScore.risk_category}
                detailJson={currentScore.detail_json}
                scoredAt={currentScore.scored_at}
                scoredBy={currentScore.scored_by}
              />
            ) : (
              <Card>
                <div className="text-center py-10">
                  <RefreshCw className="w-10 h-10 text-[#E5E7EB] mx-auto mb-3" />
                  <p className="text-sm text-[#9CA3AF] mb-3">
                    Aucun score calculé
                  </p>
                  <Button onClick={handleRescore} loading={rescoring}>
                    <RefreshCw className="w-4 h-4" /> Calculer le score
                  </Button>
                </div>
              </Card>
            )}
            <Card title="Historique des scores" noPad>
              <Table
                columns={scoreCols}
                data={scores}
                emptyText="Aucun historique disponible"
              />
            </Card>
          </div>
        )}

        {tab === "alerts" && (
          <Card title="Alertes du client" noPad>
            <Table
              columns={alertCols}
              data={alerts}
              emptyText="Aucune alerte pour ce client"
            />
          </Card>
        )}
      </div>
    </Layout>
  );
}
