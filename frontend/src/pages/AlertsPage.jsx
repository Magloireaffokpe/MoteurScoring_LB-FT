// src/pages/AlertsPage.jsx
import { useState, useCallback } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

import { Layout } from "../components/Layout";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Badge } from "../components/Badge";
import { Modal, ModalFooter } from "../components/Modal";
import { Table, Pagination } from "../components/Table";
import { FormInput, FormSelect, FormTextarea } from "../components/FormInput";

import { alertService } from "../services/alertService";
import { exportService } from "../services/exportService";
import { useFetch } from "../hooks/useFetch";
import { usePagination } from "../hooks/usePagination";

import { formatDatetime, normalizeCategory } from "../utils/formatters";
import { clsx } from "clsx";
import toast from "react-hot-toast";

const STATUS_OPTS = [
  { v: "", l: "Tous" },
  { v: "OPEN", l: "Ouvert" },
  { v: "UNDER_REVIEW", l: "En cours" },
  { v: "CLOSED", l: "Fermé" },
];
const RISK_OPTS = [
  { v: "", l: "Tous niveaux" },
  { v: "HIGH", l: "Élevé" },
  { v: "MEDIUM", l: "Moyen" },
  { v: "LOW", l: "Faible" },
];
const ACTION_OPTS = [
  { v: "", l: "— Choisir une action —" },
  { v: "CONDITIONAL_APPROVAL", l: "Approbation conditionnelle" },
  { v: "REJECTED", l: "Rejeté" },
  { v: "UNDER_INVESTIGATION", l: "En investigation" },
  { v: "SAR_FILED", l: "SAR déposé" },
  { v: "NO_ACTION", l: "Aucune action requise" },
];

