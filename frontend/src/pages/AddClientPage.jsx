// src/pages/AddClientPage.jsx
// Formulaire d'ajout client en 3 étapes — champs synchronisés avec :
//   - app/models/customers.py        (Marcos)
//   - scripts/generate_fake_data.py  (Marcos)
//   - POST /api/clients              (contrat API v1.0)
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Check, ChevronRight } from "lucide-react";

import { Layout } from "../components/Layout";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { FormInput, FormSelect } from "../components/FormInput";

import {
  customerService,
  referentialService,
} from "../services/customerService";
import { scoringService } from "../services/scoringService";

import { PROFESSIONS, TYPES_DOC, TYPES_COMPTE } from "../utils/constants";
import { validateStep1, validateStep2 } from "../utils/validators";

import { clsx } from "clsx";
import toast from "react-hot-toast";

/* ── Valeurs initiales — strictement alignées sur Customer + CustomerDoc ── */
const INITIAL_DATA = {
  // ── Étape 1 : Customer (identité + profession) ─────────────────────────
  prenom: "", // Customer.prenom          String(100) not null
  nom: "", // Customer.nom             String(100) not null
  date_naissance: "", // Customer.date_naissance  Date nullable
  phone: "", // Customer.phone           String(20)  unique nullable
  email: "", // Customer.email           String(150) unique nullable
  profession_code: "", // Customer.profession_code String(50) nullable
  profession_name: "", // Customer.profession_name String(150) nullable
  profession_risk: "", // Customer.profession_risk String(10)  'LOW'|'MEDIUM'|'HIGH'
  revenus_declares: "", // Customer.revenus_declares Numeric(15,2) nullable

  // ── Étape 2 : Customer (localisation + KYC) + CustomerDoc ──────────────
  pays: "", // Customer.pays      FK countries.id  nullable
  zone_geo: "", // Customer.zone_geo  FK risk_zones.id nullable
  city: "", // Customer.city      String(100) nullable
  region: "", // Customer.region    String(100) nullable
  statut_pep: false, // Customer.statut_pep Boolean default false

  // CustomerDoc (si renseigné — optionnel)
  type_doc: "CNI", // CustomerDoc.type_doc    String(50)
  numero: "", // CustomerDoc.numero      String(100) nullable
  date_expiration: "", // CustomerDoc.date_expiration Date nullable
};

const STEP_LABELS = [
  "Informations personnelles",
  "Géographie & KYC",
  "Récapitulatif",
];

