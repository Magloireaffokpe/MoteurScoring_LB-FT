// src/pages/ClientDetailPage.jsx
import { useState, useCallback, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  RefreshCw,
  FileText,
  Download,
  User,
  AlertTriangle,
  Clock,
  FileCheck,
  Edit,
  TrendingUp,
} from "lucide-react";

import { Layout } from "../components/Layout";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Badge } from "../components/Badge";
import { Loader } from "../components/Loader";
import { Table } from "../components/Table";
import { ScorePanel } from "../components/ScorePanel";
import { Modal, ModalFooter } from "../components/Modal";
import { FormInput, FormSelect } from "../components/FormInput";

import { useAuthContext } from "../context/AuthContext";
import { customerService, referentialService } from "../services/customerService";
import { scoringService } from "../services/scoringService";
import { exportService } from "../services/exportService";
import { useFetch } from "../hooks/useFetch";

import {
  formatDate,
  formatDatetime,
  formatAmount,
  normalizeCategory,
  formatPep,
  getInitials,
  formatName,
} from "../utils/formatters";
import { TYPES_COMPTE, STATUTS_COMPTE, TYPES_DOC } from "../utils/constants";
import { scoreColor } from "../utils/helpers";

import { clsx } from "clsx";
import toast from "react-hot-toast";

const TABS = [
  { id: "kyc", label: "Informations KYC", icon: User },
  { id: "scoring", label: "Scoring & Historique", icon: RefreshCw },
  { id: "transactions", label: "Transactions", icon: Clock },
  { id: "alerts", label: "Alertes", icon: AlertTriangle },
];

function InfoRow({ label, value, highlight, danger }) {
  return (
    <div className="flex gap-3 py-2.5 border-b border-[#F3F4F6] last:border-0">
      <span className="text-xs font-normal font-sans text-[#9CA3AF] w-40 flex-shrink-0 pt-0.5">
        {label}
      </span>
      <span
        className={clsx(
          "text-sm flex-1 font-sans",
          highlight && "font-semibold",
          danger ? "text-[#DC2626] font-semibold" : "text-[#111827]",
        )}
      >
        {value ?? "—"}
      </span>
    </div>
  );
}

