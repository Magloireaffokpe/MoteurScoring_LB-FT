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
  UserPlus,
} from "lucide-react";
import { Badge } from "../components/Badge";
import { Layout } from "../components/Layout";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Loader } from "../components/Loader";
import { Table, Pagination } from "../components/Table";
import { Modal, ModalFooter } from "../components/Modal";
import { FormInput, FormSelect, FormTextarea } from "../components/FormInput";

import { adminService } from "../services/adminService";
import { referentialService } from "../services/customerService";
import { pepService } from "../services/pepService";
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
  { id: "agents", label: "Gestion agents", icon: UserPlus },
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
                    <span className="text-xs font-normal font-sans text-[#6B7280]">
                      %
                    </span>
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
            {t.action && (
              <p className="text-xs font-normal font-sans text-[#6B7280] border-t border-[#F3F4F6] pt-3 leading-relaxed">
                {t.action}
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

  // Search & Listing states
  const { page, pageSize, setPage, reset, paginationProps } = usePagination(25);
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState("true"); // Default to active PEPs only

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

  const { data: pepListData, loading: loadingPepList, refetch: refetchPepList } = useFetch(
    () =>
      pepService.list({
        skip: (page - 1) * pageSize,
        limit: pageSize,
        ...(search.trim() && { search: search.trim() }),
        ...(activeFilter !== "" && { active: activeFilter === "true" }),
      }),
    [page, search, activeFilter],
  );

  const pepList = pepListData?.items || [];
  const pepTotal = pepListData?.total || 0;

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
      toast.success(res.message || "Import CSV PEP terminé");
      setFile(null);
      setPreview([]);
      if (fileRef.current) fileRef.current.value = "";
      refetchPepList();
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
      refetchPepList();
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

  const pepCols = [
    { key: "prenom", label: "Prénom" },
    {
      key: "nom",
      label: "Nom",
      render: (v) => <span className="font-semibold">{v}</span>,
    },
    { key: "fonction", label: "Fonction" },
    {
      key: "pays",
      label: "Pays",
      render: (v) => {
        const c = countries.find((country) => country.id === v);
        return c ? `${c.name} (${c.code_iso})` : `—`;
      },
    },
    {
      key: "source",
      label: "Source",
      render: (v) => (
        <span className="font-mono text-[11px] bg-[#EEF2FF] text-[#1E3A8A] px-2 py-0.5 rounded">
          {v}
        </span>
      ),
    },
    {
      key: "active",
      label: "Statut",
      render: (v) => (
        <span
          className={clsx(
            "text-[11px] px-2 py-0.5 rounded font-semibold",
            v ? "bg-[#E0F2FE] text-[#0369A1]" : "bg-[#F3F4F6] text-[#4B5563]"
          )}
        >
          {v ? "Actif" : "Inactif"}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      {/* Import CSV */}
      <Card title="Import CSV — Liste PEP">
        <p className="text-xs text-[#9CA3AF] mb-3">
          Format attendu :{" "}
          <span className="font-mono">
            nom,prenom,fonction,pays_code,source,date_debut,date_fin
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
              helper="PepEntry.prenom — String(100) not null"
            />
            <FormInput
              label="Nom de famille"
              required
              value={form.nom}
              error={errors.nom}
              onChange={(e) => patchForm("nom", e.target.value.toUpperCase())}
              placeholder="BIO TCHANE"
              helper="PepEntry.nom — String(100) not null"
            />
            <FormInput
              label="Fonction"
              value={form.fonction}
              error={errors.fonction}
              onChange={(e) => patchForm("fonction", e.target.value)}
              placeholder="Ministre de l'Économie"
              className="sm:col-span-2"
              helper="PepEntry.fonction — String(200) nullable"
            />
            <FormSelect
              label="Pays"
              value={form.pays}
              onChange={(e) => patchForm("pays", e.target.value)}
              helper="PepEntry.pays — FK countries.id nullable"
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
              helper="PepEntry.source — String(100) nullable"
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
              helper="PepEntry.date_fin — Date nullable (NULL = toujours en fonction)"
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

      {/* Base de données des PEP */}
      <Card title={`Base de données des PEP (${pepTotal})`} noPad>
        <div className="p-4 border-b border-[#E5E7EB] flex flex-col sm:flex-row gap-3 items-center justify-between">
          <div className="w-full sm:w-72">
            <input
              type="text"
              placeholder="Rechercher par nom, prénom..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                reset();
              }}
              className="w-full px-3 py-2 rounded-xl border border-[#E5E7EB] bg-white text-sm text-[#111827] placeholder-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]/30 focus:border-[#1E3A8A] transition-all duration-200 font-sans"
            />
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="activeFilter" className="text-xs font-medium text-[#374151] select-none font-sans">
              Statut :
            </label>
            <select
              id="activeFilter"
              value={activeFilter}
              onChange={(e) => {
                setActiveFilter(e.target.value);
                reset();
              }}
              className="px-3 py-1.5 rounded-xl border border-[#E5E7EB] bg-white text-xs text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]/30 focus:border-[#1E3A8A] transition-all duration-200 font-sans"
            >
              <option value="">Tous</option>
              <option value="true">Actifs</option>
              <option value="false">Inactifs</option>
            </select>
          </div>
        </div>

        <Table
          columns={pepCols}
          data={pepList}
          loading={loadingPepList}
          emptyText="Aucune personne politiquement exposée trouvée."
        />

        {pepTotal > pageSize && (
          <div className="p-4 border-t border-[#E5E7EB]">
            <Pagination
              page={page}
              total={pepTotal}
              pageSize={pageSize}
              onPageChange={setPage}
            />
          </div>
        )}
      </Card>
    </div>
  );
}

const ACTION_DESCRIPTIONS = {
  LOGIN: "Connexion à l'application",
  LIST_CLIENTS: "Consultation de la liste des clients",
  VIEW_CUSTOMER: "Consultation d'une fiche client",
  CREATE_CUSTOMER: "Création d'un nouveau client",
  UPDATE_CUSTOMER: "Modification d'une fiche client",
  LIST_ALERTS: "Consultation de la liste des alertes",
  VIEW_ALERT: "Consultation d'une alerte",
  CREATE_ALERT: "Création manuelle d'une alerte",
  UPDATE_ALERT: "Mise à jour d'une alerte",
  SCORING_CALCULATE: "Calcul du score LBC/FT initial",
  SCORING_RESCORE: "Recalcul manuel du score LBC/FT",
  SCORING_RESCORE_ALL: "Rescoring global de tous les clients",
  EXPORT_PDF: "Export PDF d'une fiche client",
  EXPORT_CSV: "Export CSV des transactions",
  IMPORT_PEP_LIST: "Import CSV de la liste PEP",
  UPDATE_SCORING_CRITERIA: "Modification des poids de scoring",
  CREATE_ACCOUNT: "Ajout d'un compte bancaire",
  CREATE_TRANSACTION: "Ajout d'une transaction",
  CREATE_DOCUMENT: "Ajout d'un document KYC",
  UPDATE_RISK_THRESHOLD: "Modification des seuils de risque",
  USER_ACTIVATED: "Activation d'un utilisateur",
  USER_DEACTIVATED: "Désactivation d'un utilisateur",
  CREATE_USER: "Création d'un compte agent",
  USER_PASSWORD_RESET: "Réinitialisation du mot de passe",
  ADD_PEP_MANUAL: "Ajout manuel d'une entrée PEP",
};

/* ─────────────────────────────────────────────────────────────────────
   Section 4 — Audit logs
───────────────────────────────────────────────────────────────────── */
function AuditSection() {
  const { page, pageSize, setPage, reset, paginationProps } = usePagination(50);
  const [actionFilter, setActionFilter] = useState("");
  const [userFilter, setUserFilter] = useState("");
  const [users, setUsers] = useState([]);
  const [detailLog, setDetailLog] = useState(null);

  // Charger la liste des utilisateurs pour faire correspondre les identifiants
  useEffect(() => {
    adminService
      .getUsers()
      .then((res) => setUsers(res.items || []))
      .catch(() => {});
  }, []);

  const { data, loading, refetch } = useFetch(
    () =>
      adminService.getAuditLogs({
        skip: (page - 1) * pageSize,
        limit: pageSize,
        ...(actionFilter && { action: actionFilter }),
        ...(userFilter && { user_id: userFilter }),
      }),
    [page, actionFilter, userFilter],
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
      render: (v) => {
        const u = users.find((usr) => String(usr.id) === String(v));
        return (
          <span className="font-mono text-[11px] font-semibold text-[#1E3A8A]">
            {u ? u.login : v?.slice(0, 8) + "…"}
          </span>
        );
      },
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
    {
      key: "client_id",
      label: "Client ID",
      render: (v) => (
        <span className="font-mono text-[11px] text-[#9CA3AF]">
          {v ? v.slice(0, 12) + "…" : "—"}
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

        <div className="flex-1 min-w-[200px]">
          <label className="text-sm font-medium text-[#374151] font-sans block mb-1.5">
            Filtrer par utilisateur
          </label>
          <select
            className="w-full px-3 py-2.5 rounded-xl border border-[#E5E7EB] text-sm bg-white
                       focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]/30"
            value={userFilter}
            onChange={(e) => {
              setUserFilter(e.target.value);
              reset();
            }}
          >
            <option value="">Tous les utilisateurs</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.login} ({u.role})
              </option>
            ))}
          </select>
        </div>

        <Button
          variant="ghost"
          onClick={() => {
            setActionFilter("");
            setUserFilter("");
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
          onRowClick={(row) => setDetailLog(row)}
        />
        <div className="px-5 pb-3">
          <Pagination {...paginationProps(total)} />
        </div>
      </Card>

      {/* Modal de détail d'un log d'audit */}
      <Modal
        open={!!detailLog}
        onClose={() => setDetailLog(null)}
        title="Détail de l'action"
        size="md"
      >
        {detailLog && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-1">
                  Action
                </p>
                <p className="font-mono text-sm font-bold text-[#1E3A8A]">
                  {detailLog.action}
                </p>
                <p className="text-xs text-[#6B7280] mt-0.5">
                  {ACTION_DESCRIPTIONS[detailLog.action] || "—"}
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-1">
                  Date & heure
                </p>
                <p className="text-sm font-medium">
                  {formatDatetime(detailLog.timestamp)}
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-1">
                  Utilisateur
                </p>
                <p className="text-sm font-medium">
                  {(() => {
                    const u = users.find(
                      (usr) => String(usr.id) === String(detailLog.user_id),
                    );
                    return u
                      ? `${u.login} (${u.role})`
                      : detailLog.user_id;
                  })()}
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-1">
                  Adresse IP
                </p>
                <p className="font-mono text-sm font-medium">
                  {detailLog.ip_address || "Non capturée"}
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-1">
                  Client cible
                </p>
                <p className="font-mono text-xs text-[#374151] break-all">
                  {detailLog.client_id || "Aucun"}
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-1">
                  ID du log
                </p>
                <p className="font-mono text-xs text-[#6B7280] break-all">
                  {detailLog.id}
                </p>
              </div>
            </div>

            <ModalFooter>
              <Button variant="ghost" onClick={() => setDetailLog(null)}>
                Fermer
              </Button>
            </ModalFooter>
          </div>
        )}
      </Modal>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────
   Section 5 — Gestion des Agents
───────────────────────────────────────────────────────────────────── */
function AgentsSection() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [toggling, setToggling] = useState(null);
  const [resetting, setResetting] = useState(null);
  const [resetModal, setResetModal] = useState({ open: false, user: null, newPassword: "" });

  const [form, setForm] = useState({
    login: "",
    password: "",
    role_name: "compliance_officer",
  });

  const loadUsers = useCallback(() => {
    setLoading(true);
    adminService
      .getUsers()
      .then((d) => {
        setUsers(d.items || d || []);
      })
      .catch(() => {
        setUsers([]);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleToggleActive = async (user) => {
    setToggling(user.id);
    try {
      await adminService.toggleUserActive(user.id);
      toast.success(`Statut de ${user.login} mis à jour`);
      loadUsers();
    } catch (err) {
      const errMsg = err.response?.data?.detail || "Action impossible";
      toast.error(errMsg);
    } finally {
      setToggling(null);
    }
  };

  const openResetModal = (user) => {
    setResetModal({ open: true, user, newPassword: "" });
  };

  const closeResetModal = () => {
    setResetModal({ open: false, user: null, newPassword: "" });
  };

  const handleResetPassword = async () => {
    if (!resetModal.newPassword?.trim()) {
      toast.error("Le nouveau mot de passe est requis");
      return;
    }

    setResetting(resetModal.user.id);
    try {
      await adminService.resetUserPassword(resetModal.user.id, resetModal.newPassword.trim());
      toast.success(`Mot de passe réinitialisé pour ${resetModal.user.login}`);
      closeResetModal();
      loadUsers();
    } catch (err) {
      const errMsg = err.response?.data?.detail || "Réinitialisation impossible";
      toast.error(errMsg);
    } finally {
      setResetting(null);
    }
  };

  const handleAddAgent = async (e) => {
    e.preventDefault();
    if (!form.login.trim() || !form.password.trim()) {
      toast.error("Veuillez remplir tous les champs obligatoires");
      return;
    }

    setAdding(true);
    try {
      await adminService.createUser({
        login: form.login.trim(),
        password: form.password.trim(),
        role_name: form.role_name,
      });
      toast.success(`Agent ${form.login} créé avec succès`);
      setForm({
        login: "",
        password: "",
        role_name: "compliance_officer",
      });
      loadUsers();
    } catch (err) {
      const errMsg = err.response?.data?.detail || "Création impossible";
      toast.error(errMsg);
    } finally {
      setAdding(false);
    }
  };

  if (loading) return <Loader />;

  const columns = [
    { key: "login", label: "Identifiant / Login", render: (v) => <span className="font-semibold">{v}</span> },
    {
      key: "role",
      label: "Rôle",
      render: (v) => (
        <Badge type={v === "admin" ? "PEP" : "MOYEN"}>
          {v === "admin" ? "Administrateur" : "Compliance Officer"}
        </Badge>
      ),
    },
    {
      key: "is_active",
      label: "Statut",
      render: (v) => (
        <span className={clsx("font-semibold text-xs", v ? "text-[#10B981]" : "text-[#EF4444]")}>
          {v ? "✓ Actif" : "✗ Inactif"}
        </span>
      ),
    },
    {
      key: "id",
      label: "Actions",
      render: (_, row) => (
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button
            size="sm"
            variant={row.is_active ? "ghost" : "outline"}
            loading={toggling === row.id}
            onClick={() => handleToggleActive(row)}
          >
            {row.is_active ? "Désactiver" : "Activer"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            loading={resetting === row.id}
            onClick={() => openResetModal(row)}
          >
            Réinitialiser MDp
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Formulaire ajout */}
      <Card title="Ajouter un nouvel agent">
        <form onSubmit={handleAddAgent}>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
            <FormInput
              label="Identifiant (Login)"
              required
              value={form.login}
              onChange={(e) => setForm((f) => ({ ...f, login: e.target.value }))}
              placeholder="ex. bio_tchane"
            />
            <FormInput
              label="Mot de passe"
              type="password"
              required
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              placeholder="••••••••"
            />
            <FormSelect
              label="Rôle de l'agent"
              value={form.role_name}
              onChange={(e) => setForm((f) => ({ ...f, role_name: e.target.value }))}
            >
              <option value="compliance_officer">Compliance Officer</option>
              <option value="admin">Administrateur</option>
            </FormSelect>
          </div>
          <Button type="submit" loading={adding} className="mt-4">
            <Plus className="w-4 h-4" /> Créer le compte
          </Button>
        </form>
      </Card>

      {/* Liste des agents */}
      <Card title="Agents enregistrés" noPad>
        <Table
          columns={columns}
          data={users}
          emptyText="Aucun agent enregistré."
        />
      </Card>

      {/* Modal réinitialisation mot de passe */}
      {resetModal.open && resetModal.user && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <Card className="w-full max-w-md">
            <div className="space-y-4">
              <h2 className="text-lg font-bold">Réinitialiser le mot de passe</h2>
              <p className="text-sm text-gray-600">
                Utilisateur : <span className="font-semibold">{resetModal.user.login}</span>
              </p>
              <FormInput
                label="Nouveau mot de passe"
                type="password"
                value={resetModal.newPassword}
                onChange={(e) => setResetModal((m) => ({ ...m, newPassword: e.target.value }))}
                placeholder="••••••••"
                autoFocus
              />
              <div className="flex gap-3 justify-end">
                <Button
                  variant="ghost"
                  onClick={closeResetModal}
                  disabled={resetting === resetModal.user.id}
                >
                  Annuler
                </Button>
                <Button
                  variant="outline"
                  loading={resetting === resetModal.user.id}
                  onClick={handleResetPassword}
                >
                  Confirmer
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
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
          {tab === "agents" && <AgentsSection />}
          {tab === "audit" && <AuditSection />}
        </div>
      </div>
    </Layout>
  );
}
