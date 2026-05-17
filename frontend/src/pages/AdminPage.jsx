// src/pages/AdminPage.jsx
import { useState, useEffect, useRef, useCallback } from "react";
import {
  Settings,
  Upload,
  Plus,
  Save,
  Users,
  FileText,
  RefreshCw,
  Shield,
  AlertTriangle,
} from "lucide-react";

import { Layout } from "../components/Layout";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Loader } from "../components/Loader";
import { Table, Pagination } from "../components/Table";
import { FormInput, FormSelect, FormTextarea } from "../components/FormInput";

import { adminService } from "../services/adminService";
import { referentialService } from "../services/customerService";
import { usePagination } from "../hooks/usePagination";
import { useFetch } from "../hooks/useFetch";

import { validatePepForm } from "../utils/validators";
import {
  MOCK_CRITERIA,
  MOCK_THRESHOLDS,
  MOCK_COUNTRIES,
  PEP_SOURCES,
  FONCTIONS_PEP,
} from "../utils/constants";
import { formatDatetime, formatDate } from "../utils/formatters";

import { clsx } from "clsx";
import toast from "react-hot-toast";

const TABS = [
  { id: "criteria", label: "Poids critères", icon: Settings },
  { id: "thresholds", label: "Seuils risque", icon: Shield },
  { id: "pep", label: "Gestion PEP", icon: Users },
  { id: "audit", label: "Audit logs", icon: FileText },
];

