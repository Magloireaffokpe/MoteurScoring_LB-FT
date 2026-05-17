// src/pages/ClientsListPage.jsx
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Search, RefreshCw, Filter, ChevronRight } from "lucide-react";

import { Layout } from "../components/Layout";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Badge } from "../components/Badge";
import { Table, Pagination } from "../components/Table";

import { customerService } from "../services/customerService";
import { scoringService } from "../services/scoringService";
import { usePagination } from "../hooks/usePagination";

import {
  formatDatetime,
  normalizeCategory,
  formatName,
} from "../utils/formatters";
import { scoreColor } from "../utils/helpers";

import { clsx } from "clsx";
import toast from "react-hot-toast";

const KYC_OPTIONS = [
  { value: "", label: "Tous niveaux KYC" },
  { value: "LOW", label: "LOW" },
  { value: "MEDIUM", label: "MEDIUM" },
  { value: "HIGH", label: "HIGH" },
];
const STATUS_OPTIONS = [
  { value: "", label: "Tous statuts" },
  { value: "ACTIVE", label: "Actif" },
  { value: "INACTIVE", label: "Inactif" },
  { value: "SUSPENDED", label: "Suspendu" },
];
const PEP_OPTIONS = [
  { value: "", label: "PEP : Tous" },
  { value: "true", label: "PEP seulement" },
  { value: "false", label: "Non PEP" },
];

