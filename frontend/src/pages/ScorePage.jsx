// src/pages/ScorePage.jsx
// Page dédiée à la visualisation d'un score particulier
// Route : /score/:scoreId  (accessible depuis l'historique des scores)
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { Layout } from "../components/Layout";
import { ScorePanel } from "../components/ScorePanel";
import { Loader } from "../components/Loader";
import { Button } from "../components/Button";
import { Card } from "../components/Card";

import { scoringService } from "../services/scoringService";
import { useFetch } from "../hooks/useFetch";
import { formatDatetime, normalizeCategory } from "../utils/formatters";

export default function ScorePage() {
  const { scoreId } = useParams();
  const navigate = useNavigate();

  const {
    data: score,
    loading,
    error,
  } = useFetch(() => scoringService.getById(scoreId), [scoreId]);

  if (loading)
    return (
      <Layout pageTitle="Détail du score">
        <Loader />
      </Layout>
    );
  if (error || !score) {
    return (
      <Layout pageTitle="Détail du score">
        <div className="text-center py-20">
          <p className="text-[#9CA3AF] mb-4">Score introuvable.</p>
          <Button onClick={() => navigate(-1)} variant="ghost">
            <ArrowLeft className="w-4 h-4" /> Retour
          </Button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout pageTitle="Détail du score">
      <div className="max-w-3xl mx-auto space-y-5">
        {/* Retour */}
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm text-[#6B7280] hover:text-[#111827] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Retour
        </button>

        {/* Meta */}
        <Card>
          <div className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
            <div>
              <span className="text-[#9CA3AF] text-xs font-medium uppercase tracking-wide block mb-0.5">
                Score ID
              </span>
              <span className="font-mono text-[#111827] text-xs">
                {score.id}
              </span>
            </div>
            <div>
              <span className="text-[#9CA3AF] text-xs font-medium uppercase tracking-wide block mb-0.5">
                Client ID
              </span>
              <button
                className="font-mono text-[#1E3A8A] text-xs hover:underline"
                onClick={() => navigate(`/clients/${score.customer_id}`)}
              >
                {score.customer_id}
              </button>
            </div>
            <div>
              <span className="text-[#9CA3AF] text-xs font-medium uppercase tracking-wide block mb.5">
                Calculé le
              </span>
              <span className="text-[#111827] text-xs">
                {formatDatetime(score.scored_at)}
              </span>
            </div>
            <div>
              <span className="text-[#9CA3AF] text-xs font-medium uppercase tracking-wide block mb-0.5">
                Courant
              </span>
              <span
                className={
                  score.is_current
                    ? "text-[#10B981] font-semibold text-xs"
                    : "text-[#9CA3AF] text-xs"
                }
              >
                {score.is_current ? "✓ Score actuel" : "Archivé"}
              </span>
            </div>
          </div>
        </Card>

        {/* ScorePanel */}
        <ScorePanel
          score={score.global_score}
          riskCategory={score.risk_category}
          detailJson={score.detail_json}
          scoredAt={score.scored_at}
          scoredBy={score.scored_by}
        />

        {/* Bouton vers la fiche client */}
        <div className="flex justify-center">
          <Button
            variant="outline"
            onClick={() => navigate(`/clients/${score.customer_id}`)}
          >
            Voir la fiche client complète
          </Button>
        </div>
      </div>
    </Layout>
  );
}
