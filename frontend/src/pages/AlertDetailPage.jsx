// src/pages/AlertDetailPage.jsx
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, ExternalLink, AlertTriangle } from "lucide-react";

import { Layout } from "../components/Layout";
import { Card } from "../components/Card";
import { Badge } from "../components/Badge";
import { Button } from "../components/Button";
import { Loader } from "../components/Loader";
import { ScorePanel } from "../components/ScorePanel";

import { alertService } from "../services/alertService";
import { customerService } from "../services/customerService";
import { scoringService } from "../services/scoringService";
import { useFetch } from "../hooks/useFetch";
import { formatDatetime, formatAmount, normalizeCategory } from "../utils/formatters";

const TYPE_LABELS = {
  SCORE_ELEVE: "Score élevé",
  PEP_DETECTE: "PEP détecté",
  SEUIL_DEPASSE: "Seuil dépassé",
  BENEFICIAIRE_GROUPEMENT: "Bénéficiaire groupement",
  KYC_INCOMPLET: "KYC incomplet",
  SMURFING_DETECTE: "Smurfing",
};

const STATUT_BADGE = {
  OPEN: "ÉLEVÉ",
  UNDER_REVIEW: "MOYEN",
  CLOSED: "FAIBLE",
};

export default function AlertDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const { data: alert, loading, error } = useFetch(
    () => alertService.getById(id),
    [id],
  );

  const { data: customer } = useFetch(
    () => (alert?.client_id ? customerService.get(alert.client_id) : null),
    [alert?.client_id],
  );

  const { data: score } = useFetch(
    () => (alert?.score_id ? scoringService.getById(alert.score_id) : null),
    [alert?.score_id],
  );

  const { data: transactions } = useFetch(
    () => {
      if (!alert?.tx_ids?.length) return null;
      return Promise.all(
        alert.tx_ids.map((txId) =>
          customerService.getTransactionById(txId).catch(() => null),
        ),
      );
    },
    [alert?.tx_ids],
  );

  if (loading)
    return (
      <Layout pageTitle="Détail de l'alerte">
        <Loader />
      </Layout>
    );
  if (error || !alert) {
    return (
      <Layout pageTitle="Détail de l'alerte">
        <div className="text-center py-20">
          <AlertTriangle className="w-12 h-12 text-[#E5E7EB] mx-auto mb-3" />
          <p className="text-[#9CA3AF] mb-4">Alerte introuvable.</p>
          <Button onClick={() => navigate("/alerts")} variant="ghost">
            <ArrowLeft className="w-4 h-4" /> Retour aux alertes
          </Button>
        </div>
      </Layout>
    );
  }

  const cat = normalizeCategory(alert.risk_category) || (
    ["SCORE_ELEVE", "PEP_DETECTE", "SEUIL_DEPASSE", "BENEFICIAIRE_GROUPEMENT", "SMURFING_DETECTE"].includes(alert.type_alerte)
      ? "ÉLEVÉ"
      : "MOYEN"
  );

  return (
    <Layout pageTitle={`Alerte — ${TYPE_LABELS[alert.type_alerte] || alert.type_alerte}`}>
      <div className="max-w-4xl mx-auto space-y-5">
        {/* Retour */}
        <button
          onClick={() => navigate("/alerts")}
          className="flex items-center gap-2 text-sm text-[#6B7280] hover:text-[#111827] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Retour aux alertes
        </button>

        {/* ── En-tête alerte ── */}
        <Card>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-bold font-display text-[#111827]">
                  {TYPE_LABELS[alert.type_alerte] || alert.type_alerte}
                </h2>
                <Badge type={cat}>{cat}</Badge>
                <Badge type={STATUT_BADGE[alert.statut]}>
                  {alert.statut === "OPEN"
                    ? "Ouvert"
                    : alert.statut === "UNDER_REVIEW"
                      ? "En cours"
                      : "Fermé"}
                </Badge>
              </div>
              <p className="text-xs text-[#9CA3AF]">
                Créée le {formatDatetime(alert.date_creation)}
                {alert.date_cloture && ` · Clôturée le ${formatDatetime(alert.date_cloture)}`}
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate(`/clients/${alert.client_id}`)}
              >
                <ExternalLink className="w-4 h-4" /> Voir le client
              </Button>
            </div>
          </div>

          {alert.decision && (
            <div className="mt-4 p-3 bg-[#F9FAFB] rounded-xl text-sm text-[#374151]">
              <span className="font-semibold text-xs text-[#9CA3AF] uppercase tracking-wide block mb-1">
                Décision / Notes
              </span>
              {alert.decision}
            </div>
          )}

          <div className="flex flex-wrap gap-x-8 gap-y-2 text-sm mt-4 pt-4 border-t border-[#E5E7EB]">
            <div>
              <span className="text-[#9CA3AF] text-xs font-medium uppercase tracking-wide block">
                SAR
              </span>
              <span className={alert.sar_declare ? "text-[#10B981] font-semibold" : "text-[#9CA3AF]"}>
                {alert.sar_declare ? "Déposé" : "Non déclaré"}
              </span>
            </div>
            {alert.score_id && (
              <div>
                <span className="text-[#9CA3AF] text-xs font-medium uppercase tracking-wide block">
                  Score lié
                </span>
                <button
                  className="font-mono text-[#1E3A8A] text-xs hover:underline"
                  onClick={() => navigate(`/score/${alert.score_id}`)}
                >
                  {alert.score_id.slice(0, 12)}…
                </button>
              </div>
            )}
            {alert.beneficiaire_nom && (
              <div>
                <span className="text-[#9CA3AF] text-xs font-medium uppercase tracking-wide block">
                  Bénéficiaire
                </span>
                <span className="font-semibold text-[#DC2626] text-sm">
                  {alert.beneficiaire_nom}
                </span>
              </div>
            )}
          </div>
        </Card>

        {/* ── Client ── */}
        {customer && (
          <Card title="Client concerné">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-lg font-bold text-[#111827]">
                  {customer.prenom} {customer.nom}
                </p>
                <p className="text-sm text-[#6B7280]">
                  {customer.phone} · {customer.email}
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate(`/clients/${customer.id}`)}
              >
                <ExternalLink className="w-4 h-4" /> Fiche client
              </Button>
            </div>
          </Card>
        )}

        {/* ── Score lié ── */}
        {score && (
          <ScorePanel
            score={score.global_score}
            riskCategory={score.risk_category}
            detailJson={score.detail_json}
            scoredAt={score.scored_at}
            scoredBy={score.scored_by}
          />
        )}

        {/* ── Transactions liées ── */}
        {transactions && transactions.length > 0 && (
          <Card title={`Transactions liées (${transactions.length})`} noPad>
            <div className="divide-y divide-[#F3F4F6]">
              {transactions.map((tx) =>
                tx ? (
                  <div
                    key={tx.id}
                    className="flex items-center justify-between px-5 py-3 text-sm"
                  >
                    <div className="flex items-center gap-4">
                      <Badge type={
                        tx.type_op === "DEPOT" ? "FAIBLE"
                        : tx.type_op === "RETRAIT" ? "MOYEN"
                        : "ÉLEVÉ"
                      }>
                        {tx.type_op}
                      </Badge>
                      <span className="font-mono font-bold text-[#111827]">
                        {formatAmount(tx.montant, tx.devise)}
                      </span>
                    </div>
                    <div className="text-right text-xs text-[#6B7280]">
                      <p>{formatDatetime(tx.date_op)}</p>
                      {tx.destination && (
                        <p className="font-medium text-[#374151]">
                          → {tx.destination}
                        </p>
                      )}
                    </div>
                  </div>
                ) : null,
              )}
            </div>
          </Card>
        )}
      </div>
    </Layout>
  );
}
