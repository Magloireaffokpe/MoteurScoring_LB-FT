// src/pages/EditClientPage.jsx
import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Save, ShieldAlert } from "lucide-react";

import { Layout } from "../components/Layout";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Loader } from "../components/Loader";
import { FormInput, FormSelect } from "../components/FormInput";

import {
  customerService,
  referentialService,
} from "../services/customerService";
import { scoringService } from "../services/scoringService";

import { PROFESSIONS } from "../utils/constants";
import { clsx } from "clsx";
import toast from "react-hot-toast";

const STATUS_OPTIONS = [
  { value: "ACTIVE", label: "Actif" },
  { value: "INACTIVE", label: "Inactif" },
  { value: "SUSPENDED", label: "Suspendu" },
];

export default function EditClientPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [countries, setCountries] = useState([]);
  const [zones, setZones] = useState([]);

  const [formData, setFormData] = useState({
    prenom: "",
    nom: "",
    date_naissance: "",
    phone: "",
    email: "",
    profession_code: "",
    profession_name: "",
    profession_risk: "",
    revenus_declares: "",
    pays: "",
    zone_geo: "",
    city: "",
    region: "",
    status: "ACTIVE",
  });

  const [errors, setErrors] = useState({});

  // Charger le client et les référentiels
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [client, countryList, zoneList] = await Promise.all([
          customerService.get(id),
          referentialService.countries(),
          referentialService.riskZones(),
        ]);

        setCountries(countryList || []);
        setZones(zoneList || []);

        setFormData({
          prenom: client.prenom || "",
          nom: client.nom || "",
          date_naissance: client.date_naissance || "",
          phone: client.phone || "",
          email: client.email || "",
          profession_code: client.profession_code || "",
          profession_name: client.profession_name || "",
          profession_risk: client.profession_risk || "",
          revenus_declares: client.revenus_declares ?? "",
          pays: client.pays ?? "",
          zone_geo: client.zone_geo ?? "",
          city: client.city || "",
          region: client.region || "",
          status: client.status || "ACTIVE",
        });
      } catch (err) {
        toast.error("Erreur lors du chargement des données");
        navigate("/clients");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id, navigate]);

  const patch = (fields) => {
    setFormData((prev) => ({ ...prev, ...fields }));
    // Clear field error
    const keys = Object.keys(fields);
    if (keys.length > 0) {
      setErrors((errs) => {
        const updated = { ...errs };
        keys.forEach((k) => delete updated[k]);
        return updated;
      });
    }
  };

  const handleProfessionChange = (code) => {
    const prof = PROFESSIONS.find((p) => p.code === code);
    patch({
      profession_code: code,
      profession_name: prof?.name || "",
      profession_risk: prof?.risk || "",
    });
  };

  const validate = () => {
    const errs = {};
    if (!formData.prenom.trim()) errs.prenom = "Le prénom est requis";
    if (!formData.nom.trim()) errs.nom = "Le nom de famille est requis";
    if (!formData.profession_code) errs.profession_code = "La profession est requise";
    if (!formData.pays) errs.pays = "Le pays est requis";

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) {
      toast.error("Veuillez remplir les champs obligatoires");
      return;
    }

    setSaving(true);
    const toastId = toast.loading("Mise à jour du client...");
    try {
      const payload = {
        nom: formData.nom.trim(),
        prenom: formData.prenom.trim(),
        date_naissance: formData.date_naissance || null,
        phone: formData.phone || null,
        email: formData.email || null,
        profession_code: formData.profession_code || null,
        profession_name: formData.profession_name || null,
        profession_risk: formData.profession_risk || null,
        revenus_declares: formData.revenus_declares !== "" ? parseFloat(formData.revenus_declares) : null,
        pays: formData.pays ? parseInt(formData.pays) : null,
        zone_geo: formData.zone_geo ? parseInt(formData.zone_geo) : null,
        city: formData.city || null,
        region: formData.region || null,
        status: formData.status || "ACTIVE",
      };

      // Mettre à jour le profil du client
      await customerService.update(id, payload);

      // Lancer automatiquement un rescoring suite aux changements de profil
      try {
        await scoringService.rescore(id);
      } catch (scoreErr) {
        console.warn("Échec du rescoring automatique", scoreErr);
      }

      toast.success("Client mis à jour et re-calculé avec succès !", { id: toastId });
      navigate(`/clients/${id}`);
    } catch (err) {
      toast.error("Échec de la mise à jour", { id: toastId });
    } finally {
      setSaving(false);
    }
  };

  const RISK_COLORS = {
    LOW: "text-[#059669]",
    MEDIUM: "text-[#D97706]",
    HIGH: "text-[#DC2626]",
  };
  const RISK_LABELS = { LOW: "Faible", MEDIUM: "Moyen", HIGH: "Élevé" };

  const ZONE_RISK_COLORS = {
    FAIBLE: "text-[#059669]",
    MOYEN: "text-[#D97706]",
    ELEVE: "text-[#DC2626]",
    TRES_ELEVE: "text-[#DC2626]",
  };

  const selectedZone = zones.find(
    (z) => String(z.id) === String(formData.zone_geo),
  );

  if (loading) {
    return (
      <Layout pageTitle="Modifier le client">
        <Loader />
      </Layout>
    );
  }

  return (
    <Layout pageTitle="Modifier le client">
      <div className="max-w-4xl mx-auto space-y-5">
        {/* Navigation */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(`/clients/${id}`)}
            className="flex items-center gap-2 text-sm text-[#6B7280] hover:text-[#111827] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Annuler
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Colonne Gauche: Identité & Profession */}
            <div className="space-y-5">
              <Card title="Informations Personnelles">
                <div className="space-y-4">
                  <FormInput
                    label="Prénom"
                    required
                    name="prenom"
                    value={formData.prenom}
                    error={errors.prenom}
                    onChange={(e) => patch({ prenom: e.target.value })}
                    placeholder="ex : Koffi"
                  />
                  <FormInput
                    label="Nom de famille"
                    required
                    name="nom"
                    value={formData.nom}
                    error={errors.nom}
                    onChange={(e) => patch({ nom: e.target.value.toUpperCase() })}
                    placeholder="ex : BIAOU"
                  />
                  <FormInput
                    label="Date de naissance"
                    type="date"
                    name="date_naissance"
                    value={formData.date_naissance}
                    onChange={(e) => patch({ date_naissance: e.target.value })}
                  />
                  <FormInput
                    label="Téléphone"
                    name="phone"
                    value={formData.phone}
                    error={errors.phone}
                    onChange={(e) => patch({ phone: e.target.value })}
                    placeholder="+22966123456"
                  />
                  <FormInput
                    label="Adresse email"
                    type="email"
                    name="email"
                    value={formData.email}
                    error={errors.email}
                    onChange={(e) => patch({ email: e.target.value })}
                    placeholder="koffi@example.bj"
                  />
                </div>
              </Card>

              <Card title="Profession & Revenus">
                <div className="space-y-4">
                  <FormSelect
                    label="Profession / Secteur d'activité"
                    required
                    name="profession_code"
                    value={formData.profession_code}
                    error={errors.profession_code}
                    onChange={(e) => handleProfessionChange(e.target.value)}
                  >
                    <option value="">— Sélectionner une profession —</option>
                    {PROFESSIONS.map((p) => (
                      <option key={p.code} value={p.code}>
                        {p.name}
                      </option>
                    ))}
                  </FormSelect>

                  {formData.profession_risk && (
                    <div className="flex items-center gap-2 px-4 py-2.5 bg-[#F9FAFB] rounded-xl border border-[#E5E7EB] text-sm">
                      <span className="text-[#6B7280]">Risque profession :</span>
                      <span
                        className={clsx("font-bold", RISK_COLORS[formData.profession_risk])}
                      >
                        {RISK_LABELS[formData.profession_risk]}
                      </span>
                    </div>
                  )}

                  <FormInput
                    label="Revenus mensuels déclarés (XOF)"
                    type="number"
                    name="revenus_declares"
                    value={formData.revenus_declares}
                    error={errors.revenus_declares}
                    min="0"
                    step="1000"
                    onChange={(e) => patch({ revenus_declares: e.target.value })}
                    placeholder="250000"
                  />
                </div>
              </Card>
            </div>

            {/* Colonne Droite: Géographie & Statut */}
            <div className="space-y-5">
              <Card title="Géographie & Localisation">
                <div className="space-y-4">
                  <FormSelect
                    label="Pays / Nationalité"
                    required
                    name="pays"
                    value={formData.pays}
                    error={errors.pays}
                    onChange={(e) => patch({ pays: e.target.value })}
                  >
                    <option value="">— Sélectionner un pays —</option>
                    {countries.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.code_iso}){c.is_fatf ? " ⚠ FATF" : ""}
                        {c.is_border ? " ⚠ Frontalier" : ""}
                      </option>
                    ))}
                  </FormSelect>

                  <FormSelect
                    label="Zone géographique"
                    name="zone_geo"
                    value={formData.zone_geo}
                    onChange={(e) => patch({ zone_geo: e.target.value })}
                  >
                    <option value="">— Sélectionner une zone —</option>
                    {zones.map((z) => (
                      <option key={z.id} value={z.id}>
                        {z.name} — {z.risk_level}
                      </option>
                    ))}
                  </FormSelect>

                  {selectedZone && (
                    <div className="flex items-center gap-2 px-4 py-2.5 bg-[#F9FAFB] rounded-xl border border-[#E5E7EB] text-sm">
                      <span className="text-[#6B7280]">
                        Risque zone :
                      </span>
                      <span
                        className={clsx(
                          "font-bold",
                          ZONE_RISK_COLORS[selectedZone.risk_level],
                        )}
                      >
                        {selectedZone.risk_level}
                      </span>
                    </div>
                  )}

                  <FormInput
                    label="Ville"
                    name="city"
                    value={formData.city}
                    error={errors.city}
                    onChange={(e) => patch({ city: e.target.value })}
                    placeholder="Cotonou"
                  />
                  <FormInput
                    label="Région / Département"
                    name="region"
                    value={formData.region}
                    error={errors.region}
                    onChange={(e) => patch({ region: e.target.value })}
                    placeholder="Littoral"
                  />
                </div>
              </Card>

              <Card title="Paramètres du compte">
                <div className="space-y-4">
                  <FormSelect
                    label="Statut du client"
                    name="status"
                    value={formData.status}
                    onChange={(e) => patch({ status: e.target.value })}
                  >
                    {STATUS_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </FormSelect>
                </div>
              </Card>

              <div className="flex justify-end gap-3 pt-4">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => navigate(`/clients/${id}`)}
                >
                  Annuler
                </Button>
                <Button type="submit" loading={saving}>
                  <Save className="w-4 h-4" /> Enregistrer les modifications
                </Button>
              </div>
            </div>
          </div>
        </form>
      </div>
    </Layout>
  );
}