/* ─────────────────────────────────────────────────────────────────────
   Section 1 — Poids des critères
───────────────────────────────────────────────────────────────────── */
function CriteriaSection() {
  const [criteria, setCriteria] = useState([]);
  const [weights, setWeights] = useState({});
  const [saving, setSaving] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminService
      .getCriteria()
      .then((d) => {
        const items = d.items || d || MOCK_CRITERIA;
        setCriteria(items);
        setWeights(
          Object.fromEntries(items.map((c) => [c.id, Number(c.weight)])),
        );
      })
      .catch(() => {
        setCriteria(MOCK_CRITERIA);
        setWeights(
          Object.fromEntries(MOCK_CRITERIA.map((c) => [c.id, c.weight])),
        );
      })
      .finally(() => setLoading(false));
  }, []);

  const total = Object.values(weights).reduce((s, v) => s + Number(v || 0), 0);
  const isValid = Math.abs(total - 100) < 0.5;

  const handleSave = async (c) => {
    setSaving(c.id);
    try {
      await adminService.updateCriteria(c.id, {
        weight: Number(weights[c.id]),
      });
      toast.success(`${c.code} — poids mis à jour`);
    } catch {
      toast.error("Mise à jour échouée");
    } finally {
      setSaving(null);
    }
  };

  if (loading) return <Loader />;

  const CRITERA_DESC = {
    C1: "Profil professionnel",
    C2: "Zone géographique",
    C3: "Historique transactionnel",
    C4: "Ancienneté & fidélité",
    C5: "Statut PEP",
    C6: "Cohérence KYC",
  };

  return (
    <div className="space-y-4">
      {/* Indicateur total */}
      <div
        className={clsx(
          "flex items-center justify-between px-4 py-3 rounded-xl border text-sm font-medium",
          isValid
            ? "bg-[#ECFDF5] border-[#A7F3D0] text-[#059669]"
            : "bg-[#FEF2F2] border-[#FECACA] text-[#DC2626]",
        )}
      >
        <span>
          Somme des poids : <strong>{total.toFixed(1)} %</strong>
        </span>
        {!isValid && (
          <span className="text-xs">La somme doit être égale à 100 %</span>
        )}
      </div>

      <div className="space-y-3">
        {criteria.map((c) => (
          <Card key={c.id}>
              <div className="flex flex-col sm:flex-row sm:items-center gap-4 w-full">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-3xl font-bold font-display text-[#1E3A8A]">
                      {c.code}
                    </span>
                    <span className="text-base font-medium text-[#111827] font-sans truncate">
                      {CRITERA_DESC[c.code] || c.name}
                    </span>
                  </div>
                  <div className="h-2 bg-[#F3F4F6] rounded-full overflow-hidden w-full">
                    <div
                      className="h-full bg-[#1E3A8A] rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, weights[c.id] || 0)}%` }}
                    />
                  </div>
                </div>
                <div className="flex flex-wrap sm:flex-nowrap items-center justify-between sm:justify-end gap-3 flex-shrink-0 pt-2 sm:pt-0 border-t sm:border-0 border-[#F3F4F6]">
                  <input
                    type="range"
                    min="0"
                    max="50"
                    step="1"
                    value={weights[c.id] || 0}
                    onChange={(e) =>
                      setWeights((w) => ({ ...w, [c.id]: e.target.value }))
                    }
                    className="w-full sm:flex-1 sm:w-24 accent-[#1E3A8A]"
                  />
                  <div className="flex flex-1 sm:flex-none items-center justify-end gap-2">
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        min="0"
                        max="50"
                        value={weights[c.id] || 0}
                        onChange={(e) =>
                          setWeights((w) => ({ ...w, [c.id]: e.target.value }))
                        }
                        className="w-14 px-2 py-1.5 rounded-lg border border-[#E5E7EB] text-sm text-center
                                   font-bold font-mono focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]/30"
                      />
                      <span className="text-xs font-normal font-sans text-[#6B7280]">%</span>
                    </div>
                    <Button
                      size="sm"
                      loading={saving === c.id}
                      onClick={() => handleSave(c)}
                      className="flex-shrink-0"
                    >
                      <Save className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────
   Section 2 — Seuils de risque
───────────────────────────────────────────────────────────────────── */
function ThresholdsSection() {
  const [thresholds, setThresholds] = useState([]);
  const [local, setLocal] = useState({});
  const [saving, setSaving] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminService
      .getThresholds()
      .then((d) => {
        const items = d.items || d || MOCK_THRESHOLDS;
        setThresholds(items);
        setLocal(
          Object.fromEntries(
            items.map((t) => [t.id, { min: t.score_min, max: t.score_max }]),
          ),
        );
      })
      .catch(() => {
        setThresholds(MOCK_THRESHOLDS);
        setLocal(
          Object.fromEntries(
            MOCK_THRESHOLDS.map((t) => [
              t.id,
              { min: t.score_min, max: t.score_max },
            ]),
          ),
        );
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (t) => {
    setSaving(t.id);
    try {
      await adminService.updateThreshold(t.id, {
        score_min: Number(local[t.id].min),
        score_max: Number(local[t.id].max),
      });
      toast.success(`Seuil ${t.category} mis à jour`);
    } catch {
      toast.error("Mise à jour échouée");
    } finally {
      setSaving(null);
    }
  };

  if (loading) return <Loader />;

  const CAT_STYLES = {
    FAIBLE: {
      border: "border-[#A7F3D0]",
      bg: "bg-[#ECFDF5]",
      text: "text-[#059669]",
      badge: "bg-[#ECFDF5] text-[#059669]",
    },
    MOYEN: {
      border: "border-[#FDE68A]",
      bg: "bg-[#FFFBEB]",
      text: "text-[#D97706]",
      badge: "bg-[#FFFBEB] text-[#D97706]",
    },
    ELEVE: {
      border: "border-[#FECACA]",
      bg: "bg-[#FEF2F2]",
      text: "text-[#DC2626]",
      badge: "bg-[#FEF2F2] text-[#DC2626]",
    },
    ÉLEVÉ: {
      border: "border-[#FECACA]",
      bg: "bg-[#FEF2F2]",
      text: "text-[#DC2626]",
      badge: "bg-[#FEF2F2] text-[#DC2626]",
    },
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      {thresholds.map((t) => {
        const s = CAT_STYLES[t.category] || CAT_STYLES.FAIBLE;
        return (
          <div
            key={t.id}
            className={clsx(
              "bg-white rounded-xl border-2 p-5 space-y-4",
              s.border,
            )}
          >
            <div
              className={clsx(
                "inline-flex px-3 py-1 rounded-xl text-xs font-semibold font-sans",
                s.badge,
              )}
            >
              {t.category}
            </div>
            <FormInput
              label="Score minimum"
              type="number"
              min="0"
              max="100"
              value={local[t.id]?.min ?? t.score_min}
              onChange={(e) =>
                setLocal((l) => ({
                  ...l,
                  [t.id]: { ...l[t.id], min: e.target.value },
                }))
              }
            />
            <FormInput
              label="Score maximum"
              type="number"
              min="0"
              max="100"
              value={local[t.id]?.max ?? t.score_max}
              onChange={(e) =>
                setLocal((l) => ({
                  ...l,
                  [t.id]: { ...l[t.id], max: e.target.value },
                }))
              }
            />
            {t.required_action && (
              <p className="text-xs font-normal font-sans text-[#6B7280] border-t border-[#F3F4F6] pt-3 leading-relaxed">
                {t.required_action}
              </p>
            )}
            <Button
              fullWidth
              size="sm"
              loading={saving === t.id}
              onClick={() => handleSave(t)}
            >
              <Save className="w-3 h-3" /> Enregistrer
            </Button>
          </div>
        );
      })}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────
   Section 3 — Gestion PEP
───────────────────────────────────────────────────────────────────── */
function PepSection() {
  const fileRef = useRef();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState([]);
  const [importing, setImporting] = useState(false);
  const [countries, setCountries] = useState([]);
  const [pepAdded, setPepAdded] = useState([]);
  const [adding, setAdding] = useState(false);
  const [errors, setErrors] = useState({});

  // Formulaire PEP manuel — champs synchronisés avec PepEntry (pep_list.py de Marcos)
  const [form, setForm] = useState({
    prenom: "",
    nom: "",
    fonction: "",
    pays: "", // FK countries.id
    source: "CENTIF",
    date_debut: "", // PepEntry.date_debut
    date_fin: "", // PepEntry.date_fin (NULL = toujours en fonction)
  });

  useEffect(() => {
    referentialService
      .countries()
      .then(setCountries)
      .catch(() => setCountries(MOCK_COUNTRIES));
  }, []);

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    const reader = new FileReader();
    reader.onload = (ev) => {
      setPreview(ev.target.result.split("\n").slice(0, 8).filter(Boolean));
    };
    reader.readAsText(f);
  };

  const handleImport = async () => {
    if (!file) return;
    setImporting(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await adminService.importPep(fd);
      toast.success(
        `Import : ${res.imported} entrées, ${res.skipped || 0} ignorées`,
      );
      setFile(null);
      setPreview([]);
      if (fileRef.current) fileRef.current.value = "";
    } catch {
      toast.error("Erreur import CSV PEP");
    } finally {
      setImporting(false);
    }
  };

  const patchForm = (key, value) => {
    setForm((f) => ({ ...f, [key]: value }));
    if (errors[key]) setErrors((e) => ({ ...e, [key]: "" }));
  };

  const handleAddManual = async (e) => {
    e.preventDefault();
    const errs = validatePepForm(form);
    if (Object.keys(errs).length) {
      setErrors(errs);
      return;
    }

    setAdding(true);
    try {
      // Payload synchronisé avec PepEntry.py (Marcos)
      const payload = {
        nom: form.nom.trim(),
        prenom: form.prenom.trim(),
        fonction: form.fonction || null,
        pays: form.pays ? Number(form.pays) : null,
        source: form.source,
        date_debut: form.date_debut || null,
        date_fin: form.date_fin || null,
        active: true,
      };
      await adminService.addPep(payload);
      toast.success(`PEP ajouté : ${form.prenom} ${form.nom}`);
      setPepAdded((l) => [{ id: Date.now(), ...form }, ...l]);
      setForm({
        prenom: "",
        nom: "",
        fonction: "",
        pays: "",
        source: "CENTIF",
        date_debut: "",
        date_fin: "",
      });
      setErrors({});
    } catch {
      // Fallback local si endpoint absent
      setPepAdded((l) => [{ id: Date.now(), ...form }, ...l]);
      toast.success(`PEP ajouté localement : ${form.prenom} ${form.nom}`);
      setForm({
        prenom: "",
        nom: "",
        fonction: "",
        pays: "",
        source: "CENTIF",
        date_debut: "",
        date_fin: "",
      });
      setErrors({});
    } finally {
      setAdding(false);
    }
  };

  const addedCols = [
    { key: "prenom", label: "Prénom" },
    {
      key: "nom",
      label: "Nom",
      render: (v) => <span className="font-semibold">{v}</span>,
    },
    { key: "fonction", label: "Fonction" },
    {
      key: "source",
      label: "Source",
      render: (v) => (
        <span className="font-mono text-[11px] bg-[#EEF2FF] text-[#1E3A8A] px-2 py-0.5 rounded">
          {v}
        </span>
      ),
    },
    { key: "date_debut", label: "Depuis", render: (v) => formatDate(v) || "—" },
  ];

  return (
    <div className="space-y-5">
      {/* Import CSV */}
      <Card title="Import CSV — Liste PEP">
        <p className="text-xs text-[#9CA3AF] mb-3">
          Format attendu :{" "}
          <span className="font-mono">
            nom;prenom;fonction;pays_id;source;date_debut;date_fin
          </span>
        </p>

        <div
          className="border-2 border-dashed border-[#E5E7EB] rounded-xl p-8 text-center
                     cursor-pointer hover:border-[#1E3A8A] hover:bg-[#F9FAFB] transition-colors"
          onClick={() => fileRef.current?.click()}
        >
          <Upload className="w-8 h-8 text-[#9CA3AF] mx-auto mb-2" />
          <p className="text-sm font-medium text-[#111827]">
            {file ? file.name : "Cliquez pour sélectionner un fichier CSV"}
          </p>
          <p className="text-xs text-[#9CA3AF] mt-1">
            Formats acceptés : .csv, .txt
          </p>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.txt"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>

        {preview.length > 0 && (
          <div className="mt-3 bg-[#F9FAFB] rounded-xl border border-[#E5E7EB] p-3 overflow-y-auto max-h-36">
            <p className="text-[11px] font-semibold text-[#9CA3AF] mb-2">
              Aperçu ({preview.length} lignes) :
            </p>
            {preview.map((line, i) => (
              <p key={i} className="font-mono text-[11px] text-[#6B7280]">
                {line}
              </p>
            ))}
          </div>
        )}

        {file && (
          <Button className="mt-3" loading={importing} onClick={handleImport}>
            <Upload className="w-4 h-4" /> Importer {file.name}
          </Button>
        )}
      </Card>

      {/* Ajout manuel */}
      <Card title="Ajout manuel d'une entrée PEP">
        <p className="text-xs text-[#9CA3AF] mb-4">
          Champs synchronisés avec <span className="font-mono">PepEntry</span>{" "}
          (app/models/pep_list.py)
        </p>
        <form onSubmit={handleAddManual}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormInput
              label="Prénom"
              required
              value={form.prenom}
              error={errors.prenom}
              onChange={(e) => patchForm("prenom", e.target.value)}
              placeholder="Abdoulaye"
              helper="PepEntry.prenom — String(100)"
            />
            <FormInput
              label="Nom de famille"
              required
              value={form.nom}
              error={errors.nom}
              onChange={(e) => patchForm("nom", e.target.value.toUpperCase())}
              placeholder="BIO TCHANE"
              helper="PepEntry.nom — String(100)"
            />
            <FormInput
              label="Fonction"
              value={form.fonction}
              error={errors.fonction}
              onChange={(e) => patchForm("fonction", e.target.value)}
              placeholder="Ministre de l'Économie"
              className="sm:col-span-2"
              helper="PepEntry.fonction — String(200)"
            />
            <FormSelect
              label="Pays"
              value={form.pays}
              onChange={(e) => patchForm("pays", e.target.value)}
              helper="PepEntry.pays — FK countries.id"
            >
              <option value="">— Sélectionner un pays —</option>
              {countries.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.code_iso})
                </option>
              ))}
            </FormSelect>
            <FormSelect
              label="Source"
              value={form.source}
              onChange={(e) => patchForm("source", e.target.value)}
              helper="PepEntry.source : CENTIF | GIABA | ONU | FATF"
            >
              {PEP_SOURCES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </FormSelect>
            <FormInput
              label="Date début de fonction"
              type="date"
              value={form.date_debut}
              onChange={(e) => patchForm("date_debut", e.target.value)}
              helper="PepEntry.date_debut — Date nullable"
            />
            <FormInput
              label="Date fin de fonction (optionnel)"
              type="date"
              value={form.date_fin}
              error={errors.date_fin}
              onChange={(e) => patchForm("date_fin", e.target.value)}
              helper="PepEntry.date_fin — NULL = toujours en fonction"
            />
          </div>
          <Button type="submit" loading={adding} className="mt-4">
            <Plus className="w-4 h-4" /> Ajouter à la liste PEP
          </Button>
        </form>
      </Card>

      {/* Entrées ajoutées dans cette session */}
      {pepAdded.length > 0 && (
        <Card title={`Ajoutés dans cette session (${pepAdded.length})`} noPad>
          <Table columns={addedCols} data={pepAdded} emptyText="—" />
        </Card>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────
   Section 4 — Audit logs
───────────────────────────────────────────────────────────────────── */
function AuditSection() {
  const { page, pageSize, setPage, reset, paginationProps } = usePagination(50);
  const [actionFilter, setActionFilter] = useState("");

  const { data, loading, refetch } = useFetch(
    () =>
      adminService.getAuditLogs({
        skip: (page - 1) * pageSize,
        limit: pageSize,
        ...(actionFilter && { action: actionFilter }),
      }),
    [page, actionFilter],
  );

  const logs = data?.items || [];
  const total = data?.total || 0;

  const ACTION_TYPES = [
    "",
    "SCORING_CALCULATE",
    "SCORING_RESCORE",
    "EXPORT_CUSTOMER_PDF",
    "EXPORT_TRANSACTIONS_CSV",
    "EXPORT_SAR_PDF",
    "VIEW_CUSTOMER",
    "CREATE_CUSTOMER",
  ];

  const columns = [
    {
      key: "user_id",
      label: "Utilisateur",
      render: (v) => (
        <span className="font-mono text-[11px]">{v?.slice(0, 8)}…</span>
      ),
    },
    {
      key: "action",
      label: "Action",
      render: (v) => (
        <span className="font-mono text-[11px] bg-[#EEF2FF] text-[#1E3A8A] px-2 py-0.5 rounded">
          {v}
        </span>
      ),
    },
    { key: "resource_type", label: "Ressource" },
    {
      key: "resource_id",
      label: "ID ressource",
      render: (v) => (
        <span className="font-mono text-[11px] text-[#9CA3AF]">
          {v?.slice(0, 12)}…
        </span>
      ),
    },
    { key: "timestamp", label: "Date/Heure", render: (v) => formatDatetime(v) },
    {
      key: "ip_address",
      label: "IP",
      render: (v) => (
        <span className="font-mono text-xs text-[#9CA3AF]">{v || "—"}</span>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex gap-3 items-end flex-wrap">
        <div className="flex-1 min-w-[200px]">
          <label className="text-sm font-medium text-[#374151] font-sans block mb-1.5">
            Filtrer par action
          </label>
          <select
            className="w-full px-3 py-2.5 rounded-xl border border-[#E5E7EB] text-sm bg-white
                       focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]/30"
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              reset();
            }}
          >
            <option value="">Toutes les actions</option>
            {ACTION_TYPES.slice(1).map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>
        <Button
          variant="ghost"
          onClick={() => {
            setActionFilter("");
            reset();
            refetch();
          }}
        >
          <RefreshCw className="w-4 h-4" /> Actualiser
        </Button>
      </div>

      <Card noPad>
        <Table
          columns={columns}
          data={logs}
          loading={loading}
          emptyText="Aucun log disponible — les actions seront enregistrées ici."
        />
        <div className="px-5 pb-3">
          <Pagination {...paginationProps(total)} />
        </div>
      </Card>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────
   AdminPage principale
───────────────────────────────────────────────────────────────────── */
export default function AdminPage() {
  const [tab, setTab] = useState("criteria");

  return (
    <Layout pageTitle="Administration">
      <div className="space-y-5">
        {/* Avertissement */}
        <div className="flex items-start gap-3 px-4 py-3 bg-[#FEF2F2] border border-[#FECACA] rounded-xl text-sm text-[#DC2626]">
          <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <p className="font-medium font-sans">
            Zone réservée aux administrateurs. Toute modification des poids ou
            seuils impacte immédiatement le moteur de scoring en production.
          </p>
        </div>

        {/* Onglets */}
        <div className="flex gap-1 bg-[#F3F4F6] p-1 rounded-xl overflow-x-auto">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all",
                tab === id
                  ? "bg-white text-[#1E3A8A] shadow-sm"
                  : "text-[#6B7280] hover:text-[#111827]",
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* Contenu */}
        <div>
          {tab === "criteria" && <CriteriaSection />}
          {tab === "thresholds" && <ThresholdsSection />}
          {tab === "pep" && <PepSection />}
          {tab === "audit" && <AuditSection />}
        </div>
      </div>
    </Layout>
  );
}
