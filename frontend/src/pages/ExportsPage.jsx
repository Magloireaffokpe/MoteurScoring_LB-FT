// src/pages/ExportsPage.jsx
import { useState } from "react";
import { FileText, Download, AlertTriangle } from "lucide-react";

import { Layout } from "../components/Layout";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { FormInput } from "../components/FormInput";
import { exportService } from "../services/exportService";

import toast from "react-hot-toast";

export default function ExportsPage() {
  const [customerId, setCustomerId] = useState("");
  const [alertId, setAlertId] = useState("");
  const [days, setDays] = useState(90);
  const [loading, setLoading] = useState(null);

  const run = async (key, fn) => {
    setLoading(key);
    try {
      await fn();
      toast.success("Export téléchargé");
    } catch {
      toast.error("Erreur lors de l'export");
    } finally {
      setLoading(null);
    }
  };

  const EXPORTS = [
    {
      key: "pdf",
      icon: FileText,
      color: "bg-[#EEF2FF] text-[#1E3A8A]",
      title: "Fiche client — PDF",
      desc: "Rapport complet LBC/FT (3 pages) : identité KYC, score, contributions C1–C6, alertes, conformité CENTIF.",
      content: (
        <FormInput
          label="UUID du client"
          value={customerId}
          onChange={(e) => setCustomerId(e.target.value)}
          placeholder="550e8400-e29b-41d4-a716-446655440000"
        />
      ),
      disabled: !customerId.trim(),
      action: () =>
        run("pdf", () => exportService.customerPdf(customerId.trim())),
      label: "Télécharger PDF",
    },
    {
      key: "csv",
      icon: Download,
      color: "bg-[#ECFDF5] text-[#10B981]",
      title: "Transactions — CSV",
      desc: "Export des transactions client (séparateur « ; », UTF-8, colonnes françaises, compatible Excel).",
      content: (
        <div className="space-y-3">
          <FormInput
            label="UUID du client"
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            placeholder="550e8400-e29b-41d4-a716-446655440000"
          />
          <div>
            <label className="text-sm font-medium text-[#6B7280] block mb-1.5">
              Fenêtre temporelle :{" "}
              <span className="text-[#111827] font-bold">{days} jours</span>
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="7"
                max="730"
                step="7"
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="flex-1 accent-[#10B981]"
              />
              <span className="text-xs text-[#9CA3AF] w-16 text-right">
                {days < 30
                  ? `${days}j`
                  : days < 365
                    ? `${Math.round(days / 30)} mois`
                    : `${(days / 365).toFixed(1)} an(s)`}
              </span>
            </div>
          </div>
        </div>
      ),
      disabled: !customerId.trim(),
      action: () =>
        run("csv", () =>
          exportService.transactionsCsv(customerId.trim(), days),
        ),
      label: "Télécharger CSV",
    },
    {
      key: "sar",
      icon: AlertTriangle,
      color: "bg-[#FEF2F2] text-[#EF4444]",
      title: "Déclaration de Soupçon — SAR",
      desc: "Génère la Déclaration de Soupçon conforme CENTIF Bénin (Article 26, Loi n°2006-14). Format PDF officiel.",
      content: (
        <FormInput
          label="UUID de l'alerte"
          value={alertId}
          onChange={(e) => setAlertId(e.target.value)}
          placeholder="aa0e8400-e29b-41d4-a716-446655440000"
        />
      ),
      disabled: !alertId.trim(),
      action: () => run("sar", () => exportService.sarPdf(alertId.trim())),
      label: "Générer SAR PDF",
    },
  ];

  return (
    <Layout pageTitle="Exports">
      <div className="space-y-5 max-w-2xl mx-auto">
        <p className="text-sm text-[#6B7280]">
          Générez vos exports réglementaires. Les fichiers sont produits en
          mémoire et téléchargés automatiquement dans votre navigateur.
        </p>

        {EXPORTS.map(
          ({
            key,
            icon: Icon,
            color,
            title,
            desc,
            content,
            disabled,
            action,
            label,
          }) => (
            <Card key={key}>
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-xl flex-shrink-0 ${color}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-display font-semibold text-xl text-[#111827] mb-1">{title}</h3>
                  <p className="text-sm font-normal font-sans text-[#4B5563] mb-4 leading-relaxed">
                    {desc}
                  </p>
                  {content}
                  <Button
                    className="mt-3"
                    loading={loading === key}
                    disabled={disabled}
                    onClick={action}
                  >
                    <Download className="w-4 h-4" /> {label}
                  </Button>
                </div>
              </div>
            </Card>
          ),
        )}
      </div>
    </Layout>
  );
}