export default function ClientDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isComplianceOfficer } = useAuthContext();
  const [tab, setTab] = useState("kyc");
  const [rescoring, setRescoring] = useState(false);
  const [exporting, setExporting] = useState(null);

  // Modal d'ajout de transaction
  const [showTxModal, setShowTxModal] = useState(false);
  const [submittingTx, setSubmittingTx] = useState(false);
  const [txForm, setTxForm] = useState({
    type_op: "DEPOT",
    compte_id: "",
    montant: "",
    canal: "GUICHET",
    origine: null,
    destination: null,
    origine_pays_id: null,
    destination_pays_id: null,
  });
  const [txErrors, setTxErrors] = useState({});

  // Modal d'ajout de compte bancaire
  const [showAccountModal, setShowAccountModal] = useState(false);
  const [submittingAccount, setSubmittingAccount] = useState(false);
  const [accountForm, setAccountForm] = useState({
    type_compte: "COURANT",
    solde_moyen: "",
    date_ouverture: "",
    status: "ACTIF",
  });
  const [accountErrors, setAccountErrors] = useState({});

  // Modal d'ajout de document KYC
  const [showDocModal, setShowDocModal] = useState(false);
  const [submittingDoc, setSubmittingDoc] = useState(false);
  const [docForm, setDocForm] = useState({
    type_doc: "CNI",
    numero: "",
    date_expiration: "",
  });
  const [docErrors, setDocErrors] = useState({});

  // Chargement données client
  const {
    data: client,
    loading,
    error,
    refetch,
  } = useFetch(() => customerService.get(id), [id]);
  const { data: scoresData, refetch: refetchScores } = useFetch(
    () => customerService.getScores(id, { limit: 10 }),
    [id],
  );
  const { data: alertsData } = useFetch(
    () => customerService.getAlerts(id),
    [id],
  );
  const { data: transactionsData, refetch: refetchTransactions } = useFetch(
    () => customerService.getTransactions(id, { limit: 100 }),
    [id],
  );

  const { data: countriesData } = useFetch(() => referentialService.countries(), []);
  const countries = countriesData || [];

  const selectedDestinationCountry = countries.find(
    (c) => String(c.id) === String(txForm.destination_pays_id)
  );

  const txRequiresOrigin = txForm.type_op === "DEPOT";
  const txRequiresDestination = txForm.type_op === "VIREMENT";

  const getAccountTypesForOp = (typeOp) => {
    if (typeOp === "RETRAIT") return ["COURANT"];
    return ["COURANT", "EPARGNE"];
  };

  const getCanalOptionsForOp = (typeOp) => {
    if (typeOp === "RETRAIT") return ["GUICHET", "MOBILE", "ATM"];
    if (typeOp === "VIREMENT") return ["INTERNET", "MOBILE", "GUICHET"];
    return ["GUICHET", "MOBILE", "INTERNET", "ATM"];
  };

  const filteredAccounts = (client?.accounts || []).filter(
    (acc) => getAccountTypesForOp(txForm.type_op).includes(acc.type_compte)
  );

  useEffect(() => {
    const stillValid = txForm.compte_id && filteredAccounts.some((a) => a.id === txForm.compte_id);
    if (!stillValid && filteredAccounts.length) {
      setTxForm((f) => ({ ...f, compte_id: filteredAccounts[0].id }));
    }
  }, [filteredAccounts, showTxModal, txForm.compte_id]);

  const scores = scoresData?.items || [];
  const alerts = alertsData?.items || [];
  const transactions = transactionsData?.items || [];
  const currentScore = scores.find((s) => s.is_current) || scores[0];

  const [currentScoreDetail, setCurrentScoreDetail] = useState(null);

  useEffect(() => {
    if (currentScore?.id) {
      scoringService
        .getById(currentScore.id)
        .then(setCurrentScoreDetail)
        .catch(() => setCurrentScoreDetail(null));
    } else {
      setCurrentScoreDetail(null);
    }
  }, [currentScore?.id]);

  const handleRescore = async () => {
    setRescoring(true);
    try {
      const r = await scoringService.rescore(id);
      toast.success(
        `Score mis à jour : ${r.global_score}/100 — ${normalizeCategory(r.risk_category)}`,
      );
      refetchScores();
      setTab("scoring");
    } catch {
      toast.error("Rescore échoué");
    } finally {
      setRescoring(false);
    }
  };

  const handleExport = async (type) => {
    setExporting(type);
    try {
      if (type === "pdf") await exportService.customerPdf(id);
      else await exportService.transactionsCsv(id);
      toast.success(`Export ${type.toUpperCase()} téléchargé`);
    } catch {
      toast.error(`Erreur export ${type.toUpperCase()}`);
    } finally {
      setExporting(null);
    }
  };

  const handleAddTransaction = async (e) => {
    e.preventDefault();
    const errors = {};
    if (!txForm.compte_id) {
      errors.compte_id = "Sélectionnez un compte";
    }
    if (!txForm.montant || Number(txForm.montant) <= 0) {
      errors.montant = "Le montant doit être supérieur à 0";
    }
    if (txRequiresDestination && !txForm.destination) {
      errors.destination = "Destination requise";
    }
    if (txForm.type_op === "VIREMENT" && !txForm.destination_pays_id) {
      errors.destination_pays_id = "Pays de destination requis";
    }
    if (Object.keys(errors).length > 0) {
      setTxErrors(errors);
      return;
    }
    setTxErrors({});
    setSubmittingTx(true);

    try {
      const isDepot = txForm.type_op === "DEPOT";
      const isVirement = txForm.type_op === "VIREMENT";
      const r = await customerService.createTransaction(id, {
        compte_id: txForm.compte_id,
        montant: Number(txForm.montant),
        devise: "XOF",
        type_op: txForm.type_op,
        canal: txForm.canal,
        origine: isDepot ? (txForm.origine || null) : null,
        destination: isVirement ? txForm.destination : null,
        origine_pays_id: (isDepot || isVirement) ? 1 : null,
        destination_pays_id: isVirement ? (txForm.destination_pays_id ? parseInt(txForm.destination_pays_id) : null) : null,
      });
      const scoreMsg = r.new_score_global != null
        ? ` — Score : ${r.new_score_global}/100 (${normalizeCategory(r.new_score_category)})`
        : "";
      toast.success(`Transaction ajoutée${scoreMsg}`);
      setShowTxModal(false);
      setTxForm({
        type_op: "DEPOT",
        compte_id: "",
        montant: "",
        canal: "GUICHET",
        origine: null,
        destination: null,
        origine_pays_id: null,
        destination_pays_id: null,
      });
      await refetchTransactions();
      if (r.new_score_global != null) {
        refetchScores();
      }
    } catch (err) {
      console.error("Erreur d'ajout de transaction", err);
      toast.error(err.response?.data?.detail || "Impossible d'ajouter la transaction");
    } finally {
      setSubmittingTx(false);
    }
  };

  const handleAddAccount = async (e) => {
    e.preventDefault();
    const errors = {};
    if (!accountForm.type_compte) {
      errors.type_compte = "Type de compte requis";
    }
    if (!accountForm.solde_moyen || Number(accountForm.solde_moyen) <= 0) {
      errors.solde_moyen = "Solde moyen doit être supérieur à 0";
    }
    if (!accountForm.status) {
      errors.status = "Statut du compte requis";
    }

    if (Object.keys(errors).length > 0) {
      setAccountErrors(errors);
      return;
    }

    setAccountErrors({});
    setSubmittingAccount(true);

    try {
      await customerService.createAccount(id, {
        id: crypto.randomUUID(),
        type_compte: accountForm.type_compte,
        solde_moyen: Number(accountForm.solde_moyen),
        date_ouverture: accountForm.date_ouverture || null,
        status: accountForm.status,
      });
      toast.success("Compte bancaire ajouté avec succès");
      setShowAccountModal(false);
      setAccountForm({
        type_compte: "COURANT",
        solde_moyen: "",
        date_ouverture: "",
        status: "ACTIF",
      });
      await refetch();
    } catch (err) {
      console.error("Erreur d'ajout de compte", err);
      toast.error("Impossible d'ajouter le compte bancaire");
    } finally {
      setSubmittingAccount(false);
    }
  };

  const handleAddDocument = async (e) => {
    e.preventDefault();
    const errors = {};
    if (!docForm.type_doc) {
      errors.type_doc = "Type de document requis";
    }

    if (Object.keys(errors).length > 0) {
      setDocErrors(errors);
      return;
    }

    setDocErrors({});
    setSubmittingDoc(true);

    try {
      await customerService.createDocument(id, {
        type_doc: docForm.type_doc,
        numero: docForm.numero || null,
        date_expiration: docForm.date_expiration || null,
      });
      toast.success("Document KYC ajouté avec succès");
      setShowDocModal(false);
      setDocForm({
        type_doc: "CNI",
        numero: "",
        date_expiration: "",
      });
      await refetch();
    } catch (err) {
      console.error("Erreur d'ajout de document", err);
      toast.error("Impossible d'ajouter le document KYC");
    } finally {
      setSubmittingDoc(false);
    }
  };

  if (loading)
    return (
      <Layout pageTitle="Fiche client">
        <Loader />
      </Layout>
    );
  if (error || !client) {
    toast.error("Client introuvable");
    navigate("/clients");
    return null;
  }

  const fullName = formatName(client);
  const isPep = client.statut_pep;
  const kycCompletion = client.kyc_completion || 0;
  const kycColor =
    kycCompletion >= 80
      ? "#10B981"
      : kycCompletion >= 50
        ? "#F59E0B"
        : "#EF4444";

  /* Colonnes transactions */
  const txCols = [
    { key: "date_op", label: "Date & Heure", render: (v) => formatDatetime(v) },
    {
      key: "type_op",
      label: "Type",
      render: (v) => (
        <Badge
          type={
            v === "DEPOT"
              ? "FAIBLE"
              : v === "RETRAIT"
                ? "MOYEN"
                : "ÉLEVÉ"
          }
        >
          {v}
        </Badge>
      ),
    },
    {
      key: "montant",
      label: "Montant",
      render: (v, row) => (
        <span className="font-bold font-mono">
          {formatAmount(v)} {row.devise || "XOF"}
        </span>
      ),
    },
    {
      key: "canal",
      label: "Canal",
      render: (v) => <span className="text-xs">{v || "—"}</span>,
    },
    {
      key: "origine",
      label: "Origine",
      render: (v) => (
        <span className="text-xs truncate max-w-[120px] inline-block">
          {v || "—"}
        </span>
      ),
    },
    {
      key: "destination",
      label: "Destination",
      render: (v) => (
        <span className="text-xs truncate max-w-[120px] inline-block">
          {v || "—"}
        </span>
      ),
    },
  ];

  /* Colonnes historique scores */
  const scoreCols = [
    { key: "scored_at", label: "Date", render: (v) => formatDatetime(v) },
    {
      key: "global_score",
      label: "Score",
      render: (v) => <span className="font-bold font-mono">{v}/100</span>,
    },
    {
      key: "risk_category",
      label: "Catégorie",
      render: (v) => (
        <Badge type={normalizeCategory(v)}>{normalizeCategory(v)}</Badge>
      ),
    },
    {
      key: "is_current",
      label: "Courant",
      render: (v) =>
        v ? (
          <span className="text-[#10B981] font-semibold text-xs">✓ Actuel</span>
        ) : (
          <span className="text-[#9CA3AF] text-xs">Archivé</span>
        ),
    },
    {
      key: "scored_by",
      label: "Par",
      render: (v) => (
        <span className="text-xs text-[#9CA3AF]">{v || "AUTOMATED"}</span>
      ),
    },
  ];

  /* Colonnes alertes */
  const alertCols = [
    {
      key: "type_alerte",
      label: "Type",
      render: (v) => <span className="font-mono text-xs">{v}</span>,
    },
    { key: "date_creation", label: "Date", render: (v) => formatDatetime(v) },
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
      key: "type_alerte",
      label: "Niveau",
      render: (v) => (
        <Badge
          type={
            v === "SCORE_ELEVE"
              ? "ÉLEVÉ"
              : v === "PEP_DETECTE"
                ? "ÉLEVÉ"
                : "MOYEN"
          }
        >
          {v}
        </Badge>
      ),
    },
    {
      key: "id",
      label: "SAR",
      render: (alertId, row) =>
        row.sar_declare ? (
          <span className="text-xs text-[#10B981] font-semibold">Déposé</span>
        ) : (
          <Button
            size="sm"
            variant="ghost"
            onClick={async () => {
              try {
                await exportService.sarPdf(alertId);
                toast.success("SAR généré");
              } catch {
                toast.error("Erreur SAR");
              }
            }}
          >
            <FileText className="w-3 h-3" /> SAR
          </Button>
        ),
    },
  ];

  return (
    <Layout pageTitle="Fiche client">
      <div className="max-w-5xl mx-auto space-y-5">
        {/* Header navigation */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <button
            onClick={() => navigate("/clients")}
            className="flex items-center gap-2 text-sm text-[#6B7280] hover:text-[#111827] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Retour à la liste
          </button>
          <div className="flex-1" />
          <div className="flex items-center gap-2 flex-wrap">
            {isComplianceOfficer && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate(`/clients/${id}/edit`)}
              >
                <Edit className="w-4 h-4" /> Modifier
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              loading={rescoring}
              onClick={handleRescore}
            >
              <RefreshCw className="w-4 h-4" /> Rescoring
            </Button>
            <Button
              variant="ghost"
              size="sm"
              loading={exporting === "pdf"}
              onClick={() => handleExport("pdf")}
            >
              <FileText className="w-4 h-4" /> Exporter PDF
            </Button>
            <Button
              variant="ghost"
              size="sm"
              loading={exporting === "csv"}
              onClick={() => handleExport("csv")}
            >
              <Download className="w-4 h-4" /> Exporter CSV
            </Button>
          </div>
        </div>

        {/* Carte identité */}
        <Card>
          <div className="flex flex-col sm:flex-row gap-5 items-start">
            {/* Avatar */}
            <div
              className="w-16 h-16 rounded-2xl bg-[#1E3A8A] flex items-center justify-center
                            text-white text-xl font-bold font-display flex-shrink-0"
            >
              {getInitials(fullName)}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <h2 className="text-xl font-bold font-display text-[#111827]">
                  {fullName}
                </h2>
                {isPep && <Badge type="PEP">PEP</Badge>}
                {client.status && (
                  <Badge type={client.status}>{client.status}</Badge>
                )}
              </div>
              <p className="text-sm text-[#6B7280]">
                {client.profession_name || "—"}
              </p>
              <p className="text-xs text-[#9CA3AF] mt-0.5 font-mono">
                ID : {id}
              </p>
            </div>

            {/* Score badge */}
            {currentScore && (
              <div className="text-center flex-shrink-0">
                <div
                  className="w-16 h-16 rounded-full border-4 flex items-center justify-center
                             font-bold text-xl font-display"
                  style={{
                    borderColor: scoreColor(currentScore.global_score),
                    color: scoreColor(currentScore.global_score),
                  }}
                >
                  {currentScore.global_score}
                </div>
                <p className="text-[13px] font-medium font-sans text-[#6B7280] mt-1">
                  {normalizeCategory(currentScore.risk_category)}
                </p>
              </div>
            )}
          </div>

          {/* Barre KYC */}
          <div className="mt-4 pt-4 border-t border-[#F3F4F6]">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-[#9CA3AF]">
                Complétion KYC
              </span>
              <span className="text-xs font-bold text-[#111827]">
                {kycCompletion} %
              </span>
            </div>
            <div className="h-2 bg-[#F3F4F6] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${kycCompletion}%`,
                  backgroundColor: kycColor,
                }}
              />
            </div>
          </div>
        </Card>

        {/* Onglets */}
        <div className="flex gap-1 bg-[#F3F4F6] p-1 rounded-xl w-fit overflow-x-auto">
          {TABS.map(({ id: tid, label, icon: Icon }) => (
            <button
              key={tid}
              onClick={() => setTab(tid)}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all",
                tab === tid
                  ? "bg-white text-[#1E3A8A] shadow-sm"
                  : "text-[#6B7280] hover:text-[#111827]",
              )}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>

        {/* ── Bannières d'alerte ─────────────────────────────────────── */}
        {isPep && (
          <div className="flex items-start gap-3 px-4 py-3 bg-[#FEF2F2] border border-[#FECACA] rounded-xl">
            <AlertTriangle className="w-4 h-4 text-[#DC2626] mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold text-[#DC2626]">
                Personne Exposée Politiquement — Vigilance maximale
              </p>
              {client.prochaine_revision_kyc && (
                <p className="text-xs text-[#9CA3AF] mt-1">
                  Prochaine révision KYC obligatoire :{" "}
                  <span className="font-semibold text-[#DC2626]">
                    {formatDate(client.prochaine_revision_kyc)}
                  </span>
                  {" "}(GIABA — révision semestrielle)
                </p>
              )}
            </div>
          </div>
        )}

        {alerts.some(a => a.type_alerte === "SEUIL_DEPASSE" && a.statut === "OPEN") && (
          <div className="flex items-start gap-3 px-4 py-3 bg-[#FFFBEB] border border-[#FDE68A] rounded-xl">
            <TrendingUp className="w-4 h-4 text-[#D97706] mt-0.5 flex-shrink-0" />
            <p className="text-sm font-medium text-[#D97706]">
              Seuil monétaire dépassé sur les 30 derniers jours.
              Une déclaration à la CENTIF peut être requise (Art. 26, Loi 2006-14).
            </p>
          </div>
        )}

        {alerts.some(a => a.type_alerte === "BENEFICIAIRE_GROUPEMENT" && a.statut === "OPEN") && (
          <div className="flex items-start gap-3 px-4 py-3 bg-[#FEF2F2] border border-[#FECACA] rounded-xl">
            <AlertTriangle className="w-4 h-4 text-[#DC2626] mt-0.5 flex-shrink-0" />
            <p className="text-sm font-medium text-[#DC2626]">
              Transfert vers un bénéficiaire partagé avec d'autres clients détecté.
              Vérifier la cohérence des virements récents.
            </p>
          </div>
        )}

        {/* Contenu onglets */}
        {tab === "kyc" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <Card title="Identité">
              <InfoRow label="Nom complet" value={fullName} highlight />
              <InfoRow
                label="Date naissance"
                value={formatDate(client.date_naissance)}
              />
              <InfoRow label="Téléphone" value={client.phone} />
              <InfoRow label="Email" value={client.email} />
              <InfoRow
                label="Adhésion"
                value={formatDatetime(client.date_creation)}
              />
            </Card>

            <Card title="Profession & Revenus">
              <InfoRow
                label="Profession"
                value={client.profession_name}
                highlight
              />
              <InfoRow label="Code métier" value={client.profession_code} />
              <InfoRow
                label="Risque profession"
                value={client.profession_risk}
              />
              <InfoRow
                label="Revenus déclarés"
                value={formatAmount(client.revenus_declares)}
              />
              <InfoRow
                label="Zone géo."
                value={
                  client.city && client.region
                    ? `${client.city}, ${client.region}`
                    : client.zone_geo
                      ? `Zone #${client.zone_geo}`
                      : "—"
                }
              />
              <InfoRow
                label="Statut PEP"
                value={isPep ? "⚠ OUI — Vigilance maximale" : "Non"}
                danger={isPep}
              />
            </Card>

            {(client.accounts?.length > 0 || isComplianceOfficer) && (
              <Card
                title="Comptes bancaires"
                action={
                  isComplianceOfficer ? (
                    <Button
                      size="sm"
                      variant="primary"
                      onClick={() => setShowAccountModal(true)}
                    >
                      + Ajouter un compte
                    </Button>
                  ) : null
                }
              >
                {client.accounts?.length > 0 ? (
                  client.accounts.map((acc) => (
                    <div
                      key={acc.id}
                      className="flex items-center justify-between py-2.5 border-b border-[#F3F4F6] last:border-0"
                    >
                      <div>
                        <p className="text-sm font-medium">{acc.type_compte}</p>
                        <p className="text-xs text-[#9CA3AF] font-mono select-all cursor-pointer" title="Cliquer pour copier l'ID">
                          {acc.id}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold">
                          {formatAmount(acc.solde_moyen)}
                        </p>
                        <Badge
                          type={acc.status === "ACTIF" ? "FAIBLE" : "CLOSED"}
                        >
                          {acc.status}
                        </Badge>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="py-8 text-center text-sm text-[#6B7280]">
                    Aucun compte bancaire associé à ce client.
                  </div>
                )}
              </Card>
            )}

            {(client.documents?.length > 0 || isComplianceOfficer) && (
              <Card
                title="Documents KYC"
                action={
                  isComplianceOfficer ? (
                    <Button
                      size="sm"
                      variant="primary"
                      onClick={() => setShowDocModal(true)}
                    >
                      + Ajouter un document
                    </Button>
                  ) : null
                }
              >
                {client.documents?.length > 0 ? (
                  client.documents.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-start gap-3 py-2.5 border-b border-[#F3F4F6] last:border-0"
                    >
                      <FileCheck className="w-4 h-4 text-[#1E3A8A] mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="text-sm font-medium">{doc.type_doc}</p>
                        <p className="text-xs text-[#9CA3AF]">
                          N° {doc.numero || "—"}
                        </p>
                        <p className="text-xs text-[#9CA3AF]">
                          Exp. : {formatDate(doc.date_expiration)}
                        </p>
                      </div>
                      <Badge type={doc.valide ? "FAIBLE" : "ÉLEVÉ"}>
                        {doc.valide ? "Valide" : "Invalide"}
                      </Badge>
                    </div>
                  ))
                ) : (
                  <div className="py-8 text-center text-sm text-[#6B7280]">
                    Aucun document KYC enregistré pour ce client.
                  </div>
                )}
              </Card>
            )}
          </div>
        )}

        {tab === "scoring" && (
          <div className="space-y-5">
            {currentScore ? (
              <ScorePanel
                score={currentScoreDetail?.global_score ?? currentScore.global_score}
                riskCategory={currentScoreDetail?.risk_category ?? currentScore.risk_category}
                detailJson={currentScoreDetail?.detail_json}
                scoredAt={currentScoreDetail?.scored_at ?? currentScore.scored_at}
                scoredBy={currentScoreDetail?.scored_by ?? currentScore.scored_by}
              />
            ) : (
              <Card>
                <div className="text-center py-10">
                  <RefreshCw className="w-10 h-10 text-[#E5E7EB] mx-auto mb-3" />
                  <p className="text-sm text-[#9CA3AF] mb-3">
                    Aucun score calculé
                  </p>
                  <Button onClick={handleRescore} loading={rescoring}>
                    <RefreshCw className="w-4 h-4" /> Calculer le score
                  </Button>
                </div>
              </Card>
            )}
            <Card title="Historique des scores" noPad>
              <Table
                columns={scoreCols}
                data={scores}
                emptyText="Aucun historique disponible"
              />
            </Card>
          </div>
        )}

        {tab === "transactions" && (
          <div className="space-y-5">
            <Card
              title="Transactions récentes"
              action={
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => setShowTxModal(true)}
                  disabled={!client?.accounts?.length}
                >
                  + Ajouter une transaction
                </Button>
              }
              noPad
            >
              <Table
                columns={txCols}
                data={transactions}
                emptyText="Aucune transaction récente pour ce client"
              />
            </Card>
          </div>
        )}

        {tab === "alerts" && (
          <Card title="Alertes du client" noPad>
            <Table
              columns={alertCols}
              data={alerts}
              emptyText="Aucune alerte pour ce client"
            />
          </Card>
        )}
      </div>

      {/* Modal d'ajout de transaction */}
      <Modal
        open={showTxModal}
        onClose={() => setShowTxModal(false)}
        title="Ajouter une transaction"
        size="md"
      >
        <form onSubmit={handleAddTransaction} className="space-y-4">
          <div className="bg-[#F9FAFB] border border-[#E5E7EB] rounded-lg px-4 py-3 text-sm">
            {txForm.type_op === "DEPOT" && (
              <p>Argent déposé sur le compte. Vous pouvez indiquer la source des fonds (optionnel).</p>
            )}
            {txForm.type_op === "RETRAIT" && (
              <p>Argent retiré du compte courant.</p>
            )}
            {txForm.type_op === "VIREMENT" && (
              <p>Argent transféré depuis un compte courant ou épargne. Indiquez le destinataire et le pays de destination.</p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormSelect
              label="Type d'opération"
              required
              value={txForm.type_op}
              onChange={(e) =>
                setTxForm({
                  ...txForm,
                  type_op: e.target.value,
                  compte_id: "",
                  canal: getCanalOptionsForOp(e.target.value)[0],
                  origine: "",
                  destination: "",
                  origine_pays_id: "",
                  destination_pays_id: "",
                })
              }
            >
              <option value="DEPOT">DÉPÔT — Argent entrant</option>
              <option value="RETRAIT">RETRAIT — Argent sortant</option>
              <option value="VIREMENT">VIREMENT — Transfert</option>
            </FormSelect>

            <FormSelect
              label="Canal"
              required
              value={txForm.canal}
              onChange={(e) => setTxForm({ ...txForm, canal: e.target.value })}
            >
              {getCanalOptionsForOp(txForm.type_op).map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </FormSelect>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormInput
              label="Montant"
              type="number"
              required
              placeholder="Montant de l'opération en XOF"
              value={txForm.montant}
              onChange={(e) => setTxForm({ ...txForm, montant: e.target.value })}
              error={txErrors.montant}
            />
            <FormSelect
              label="Compte"
              required
              value={txForm.compte_id}
              onChange={(e) => setTxForm({ ...txForm, compte_id: e.target.value })}
              error={txErrors.compte_id}
              disabled={!filteredAccounts.length}
            >
              {filteredAccounts.length === 1 ? (
                <option value={filteredAccounts[0].id}>
                  {filteredAccounts[0].type_compte} — {formatAmount(filteredAccounts[0].solde_moyen)}
                </option>
              ) : (
                <>
                  <option value="">— Sélectionner un compte —</option>
                  {filteredAccounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.type_compte} — {formatAmount(acc.solde_moyen)} · {acc.status}
                    </option>
                  ))}
                </>
              )}
            </FormSelect>
            <div className="flex items-end">
              <div className="w-full px-4 py-2.5 bg-[#F9FAFB] border border-[#E5E7EB] rounded-lg text-sm text-[#6B7280]">
                Devise : <strong>XOF</strong>
              </div>
            </div>
          </div>

          {/* DEPOT : Origine (optionnel) */}
          {txForm.type_op === "DEPOT" && (
            <div className="space-y-4">
              <FormInput
                label="Origine — Source des fonds"
                placeholder="Ex: salaire, vente, aide familiale"
                value={txForm.origine || ""}
                onChange={(e) => setTxForm({ ...txForm, origine: e.target.value })}
                error={txErrors.origine}
              />
            </div>
          )}

          {/* VIREMENT : Destination */}
          {txForm.type_op === "VIREMENT" && (
            <div className="space-y-4">
              <FormInput
                label="Destination — Qui reçoit l'argent ?"
                required
                placeholder="Ex: Koffi Assogba – Ecobank Togo"
                value={txForm.destination || ""}
                onChange={(e) => setTxForm({ ...txForm, destination: e.target.value })}
                error={txErrors.destination}
              />
              <FormSelect
                label="Pays de destination — Où va l'argent ?"
                required
                value={txForm.destination_pays_id}
                onChange={(e) => setTxForm({ ...txForm, destination_pays_id: e.target.value })}
                error={txErrors.destination_pays_id}
              >
                <option value="">— Sélectionner un pays —</option>
                {countries.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.code_iso})
                  </option>
                ))}
              </FormSelect>
              {selectedDestinationCountry && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-[#F9FAFB] rounded-lg border border-[#E5E7EB] text-xs">
                  <span className="text-[#6B7280]">Risque pays :</span>
                  <span className={clsx(
                    "font-bold",
                    selectedDestinationCountry.is_fatf
                      ? "text-[#DC2626]"
                      : selectedDestinationCountry.is_border
                        ? "text-[#D97706]"
                        : "text-[#059669]",
                  )}>
                    {selectedDestinationCountry.is_fatf
                      ? "ÉLEVÉ (Liste FATF)"
                      : selectedDestinationCountry.is_border
                        ? "MOYEN (Pays frontalier)"
                        : "FAIBLE (Zone UEMOA)"}
                  </span>
                </div>
              )}
            </div>
          )}

          <ModalFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setShowTxModal(false)}
              disabled={submittingTx}
            >
              Annuler
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={submittingTx}
            >
              Ajouter la transaction
            </Button>
          </ModalFooter>
        </form>
      </Modal>

      {/* Modal d'ajout de compte bancaire */}
      <Modal
        open={showAccountModal}
        onClose={() => setShowAccountModal(false)}
        title="Ajouter un compte bancaire"
        size="md"
      >
        <form onSubmit={handleAddAccount} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormSelect
              label="Type de compte"
              required
              value={accountForm.type_compte}
              onChange={(e) => setAccountForm({ ...accountForm, type_compte: e.target.value })}
              error={accountErrors.type_compte}
            >
              {TYPES_COMPTE.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </FormSelect>

            <FormSelect
              label="Statut"
              required
              value={accountForm.status}
              onChange={(e) => setAccountForm({ ...accountForm, status: e.target.value })}
              error={accountErrors.status}
            >
              {STATUTS_COMPTE.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </FormSelect>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormInput
              label="Solde moyen (XOF)"
              type="number"
              required
              placeholder="Montant moyen sur le compte (information, pas utilisé dans le scoring)"
              value={accountForm.solde_moyen}
              onChange={(e) => setAccountForm({ ...accountForm, solde_moyen: e.target.value })}
              error={accountErrors.solde_moyen}
            />
            <FormInput
              label="Date d'ouverture"
              type="date"
              value={accountForm.date_ouverture}
              onChange={(e) => setAccountForm({ ...accountForm, date_ouverture: e.target.value })}
            />
          </div>

          <ModalFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setShowAccountModal(false)}
              disabled={submittingAccount}
            >
              Annuler
            </Button>
            <Button type="submit" variant="primary" loading={submittingAccount}>
              Ajouter le compte
            </Button>
          </ModalFooter>
        </form>
      </Modal>

      {/* Modal d'ajout de document KYC */}
      <Modal
        open={showDocModal}
        onClose={() => setShowDocModal(false)}
        title="Ajouter un document KYC"
        size="md"
      >
        <form onSubmit={handleAddDocument} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormSelect
              label="Type de document"
              required
              value={docForm.type_doc}
              onChange={(e) => setDocForm({ ...docForm, type_doc: e.target.value })}
              error={docErrors.type_doc}
            >
              {TYPES_DOC.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </FormSelect>
            <FormInput
              label="Numéro du document"
              value={docForm.numero}
              onChange={(e) => setDocForm({ ...docForm, numero: e.target.value })}
            />
          </div>

          <FormInput
            label="Date d'expiration"
            type="date"
            value={docForm.date_expiration}
            onChange={(e) => setDocForm({ ...docForm, date_expiration: e.target.value })}
          />

          <ModalFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setShowDocModal(false)}
              disabled={submittingDoc}
            >
              Annuler
            </Button>
            <Button type="submit" variant="primary" loading={submittingDoc}>
              Ajouter le document
            </Button>
          </ModalFooter>
        </form>
      </Modal>
    </Layout>
  );
}