/* ── Stepper header ───────────────────────────────────────────────── */
function StepperHeader({ currentStep }) {
  return (
    <div className="flex items-start gap-0 mb-8">
      {STEP_LABELS.map((label, i) => {
        const done = i < currentStep;
        const active = i === currentStep;
        const pending = i > currentStep;
        return (
          <div key={i} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center">
              <div
                className={clsx(
                  "w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold",
                  "transition-all duration-300 flex-shrink-0",
                  done && "bg-[#10B981] text-white",
                  active && "bg-[#1E3A8A] text-white ring-4 ring-[#1E3A8A]/20",
                  pending &&
                    "bg-[#F3F4F6] text-[#9CA3AF] border-2 border-[#E5E7EB]",
                )}
              >
                {done ? <Check className="w-4 h-4" /> : i + 1}
              </div>
              <span
                className={clsx(
                   "text-[11px] mt-2 font-medium font-sans whitespace-nowrap text-center max-w-[90px]",
                  active
                    ? "text-[#1E3A8A]"
                    : done
                      ? "text-[#10B981]"
                      : "text-[#9CA3AF]",
                )}
              >
                {label}
              </span>
            </div>
            {i < STEP_LABELS.length - 1 && (
              <div
                className={clsx(
                  "h-0.5 flex-1 mx-3 mt-[-22px] transition-colors duration-300",
                  done ? "bg-[#10B981]" : "bg-[#E5E7EB]",
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── Étape 1 : Informations personnelles ────────────────────────── */
function Step1({ data, errors, patch }) {
  // Quand on choisit une profession, on auto-renseigne nom et risk
  const handleProfessionChange = (code) => {
    const prof = PROFESSIONS.find((p) => p.code === code);
    patch({
      profession_code: code,
      profession_name: prof?.name || "",
      profession_risk: prof?.risk || "",
    });
  };

  const RISK_COLORS = {
    LOW: "text-[#059669]",
    MEDIUM: "text-[#D97706]",
    HIGH: "text-[#DC2626]",
  };
  const RISK_LABELS = { LOW: "Faible", MEDIUM: "Moyen", HIGH: "Élevé" };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <FormInput
        label="Prénom"
        required
        name="prenom"
        value={data.prenom}
        error={errors.prenom}
        onChange={(e) => patch({ prenom: e.target.value })}
        placeholder="ex : Koffi"
        helper="Customer.prenom — String(100) not null"
      />
      <FormInput
        label="Nom de famille"
        required
        name="nom"
        value={data.nom}
        error={errors.nom}
        onChange={(e) => patch({ nom: e.target.value.toUpperCase() })}
        placeholder="ex : BIAOU"
        helper="Customer.nom — String(100) not null"
      />
      <FormInput
        label="Date de naissance"
        type="date"
        name="date_naissance"
        value={data.date_naissance}
        onChange={(e) => patch({ date_naissance: e.target.value })}
        helper="Customer.date_naissance — Date nullable"
      />
      <FormInput
        label="Téléphone"
        name="phone"
        value={data.phone}
        error={errors.phone}
        onChange={(e) => patch({ phone: e.target.value })}
        placeholder="+22966123456"
        helper="Customer.phone — unique, String(20) nullable"
      />
      <FormInput
        label="Adresse email"
        type="email"
        name="email"
        value={data.email}
        error={errors.email}
        onChange={(e) => patch({ email: e.target.value })}
        placeholder="koffi@example.bj"
        className="sm:col-span-2"
        helper="Customer.email — unique, String(150) nullable"
      />

      {/* Profession */}
      <FormSelect
        label="Profession / Secteur d'activité"
        required
        name="profession_code"
        value={data.profession_code}
        error={errors.profession_code}
        onChange={(e) => handleProfessionChange(e.target.value)}
        className="sm:col-span-2"
        helper="Customer.profession_code — String(50) nullable"
      >
        <option value="">— Sélectionner une profession —</option>
        {PROFESSIONS.map((p) => (
          <option key={p.code} value={p.code}>
            {p.name}
          </option>
        ))}
      </FormSelect>

      {/* Affichage automatique du niveau de risque */}
      {data.profession_risk && (
        <div className="sm:col-span-2 flex items-center gap-2 px-4 py-2.5 bg-[#F9FAFB] rounded-xl border border-[#E5E7EB] text-sm">
          <span className="text-[#6B7280]">Niveau de risque profession :</span>
          <span
            className={clsx("font-bold", RISK_COLORS[data.profession_risk])}
          >
            {RISK_LABELS[data.profession_risk]}
          </span>
          <span className="text-[#9CA3AF] text-xs ml-auto">
            Customer.profession_risk = &quot;{data.profession_risk}&quot;
          </span>
        </div>
      )}

      <FormInput
        label="Revenus mensuels déclarés (XOF)"
        type="number"
        name="revenus_declares"
        value={data.revenus_declares}
        error={errors.revenus_declares}
        min="0"
        step="1000"
        onChange={(e) => patch({ revenus_declares: e.target.value })}
        placeholder="250000"
        className="sm:col-span-2"
        helper="Customer.revenus_declares — Numeric(15,2) nullable"
      />
    </div>
  );
}

/* ── Étape 2 : Géographie & KYC ──────────────────────────────────── */
function Step2({ data, errors, patch, countries, zones }) {
  const ZONE_RISK_COLORS = {
    FAIBLE: "text-[#059669]",
    MOYEN: "text-[#D97706]",
    ELEVE: "text-[#DC2626]",
    TRES_ELEVE: "text-[#DC2626]",
  };

  const selectedZone = zones.find(
    (z) => String(z.id) === String(data.zone_geo),
  );

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {/* Pays — FK countries.id */}
      <FormSelect
        label="Pays / Nationalité"
        required
        name="pays"
        value={data.pays}
        error={errors.pays}
        onChange={(e) => patch({ pays: e.target.value })}
        helper="Customer.pays — FK countries.id nullable"
      >
        <option value="">— Sélectionner un pays —</option>
        {countries.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name} ({c.code_iso}){c.is_fatf ? " ⚠ FATF" : ""}
            {c.is_border ? " ⚠ Frontalier" : ""}
          </option>
        ))}
      </FormSelect>

      {/* Zone géographique — FK risk_zones.id */}
      <FormSelect
        label="Zone géographique"
        name="zone_geo"
        value={data.zone_geo}
        onChange={(e) => patch({ zone_geo: e.target.value })}
        helper="Customer.zone_geo — FK risk_zones.id nullable"
      >
        <option value="">— Sélectionner une zone —</option>
        {zones.map((z) => (
          <option key={z.id} value={z.id}>
            {z.name} — {z.risk_level}
          </option>
        ))}
      </FormSelect>

      {/* Affichage du risque de zone */}
      {selectedZone && (
        <div className="sm:col-span-2 flex items-center gap-2 px-4 py-2.5 bg-[#F9FAFB] rounded-xl border border-[#E5E7EB] text-sm">
          <span className="text-[#6B7280]">
            Risque de la zone sélectionnée :
          </span>
          <span
            className={clsx(
              "font-bold",
              ZONE_RISK_COLORS[selectedZone.risk_level],
            )}
          >
            {selectedZone.risk_level}
          </span>
          <span className="text-[#9CA3AF] text-xs ml-auto truncate max-w-xs">
            {selectedZone.description}
          </span>
        </div>
      )}

      <FormInput
        label="Ville"
        name="city"
        value={data.city}
        error={errors.city}
        onChange={(e) => patch({ city: e.target.value })}
        placeholder="Cotonou"
        helper="Customer.city — String(100) nullable"
      />
      <FormInput
        label="Région / Département"
        name="region"
        value={data.region}
        error={errors.region}
        onChange={(e) => patch({ region: e.target.value })}
        placeholder="Littoral"
        helper="Customer.region — String(100) nullable"
      />

      {/* Statut PEP — Customer.statut_pep Boolean */}
      <div className="sm:col-span-2">
        <p className="text-sm font-medium text-[#6B7280] mb-2">
          Statut PEP (Personne Exposée Politiquement)
          <span className="text-[#9CA3AF] text-xs ml-2 font-normal">
            Customer.statut_pep — Boolean default false
          </span>
        </p>
        <div className="flex gap-3">
          {[
            {
              val: false,
              label: "Non PEP — Standard",
              color: "border-[#10B981] bg-[#ECFDF5] text-[#059669]",
            },
            {
              val: true,
              label: "PEP — Vigilance renforcée",
              color: "border-[#EF4444] bg-[#FEF2F2] text-[#DC2626]",
            },
          ].map(({ val, label, color }) => (
            <button
              key={String(val)}
              type="button"
              onClick={() => patch({ statut_pep: val })}
              className={clsx(
                "flex-1 py-2.5 px-3 rounded-xl border-2 text-sm font-semibold transition-all duration-200",
                data.statut_pep === val
                  ? color
                  : "border-[#E5E7EB] text-[#9CA3AF] hover:border-[#D1D5DB]",
              )}
            >
              {label}
            </button>
          ))}
        </div>
        {data.statut_pep && (
          <p className="text-xs text-[#EF4444] mt-2 px-1">
            ⚠ Ce client sera automatiquement ajouté à la surveillance renforcée
            et son score C5 sera maximal (100 pts × poids).
          </p>
        )}
      </div>

      {/* Documents KYC — CustomerDoc */}
      <div className="sm:col-span-2 pt-2">
        <p className="text-sm font-medium text-[#6B7280] mb-3">
          Document d&apos;identité
          <span className="text-[#9CA3AF] text-xs ml-2 font-normal">
            CustomerDoc — optionnel
          </span>
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-[#F9FAFB] p-4 rounded-xl border border-[#E5E7EB]">
          <FormSelect
            label="Type de document"
            name="type_doc"
            value={data.type_doc}
            onChange={(e) => patch({ type_doc: e.target.value })}
            helper="CustomerDoc.type_doc — String(50) not null"
          >
            {TYPES_DOC.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </FormSelect>
          <FormInput
            label="Numéro du document"
            name="numero"
            value={data.numero}
            error={errors.numero}
            onChange={(e) => patch({ numero: e.target.value })}
            placeholder="B123456789"
            helper="CustomerDoc.numero — String(100) nullable"
          />
          <FormInput
            label="Date d'expiration"
            type="date"
            name="date_expiration"
            value={data.date_expiration}
            error={errors.date_expiration}
            onChange={(e) => patch({ date_expiration: e.target.value })}
            helper="CustomerDoc.date_expiration — Date nullable"
          />
        </div>
      </div>
    </div>
  );
}

/* ── Étape 3 : Récapitulatif ─────────────────────────────────────── */
function Recap({ data, countries, zones, onEdit }) {
  const country = countries.find((c) => String(c.id) === String(data.pays));
  const zone = zones.find((z) => String(z.id) === String(data.zone_geo));

  const RISK_LABELS = { LOW: "Faible", MEDIUM: "Moyen", HIGH: "Élevé" };

  const sections = [
    {
      title: "Informations personnelles",
      step: 0,
      rows: [
        { label: "Prénom", value: data.prenom || "—" },
        { label: "Nom", value: data.nom || "—" },
        { label: "Date naissance", value: data.date_naissance || "—" },
        { label: "Téléphone", value: data.phone || "—" },
        { label: "Email", value: data.email || "—" },
        { label: "Profession", value: data.profession_name || "—" },
        { label: "Code métier", value: data.profession_code || "—" },
        {
          label: "Risque profession",
          value: RISK_LABELS[data.profession_risk] || "—",
        },
        {
          label: "Revenus déclarés",
          value: data.revenus_declares
            ? `${Number(data.revenus_declares).toLocaleString("fr-FR")} XOF`
            : "—",
        },
      ],
    },
    {
      title: "Géographie & KYC",
      step: 1,
      rows: [
        {
          label: "Pays",
          value: country ? `${country.name} (${country.code_iso})` : "—",
        },
        {
          label: "Zone",
          value: zone ? `${zone.name} — ${zone.risk_level}` : "—",
        },
        { label: "Ville", value: data.city || "—" },
        { label: "Région", value: data.region || "—" },
        {
          label: "Statut PEP",
          value: data.statut_pep ? "⚠ OUI — Vigilance renforcée" : "Non",
          danger: data.statut_pep,
        },
        { label: "Type doc.", value: data.type_doc || "—" },
        { label: "N° document", value: data.numero || "—" },
        { label: "Expiration", value: data.date_expiration || "—" },
      ],
    },
  ];

  return (
    <div className="space-y-4">
      {/* Alerte de confirmation */}
      <div className="flex items-start gap-3 px-4 py-3 bg-[#EEF2FF] border border-[#C7D2FE] rounded-xl text-sm text-[#1E3A8A]">
        <Check className="w-4 h-4 mt-0.5 flex-shrink-0" />
        <p className="font-medium">
          Vérifiez les informations avant de créer le client. Après validation,
          le scoring initial sera lancé automatiquement.
        </p>
      </div>

      {sections.map(({ title, step, rows }) => (
        <Card key={title}>
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-[#111827]">{title}</h4>
            <button
              type="button"
              onClick={() => onEdit(step)}
              className="text-xs text-[#1E3A8A] hover:underline font-medium flex items-center gap-1"
            >
              Modifier <ChevronRight className="w-3 h-3" />
            </button>
          </div>
          <div className="space-y-0">
            {rows.map(({ label, value, danger }) => (
              <div
                key={label}
                className="flex gap-3 py-1.5 border-b border-[#F3F4F6] last:border-0"
              >
                <span className="text-xs text-[#9CA3AF] w-36 flex-shrink-0">
                  {label}
                </span>
                <span
                  className={clsx(
                    "text-sm flex-1 font-medium",
                    danger ? "text-[#DC2626]" : "text-[#111827]",
                  )}
                >
                  {value}
                </span>
              </div>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}

/* ── Page principale ─────────────────────────────────────────────── */
export default function AddClientPage() {
  const navigate = useNavigate();

  const [step, setStep] = useState(0);
  const [data, setData] = useState(INITIAL_DATA);
  const [errors, setErrors] = useState({});
  const [countries, setCountries] = useState([]);
  const [zones, setZones] = useState([]);
  const [submitting, setSub] = useState(false);

  // Chargement des référentiels (avec fallback mock automatique)
  useEffect(() => {
    referentialService
      .countries()
      .then(setCountries)
      .catch(() => {});
    referentialService
      .riskZones()
      .then(setZones)
      .catch(() => {});
  }, []);

  // Patch partiel des données
  const patch = (updates) => {
    setData((d) => ({ ...d, ...updates }));
    // Effacer les erreurs des champs modifiés
    const clearedErrors = Object.fromEntries(
      Object.keys(updates).map((k) => [k, ""]),
    );
    setErrors((e) => ({ ...e, ...clearedErrors }));
  };

  // Navigation : suivant
  const goNext = () => {
    let errs = {};
    if (step === 0) errs = validateStep1(data);
    if (step === 1) errs = validateStep2(data);
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      return;
    }
    setErrors({});
    setStep((s) => s + 1);
  };

  // Navigation : précédent
  const goBack = () => {
    setErrors({});
    setStep((s) => s - 1);
  };

  // Soumission finale
  const handleSubmit = async () => {
    setSub(true);
    try {
      // ── Payload conforme au contrat POST /api/clients ────────────────
      // Le backend (Marcos) mappe les noms de champs (ex: first_name → prenom)
      // selon la convention définie dans le contrat API v1.0
      const payload = {
        nom: data.nom || undefined,
        prenom: data.prenom || undefined,
        date_naissance: data.date_naissance || null,
        phone: data.phone || null,
        email: data.email || null,
        profession_code: data.profession_code || null,
        profession_name: data.profession_name || null,
        profession_risk: data.profession_risk || null,
        revenus_declares: data.revenus_declares
          ? Number(data.revenus_declares)
          : null,
        city: data.city || null,
        region: data.region || null,
        zone_geo: data.zone_geo ? Number(data.zone_geo) : null,
        pays: data.pays ? Number(data.pays) : null,
        statut_pep: data.statut_pep || false,
      };

      // 1. Créer le client
      const created = await customerService.create(payload);
      toast.success(`Client créé : ${data.prenom} ${data.nom}`);

      // 2. Scoring initial automatique (POST /api/scoring)
      try {
        const scoreResult = await scoringService.score(created.id);
        toast.success(
          `Score initial calculé : ${scoreResult.global_score}/100 — ${scoreResult.risk_category}`,
        );
      } catch {
        toast("Score initial non calculé — lancez-le depuis la fiche client.", {
          icon: "⚠️",
        });
      }

      // 3. Redirection vers la fiche client
      navigate(`/clients/${created.id}`);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        toast.error(detail.map((d) => d.msg).join(" | "));
      } else {
        toast.error(
          typeof detail === "string"
            ? detail
            : "Erreur lors de la création du client",
        );
      }
    } finally {
      setSub(false);
    }
  };

  return (
    <Layout pageTitle="Nouveau client">
      <div className="max-w-2xl mx-auto">
        {/* Retour */}
        <button
          onClick={() => navigate("/clients")}
          className="flex items-center gap-2 text-sm text-[#6B7280] hover:text-[#111827]
                     mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Retour à la liste
        </button>

        <Card>
          {/* Stepper */}
          <StepperHeader currentStep={step} />

          {/* Contenu */}
          <div className="min-h-[300px]">
            {step === 0 && <Step1 data={data} errors={errors} patch={patch} />}
            {step === 1 && (
              <Step2
                data={data}
                errors={errors}
                patch={patch}
                countries={countries}
                zones={zones}
              />
            )}
            {step === 2 && (
              <Recap
                data={data}
                countries={countries}
                zones={zones}
                onEdit={setStep}
              />
            )}
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8 pt-5 border-t border-[#E5E7EB]">
            <Button variant="ghost" onClick={goBack} disabled={step === 0}>
              <ArrowLeft className="w-4 h-4" /> Précédent
            </Button>

            {step < STEP_LABELS.length - 1 ? (
              <Button onClick={goNext}>
                Suivant <ArrowRight className="w-4 h-4" />
              </Button>
            ) : (
              <Button
                variant="secondary"
                size="lg"
                loading={submitting}
                onClick={handleSubmit}
              >
                <Check className="w-4 h-4" />
                {submitting ? "Création en cours…" : "Créer client et scorer"}
              </Button>
            )}
          </div>
        </Card>
      </div>
    </Layout>
  );
}