export default function ClientsListPage() {
  const navigate = useNavigate();
  const { page, pageSize, skip, setPage, reset, paginationProps } =
    usePagination(25);

  const [clients, setClients] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [rescoring, setRescoring] = useState(null);
  const [showFilter, setShowFilter] = useState(false);

  const [search, setSearch] = useState("");
  const [kyc, setKyc] = useState("");
  const [status, setStatus] = useState("");
  const [pep, setPep] = useState("");

  const load = useCallback(
    async (p = page) => {
      setLoading(true);
      try {
        const params = {
          skip: (p - 1) * pageSize,
          limit: pageSize,
          ...(search && { search }),
          ...(kyc && { kyc_level: kyc }),
          ...(status && { status }),
          ...(pep && { statut_pep: pep }),
        };
        const data = await customerService.list(params);
        setClients(data.items || []);
        setTotal(data.total || 0);
      } catch {
        toast.error("Erreur chargement clients");
      } finally {
        setLoading(false);
      }
    },
    [page, pageSize, search, kyc, status, pep],
  );

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => {
      reset();
      load(1);
    }, 400);
    return () => clearTimeout(t);
  }, [search, kyc, status, pep]); // eslint-disable-line

  useEffect(() => {
    load(page);
  }, [page]); // eslint-disable-line

  const handleRescore = async (e, id) => {
    e.stopPropagation();
    setRescoring(id);
    try {
      const r = await scoringService.rescore(id);
      toast.success(`Score mis à jour : ${r.global_score}/100`);
      load(page);
    } catch {
      toast.error("Rescore échoué");
    } finally {
      setRescoring(null);
    }
  };

  const columns = [
    {
      key: "nom",
      label: "Nom",
      render: (_, r) => (
        <span className="text-sm font-semibold text-[#111827] font-sans">
          {r.last_name || r.nom || "—"}
        </span>
      ),
    },
    {
      key: "prenom",
      label: "Prénom",
      render: (_, r) => r.first_name || r.prenom || "—",
    },
    {
      key: "score",
      label: "Score",
      render: (_, r) => {
        const sc = r.current_score ?? r.score ?? null;
        if (sc == null)
          return <span className="text-[#9CA3AF] text-xs">—</span>;
        const color = scoreColor(sc);
        return (
          <div className="flex items-center gap-2">
            <span className="font-bold font-mono text-sm text-[#1E3A8A]">
              {sc}
            </span>
            <div className="w-14 h-1.5 bg-[#F3F4F6] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{ width: `${sc}%`, backgroundColor: color }}
              />
            </div>
          </div>
        );
      },
    },
    {
      key: "risk_category",
      label: "Catégorie",
      render: (v, r) => {
        const cat = normalizeCategory(v || r.kyc_level);
        return cat ? <Badge type={cat}>{cat}</Badge> : "—";
      },
    },
    {
      key: "statut_pep",
      label: "PEP",
      render: (v, r) =>
        r.is_pep || r.statut_pep ? (
          <Badge type="PEP">PEP</Badge>
        ) : (
          <span className="text-xs font-normal font-sans text-[#9CA3AF]">Non</span>
        ),
    },
    {
      key: "date_creation",
      label: "Adhésion",
      render: (v, r) => {
        const d = r.customer_since || v;
        return (
          <span className="text-xs font-normal font-sans text-[#9CA3AF]">{formatDatetime(d)}</span>
        );
      },
    },
    {
      key: "id",
      label: "",
      render: (id) => (
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/clients/${id}`);
            }}
          >
            <ChevronRight className="w-3 h-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            loading={rescoring === id}
            onClick={(e) => handleRescore(e, id)}
            title="Rescoring"
          >
            <RefreshCw className="w-3 h-3" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <Layout pageTitle="Gestion des clients">
      <div className="space-y-4">
        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9CA3AF]" />
            <input
              className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-[#E5E7EB] text-sm bg-white
                         focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]/30 focus:border-[#1E3A8A]"
              placeholder="Rechercher…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              className="flex-1 sm:flex-none justify-center"
              onClick={() => setShowFilter((s) => !s)}
            >
              <Filter className="w-4 h-4" /> Filtres
              {(kyc || status || pep) && (
                <span className="ml-1 w-4 h-4 bg-[#1E3A8A] text-white text-[10px] rounded-full flex items-center justify-center">
                  {[kyc, status, pep].filter(Boolean).length}
                </span>
              )}
            </Button>
            <Button
              className="flex-1 sm:flex-none justify-center"
              onClick={() => navigate("/clients/new")}
            >
              <Plus className="w-4 h-4" /> Nouveau
            </Button>
          </div>
        </div>

        {/* Filtres */}
        {showFilter && (
          <Card>
            <div className="flex flex-wrap gap-4 items-end">
              {[
                {
                  label: "Niveau KYC",
                  value: kyc,
                  setter: setKyc,
                  options: KYC_OPTIONS,
                },
                {
                  label: "Statut",
                  value: status,
                  setter: setStatus,
                  options: STATUS_OPTIONS,
                },
                {
                  label: "PEP",
                  value: pep,
                  setter: setPep,
                  options: PEP_OPTIONS,
                },
              ].map(({ label, value, setter, options }) => (
                <div key={label} className="flex-1 min-w-[150px]">
                  <label className="text-sm font-medium text-[#374151] font-sans block mb-1.5">
                    {label}
                  </label>
                  <select
                    className="w-full px-3 py-2.5 rounded-xl border border-[#E5E7EB] text-sm bg-white
                               focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]/30"
                    value={value}
                    onChange={(e) => setter(e.target.value)}
                  >
                    {options.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setKyc("");
                  setStatus("");
                  setPep("");
                  setSearch("");
                }}
              >
                Réinitialiser
              </Button>
            </div>
          </Card>
        )}

        {/* Table */}
        <Card noPad>
          <div className="flex items-center justify-between px-5 py-3 border-b border-[#E5E7EB]">
            <p className="text-sm font-medium text-[#374151] font-sans">
              {loading
                ? "Chargement…"
                : `${total} client${total > 1 ? "s" : ""}`}
            </p>
          </div>
          <Table
            columns={columns}
            data={clients}
            loading={loading}
            onRowClick={(row) => navigate(`/clients/${row.id}`)}
            emptyText="Aucun client trouvé. Modifiez vos filtres."
          />
          <div className="px-5 pb-3">
            <Pagination {...paginationProps(total)} />
          </div>
        </Card>
      </div>
    </Layout>
  );
}
