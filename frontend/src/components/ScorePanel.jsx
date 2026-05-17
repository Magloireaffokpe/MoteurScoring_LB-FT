// src/components/ScorePanel.jsx
// Utilisé dans ClientDetailPage.jsx et ScorePage.jsx
import { useMemo } from "react";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { clsx } from "clsx";
import { scoreColor } from "../utils/helpers";
import { normalizeCategory, formatDatetime } from "../utils/formatters";

/* ── Jauge circulaire SVG (sans lib externe) ─────────────────────── */
function CircularGauge({ score, size = 130 }) {
  const color = scoreColor(score ?? 0);
  const radius = 46;
  const stroke = 9;
  const circ = 2 * Math.PI * radius;
  const offset = circ - ((score ?? 0) / 100) * circ;
  const cx = size / 2,
    cy = size / 2;

  return (
    <div
      className="relative flex-shrink-0"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Piste de fond */}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="none"
          stroke="#E5E7EB"
          strokeWidth={stroke}
        />
        {/* Arc de progression */}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${cx} ${cy})`}
          style={{ transition: "stroke-dashoffset 0.9s ease-out, stroke 0.3s" }}
        />
      </svg>
      {/* Texte central */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="text-3xl font-extrabold font-display leading-none"
          style={{ color }}
        >
          {score ?? "—"}
        </span>
        <span className="text-[10px] text-[#9CA3AF] font-medium">/100</span>
      </div>
    </div>
  );
}

/* ── Barre de contribution horizontale ───────────────────────────── */
function ContribBar({ label, value, maxContrib = 25 }) {
  const pct = Math.min(100, ((value ?? 0) / maxContrib) * 100);
  const color =
    value >= maxContrib * 0.6
      ? "#EF4444"
      : value >= maxContrib * 0.3
        ? "#F59E0B"
        : "#10B981";

  return (
    <div className="flex items-center gap-3">
      <span className="w-6 text-xs font-bold text-[#1E3A8A] font-mono flex-shrink-0">
        {label}
      </span>
      <div className="flex-1 h-2 bg-[#F3F4F6] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="w-10 text-right text-[11px] font-mono text-[#6B7280] flex-shrink-0">
        {(value ?? 0).toFixed(2)}
      </span>
    </div>
  );
}

/* ── Tooltip personnalisé ────────────────────────────────────────── */
function RadarTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { subject, value } = payload[0].payload;
  return (
    <div className="bg-white border border-[#E5E7EB] rounded-xl px-3 py-2 shadow-lg text-xs">
      <span className="font-bold text-[#1E3A8A]">{subject}</span> :{" "}
      <span className="font-semibold">{Number(value).toFixed(2)} pts</span>
    </div>
  );
}

/* ── Labels de l'axe polaire ─────────────────────────────────────── */
function PolarLabel({ x, y, payload }) {
  return (
    <text
      x={x}
      y={y}
      textAnchor="middle"
      dominantBaseline="middle"
      className="text-[11px] font-bold fill-[#1E3A8A]"
      style={{ fontFamily: "Sora, sans-serif" }}
    >
      {payload.value}
    </text>
  );
}

/* ── Panneau de catégorie ─────────────────────────────────────────── */
const CAT_STYLES = {
  FAIBLE: "bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]",
  MOYEN: "bg-[#FFFBEB] text-[#D97706] border border-[#FDE68A]",
  ÉLEVÉ: "bg-[#FEF2F2] text-[#DC2626] border border-[#FECACA]",
  ELEVE: "bg-[#FEF2F2] text-[#DC2626] border border-[#FECACA]",
};

/* ── Composant principal ─────────────────────────────────────────── */
/**
 * @param {number} score          - Score global 0-100
 * @param {string} riskCategory   - 'FAIBLE' | 'MOYEN' | 'ÉLEVÉ' | 'ELEVE'
 * @param {object} detailJson     - { C1: float, C2: float, ... C6: float }
 * @param {string} scoredAt       - ISO datetime
 * @param {string} scoredBy       - 'AUTOMATED' ou login agent
 */
export function ScorePanel({
  score,
  riskCategory,
  detailJson,
  scoredAt,
  scoredBy,
}) {
  const cat = normalizeCategory(riskCategory) || "FAIBLE";
  const color = scoreColor(score ?? 0);

  // Données radar : { subject: 'C1', value: 9.0, fullMark: 25 }
  const radarData = useMemo(() => {
    if (!detailJson) return [];
    return Object.entries(detailJson).map(([key, val]) => ({
      subject: key,
      value: val,
      fullMark: 25,
    }));
  }, [detailJson]);

  const totalContrib = radarData.reduce((sum, d) => sum + (d.value ?? 0), 0);

  return (
    <div className="space-y-4">
      {/* ── Score global ── */}
      <div className="bg-white rounded-xl border border-[#E5E7EB] shadow-sm p-5">
        <div className="flex flex-col sm:flex-row items-center gap-5">
          <CircularGauge score={score} size={130} />

          <div className="flex-1 text-center sm:text-left space-y-2">
            <p className="text-[10px] font-semibold text-[#9CA3AF] uppercase tracking-widest">
              Score de risque LBC/FT
            </p>

            <span
              className={clsx(
                "inline-flex items-center px-4 py-1.5 rounded-xl",
                "text-sm font-bold tracking-wide",
                CAT_STYLES[cat] || CAT_STYLES.FAIBLE,
              )}
            >
              {cat}
            </span>

            <div className="space-y-0.5 text-xs text-[#9CA3AF]">
              {scoredAt && (
                <p>
                  Calculé le :{" "}
                  <span className="font-medium text-[#111827]">
                    {formatDatetime(scoredAt)}
                  </span>
                </p>
              )}
              {scoredBy && (
                <p>
                  Par :{" "}
                  <span className="font-medium text-[#111827]">{scoredBy}</span>
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Contributions ── */}
      {radarData.length > 0 && (
        <div className="bg-white rounded-xl border border-[#E5E7EB] shadow-sm p-5">
          <h3 className="text-[10px] font-semibold text-[#9CA3AF] uppercase tracking-widest mb-4">
            Contributions par critère (C1–C6)
          </h3>

          <div className="flex flex-col lg:flex-row gap-6">
            {/* Radar chart */}
            <div className="flex-1" style={{ height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart
                  data={radarData}
                  margin={{ top: 10, right: 25, bottom: 10, left: 25 }}
                >
                  <PolarGrid stroke="#E5E7EB" />
                  <PolarAngleAxis dataKey="subject" tick={<PolarLabel />} />
                  <PolarRadiusAxis
                    angle={30}
                    domain={[0, 25]}
                    tick={false}
                    axisLine={false}
                  />
                  <Radar
                    name="Score"
                    dataKey="value"
                    stroke={color}
                    fill={color}
                    fillOpacity={0.15}
                    strokeWidth={2.5}
                  />
                  <Tooltip content={<RadarTooltip />} />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            {/* Barres + total */}
            <div className="flex-1 flex flex-col justify-center gap-3 py-2">
              {radarData.map(({ subject, value }) => (
                <ContribBar key={subject} label={subject} value={value} />
              ))}
              <div className="flex items-center justify-between pt-3 border-t border-[#E5E7EB] text-xs mt-1">
                <span className="text-[#6B7280] font-medium">
                  Somme des contributions
                </span>
                <span className="font-bold font-mono text-[#111827]">
                  {totalContrib.toFixed(2)}
                  <span className="text-[#9CA3AF] font-normal"> / 100</span>
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