export default function AlertsPage() {
  const { page, pageSize, setPage, reset, paginationProps } = usePagination(25);
  const [statusFilter, setStatusFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("");

  const [editModal, setEditModal] = useState(false);
  const [editAlert, setEditAlert] = useState(null);
  const [editForm, setEditForm] = useState({
    statut: "",
    decision: "",
    sar_declare: false,
  });
  const [saving, setSaving] = useState(false);

  const { data, loading, refetch } = useFetch(
    () =>
      alertService.list({
        skip: (page - 1) * pageSize,
        limit: pageSize,
        ...(statusFilter && { statut: statusFilter }),
      }),
    [page, statusFilter, riskFilter],
  );

  const alerts = data?.items || [];
  const total = data?.total || 0;

  const openEdit = (alert) => {
    setEditAlert(alert);
    setEditForm({
      statut: alert.statut || "OPEN",
      decision: alert.decision || "",
      sar_declare: alert.sar_declare || false,
    });
    setEditModal(true);
  };

  const handleSave = async () => {
    if (!editAlert) return;
    setSaving(true);
    try {
      await alertService.update(editAlert.id, editForm);
      toast.success("Alerte mise à jour");
      setEditModal(false);
      refetch();
    } catch {
      toast.error("Erreur mise à jour");
    } finally {
      setSaving(false);
    }
  };

  const handleSar = async (alertId) => {
    try {
      await exportService.sarPdf(alertId);
      toast.success("SAR PDF généré");
    } catch {
      toast.error("Erreur génération SAR");
    }
  };

  const columns = [
    {
      key: "customer_name",
      label: "Client",
      render: (v, r) => (
        <span className="text-sm font-semibold text-[#111827] font-sans">
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
    {
      key: "niveau",
      label: "Niveau",
      render: (_, r) => {
        const cat =
          r.type_alerte === "SCORE_ELEVE"
            ? "ÉLEVÉ"
            : r.type_alerte === "PEP_DETECTE"
              ? "ÉLEVÉ"
              : "MOYEN";
        return <Badge type={cat}>{cat}</Badge>;
      },
    },
    {
      key: "date_creation",
      label: "Date création",
      render: (v) => formatDatetime(v),
    },
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
      key: "sar_declare",
      label: "SAR",
      render: (v) =>
        v ? (
          <span className="text-xs text-[#10B981] font-semibold font-sans">
            Déposé
          </span>
        ) : (
          <span className="text-xs text-[#9CA3AF] font-sans">—</span>
        ),
    },
    {
      key: "id",
      label: "Actions",
      render: (id, row) => (
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={() => openEdit(row)}>
            Gérer
          </Button>
          <Button variant="ghost" size="sm" onClick={() => handleSar(id)}>
            SAR
          </Button>
        </div>
      ),
    },
  ];

  // Stats rapides
  const openCount = alerts.filter((a) => a.statut === "OPEN").length;
  const reviewCount = alerts.filter((a) => a.statut === "UNDER_REVIEW").length;

  return (
    <Layout pageTitle="Gestion des alertes">
      <div className="space-y-5">
        {/* KPI mini */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            {
              label: "Alertes ouvertes",
              value: openCount,
              color: "bg-[#FEF2F2] text-[#DC2626]",
              icon: AlertTriangle,
            },
            {
              label: "En cours",
              value: reviewCount,
              color: "bg-[#FFFBEB] text-[#D97706]",
              icon: RefreshCw,
            },
            {
              label: "Chargées (page)",
              value: alerts.length,
              color: "bg-[#EEF2FF] text-[#1E3A8A]",
              icon: AlertTriangle,
            },
          ].map(({ label, value, color, icon: Icon }) => (
            <div
              key={label}
              className={clsx(
                "card flex items-center gap-3 rounded-xl border border-[#E5E7EB] p-4",
                color,
              )}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              <div>
                <p className="text-[13px] font-medium font-sans opacity-80">
                  {label}
                </p>
                <p className="text-2xl font-bold font-display">{value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Filtres */}
        <Card>
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[140px]">
              <label className="text-sm font-medium text-[#374151] font-sans block mb-1.5">
                Statut
              </label>
              <select
                className="w-full px-3 py-2.5 rounded-xl border border-[#E5E7EB] text-sm bg-white
                           focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]/30"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  reset();
                }}
              >
                {STATUS_OPTS.map((o) => (
                  <option key={o.v} value={o.v}>
                    {o.l}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex-1 min-w-[140px]">
              <label className="text-sm font-medium text-[#374151] font-sans block mb-1.5">
                Niveau de risque
              </label>
              <select
                className="w-full px-3 py-2.5 rounded-xl border border-[#E5E7EB] text-sm bg-white
                           focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]/30"
                value={riskFilter}
                onChange={(e) => {
                  setRiskFilter(e.target.value);
                  reset();
                }}
              >
                {RISK_OPTS.map((o) => (
                  <option key={o.v} value={o.v}>
                    {o.l}
                  </option>
                ))}
              </select>
            </div>
            <Button
              variant="ghost"
              className="w-full sm:w-auto justify-center"
              onClick={() => {
                setStatusFilter("");
                setRiskFilter("");
                reset();
              }}
            >
              <RefreshCw className="w-4 h-4" /> Réinitialiser
            </Button>
          </div>
        </Card>

        {/* Table */}
        <Card noPad>
          <div className="flex items-center justify-between px-5 py-3 border-b border-[#E5E7EB]">
            <p className="text-sm font-medium text-[#374151] font-sans">
              {total} alerte{total > 1 ? "s" : ""} au total
            </p>
          </div>
          <Table
            columns={columns}
            data={alerts}
            loading={loading}
            emptyText="Aucune alerte trouvée"
          />
          <div className="px-5 pb-3">
            <Pagination {...paginationProps(total)} />
          </div>
        </Card>
      </div>

      {/* Modal gestion */}
      <Modal
        open={editModal}
        onClose={() => setEditModal(false)}
        title={`Gérer — ${editAlert?.type_alerte || "Alerte"}`}
      >
        <div className="space-y-4">
          <FormSelect
            label="Nouveau statut"
            value={editForm.statut}
            onChange={(e) =>
              setEditForm((f) => ({ ...f, statut: e.target.value }))
            }
          >
            <option value="OPEN">Ouvert</option>
            <option value="UNDER_REVIEW">En cours de traitement</option>
            <option value="CLOSED">Fermé</option>
          </FormSelect>

          <FormSelect
            label="Action prise"
            value={editForm.decision}
            onChange={(e) =>
              setEditForm((f) => ({ ...f, decision: e.target.value }))
            }
          >
            {ACTION_OPTS.map((o) => (
              <option key={o.v} value={o.v}>
                {o.l}
              </option>
            ))}
          </FormSelect>

          <FormTextarea
            label="Notes / Décision"
            value={editForm.decision}
            onChange={(e) =>
              setEditForm((f) => ({ ...f, decision: e.target.value }))
            }
            placeholder="Décrivez les actions prises…"
          />

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={editForm.sar_declare}
              onChange={(e) =>
                setEditForm((f) => ({ ...f, sar_declare: e.target.checked }))
              }
              className="w-4 h-4 rounded accent-[#1E3A8A]"
            />
            <span className="text-sm font-medium text-[#111827]">
              Déclaration de soupçon (SAR) transmise à la CENTIF
            </span>
          </label>

          <ModalFooter>
            <Button variant="ghost" onClick={() => setEditModal(false)}>
              Annuler
            </Button>
            <Button loading={saving} onClick={handleSave}>
              Enregistrer
            </Button>
          </ModalFooter>
        </div>
      </Modal>
    </Layout>
  );
}
