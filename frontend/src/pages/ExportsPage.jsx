// src/pages/ExportsPage.jsx
import { useState, useEffect } from "react";
import { FileText, Download, AlertTriangle, Loader2 } from "lucide-react";

import { Layout } from "../components/Layout";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { exportService } from "../services/exportService";
import { customerService } from "../services/customerService";
import { alertService } from "../services/alertService";

import toast from "react-hot-toast";

export default function ExportsPage() {
  const [customerId, setCustomerId] = useState("");
  const [alertId, setAlertId] = useState("");
  const [days, setDays] = useState(90);
  const [loading, setLoading] = useState(null);

  // States pour l'autocomplétion des clients
  const [allClients, setAllClients] = useState([]);
  const [clientSearch, setClientSearch] = useState("");
  const [selectedClient, setSelectedClient] = useState(null);
  const [showClientDropdown, setShowClientDropdown] = useState(false);

  // States pour l'autocomplétion des alertes
  const [allAlerts, setAllAlerts] = useState([]);
  const [alertSearch, setAlertSearch] = useState("");
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [showAlertDropdown, setShowAlertDropdown] = useState(false);

  const [loadingSearchData, setLoadingSearchData] = useState(true);

  // Charger les données d'autocomplétion sur le mount
  useEffect(() => {
    Promise.all([
      customerService.list({ limit: 1000 }).catch(() => ({ items: [] })),
      alertService.list({ limit: 1000 }).catch(() => ({ items: [] })),
    ])
      .then(([clientsRes, alertsRes]) => {
        setAllClients(clientsRes.items || []);
        setAllAlerts(alertsRes.items || []);
      })
      .catch(() => {})
      .finally(() => setLoadingSearchData(false));
  }, []);

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

  // Filtrer les clients par nom, prénom ou UUID
  const filteredClients = clientSearch.trim()
    ? allClients.filter(
        (c) =>
          `${c.prenom} ${c.nom}`
            .toLowerCase()
            .includes(clientSearch.toLowerCase()) ||
          c.id.toLowerCase().includes(clientSearch.toLowerCase()),
      )
    : allClients.slice(0, 5); // Affiche les 5 premiers par défaut si vide

  // Générer un label lisible pour l'alerte
  const getAlertLabel = (alert) => {
    const client = allClients.find((c) => c.id === alert.client_id);
    const clientName = client
      ? `${client.prenom} ${client.nom}`
      : `Client : ${alert.client_id.slice(0, 8)}…`;
    return `${alert.type_alerte} — ${clientName} (${alert.statut})`;
  };

  // Filtrer les alertes par type, nom de client ou UUID
  const filteredAlerts = alertSearch.trim()
    ? allAlerts.filter((a) => {
        const label = getAlertLabel(a);
        return (
          label.toLowerCase().includes(alertSearch.toLowerCase()) ||
          a.id.toLowerCase().includes(alertSearch.toLowerCase())
        );
      })
    : allAlerts.slice(0, 5); // Affiche les 5 premières par défaut si vide

  const handleBlur = (setter) => {
    setTimeout(() => setter(false), 200);
  };

  const EXPORTS = [
    {
      key: "pdf",
      icon: FileText,
      color: "bg-[#EEF2FF] text-[#1E3A8A]",
      title: "Fiche client — PDF",
      desc: "Rapport complet LBC/FT (3 pages) : identité KYC, score, contributions C1–C6, alertes, conformité CENTIF.",
      content: (
        <div className="relative space-y-2">
          <label className="text-xs font-semibold text-[#374151] block mb-1">
            Rechercher un client (Nom, Prénom ou UUID)
          </label>
          <div className="relative">
            <input
              type="text"
              className="w-full px-3.5 py-2.5 rounded-xl border border-[#E5E7EB] text-xs bg-white
                         focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]/30 focus:border-[#1E3A8A] font-sans"
              placeholder="Saisissez un nom, prénom ou collez un UUID..."
              value={clientSearch}
              onFocus={() => setShowClientDropdown(true)}
              onBlur={() => handleBlur(setShowClientDropdown)}
              onChange={(e) => {
                setClientSearch(e.target.value);
                setCustomerId("");
                setSelectedClient(null);
                setShowClientDropdown(true);
              }}
            />
            {selectedClient && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold px-2 py-0.5 bg-green-50 text-green-700 rounded-full border border-green-200">
                Sélectionné
              </span>
            )}
          </div>
          {showClientDropdown && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-[#E5E7EB] rounded-xl shadow-lg max-h-60 overflow-y-auto font-sans">
              {filteredClients.length > 0 ? (
                filteredClients.map((c) => (
                  <div
                    key={c.id}
                    className="px-4 py-2.5 hover:bg-[#F3F4F6] cursor-pointer text-xs flex items-center justify-between border-b border-[#F3F4F6] last:border-b-0"
                    onMouseDown={() => {
                      setSelectedClient(c);
                      setCustomerId(c.id);
                      setClientSearch(`${c.prenom} ${c.nom}`);
                      setShowClientDropdown(false);
                    }}
                  >
                    <div>
                      <div className="font-semibold text-[#111827]">
                        {c.prenom} {c.nom}
                      </div>
                      <div className="text-[10px] text-[#9CA3AF] font-mono mt-0.5">
                        UUID: {c.id}
                      </div>
                    </div>
                    {c.kyc_level && (
                      <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-gray-100 text-gray-800">
                        {c.kyc_level}
                      </span>
                    )}
                  </div>
                ))
              ) : (
                <div className="px-4 py-3 text-xs text-[#9CA3AF] text-center">
                  Aucun client trouvé pour "{clientSearch}"
                </div>
              )}
            </div>
          )}
          {selectedClient && (
            <div className="text-[11px] text-[#4B5563] bg-[#F9FAFB] p-2.5 rounded-lg border border-[#E5E7EB] mt-2">
              <span className="font-semibold">Client sélectionné :</span>{" "}
              {selectedClient.prenom} {selectedClient.nom} <br />
              <span className="font-mono text-[9px] text-[#9CA3AF]">
                UUID : {selectedClient.id}
              </span>
            </div>
          )}
        </div>
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
      desc: "Export des transactions client (séparateur « ; », UTF-8, colonnes de métadonnées et de transactions, compatible Excel).",
      content: (
        <div className="space-y-3">
          <div className="relative space-y-2">
            <label className="text-xs font-semibold text-[#374151] block mb-1">
              Rechercher un client (Nom, Prénom ou UUID)
            </label>
            <div className="relative">
              <input
                type="text"
                className="w-full px-3.5 py-2.5 rounded-xl border border-[#E5E7EB] text-xs bg-white
                           focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]/30 focus:border-[#1E3A8A] font-sans"
                placeholder="Saisissez un nom, prénom ou collez un UUID..."
                value={clientSearch}
                onFocus={() => setShowClientDropdown(true)}
                onBlur={() => handleBlur(setShowClientDropdown)}
                onChange={(e) => {
                  setClientSearch(e.target.value);
                  setCustomerId("");
                  setSelectedClient(null);
                  setShowClientDropdown(true);
                }}
              />
              {selectedClient && (
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold px-2 py-0.5 bg-green-50 text-green-700 rounded-full border border-green-200">
                  Sélectionné
                </span>
              )}
            </div>
            {showClientDropdown && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-[#E5E7EB] rounded-xl shadow-lg max-h-60 overflow-y-auto font-sans">
                {filteredClients.length > 0 ? (
                  filteredClients.map((c) => (
                    <div
                      key={c.id}
                      className="px-4 py-2.5 hover:bg-[#F3F4F6] cursor-pointer text-xs flex items-center justify-between border-b border-[#F3F4F6] last:border-b-0"
                      onMouseDown={() => {
                        setSelectedClient(c);
                        setCustomerId(c.id);
                        setClientSearch(`${c.prenom} ${c.nom}`);
                        setShowClientDropdown(false);
                      }}
                    >
                      <div>
                        <div className="font-semibold text-[#111827]">
                          {c.prenom} {c.nom}
                        </div>
                        <div className="text-[10px] text-[#9CA3AF] font-mono mt-0.5">
                          UUID: {c.id}
                        </div>
                      </div>
                      {c.kyc_level && (
                        <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-gray-100 text-gray-800">
                          {c.kyc_level}
                        </span>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="px-4 py-3 text-xs text-[#9CA3AF] text-center">
                    Aucun client trouvé pour "{clientSearch}"
                  </div>
                )}
              </div>
            )}
            {selectedClient && (
              <div className="text-[11px] text-[#4B5563] bg-[#F9FAFB] p-2.5 rounded-lg border border-[#E5E7EB] mt-2">
                <span className="font-semibold">Client sélectionné :</span>{" "}
                {selectedClient.prenom} {selectedClient.nom} <br />
                <span className="font-mono text-[9px] text-[#9CA3AF]">
                  UUID : {selectedClient.id}
                </span>
              </div>
            )}
          </div>
          <div>
            <label className="text-xs font-semibold text-[#374151] block mb-1.5">
              Fenêtre temporelle :{" "}
              <span className="text-[#10B981] font-bold">{days} jours</span>
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
              <span className="text-[11px] text-[#4B5563] font-sans font-medium w-16 text-right">
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
        <div className="relative space-y-2">
          <label className="text-xs font-semibold text-[#374151] block mb-1">
            Rechercher une alerte (Client, Type ou UUID)
          </label>
          <div className="relative">
            <input
              type="text"
              className="w-full px-3.5 py-2.5 rounded-xl border border-[#E5E7EB] text-xs bg-white
                         focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]/30 focus:border-[#1E3A8A] font-sans"
              placeholder="Saisissez le type d'alerte, nom client ou collez l'UUID..."
              value={alertSearch}
              onFocus={() => setShowAlertDropdown(true)}
              onBlur={() => handleBlur(setShowAlertDropdown)}
              onChange={(e) => {
                setAlertSearch(e.target.value);
                setAlertId("");
                setSelectedAlert(null);
                setShowAlertDropdown(true);
              }}
            />
            {selectedAlert && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold px-2 py-0.5 bg-green-50 text-green-700 rounded-full border border-green-200">
                Sélectionné
              </span>
            )}
          </div>
          {showAlertDropdown && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-[#E5E7EB] rounded-xl shadow-lg max-h-60 overflow-y-auto font-sans">
              {filteredAlerts.length > 0 ? (
                filteredAlerts.map((a) => {
                  const client = allClients.find((c) => c.id === a.client_id);
                  const clientName = client
                    ? `${client.prenom} ${client.nom}`
                    : "Client inconnu";
                  return (
                    <div
                      key={a.id}
                      className="px-4 py-2.5 hover:bg-[#F3F4F6] cursor-pointer text-xs flex items-center justify-between border-b border-[#F3F4F6] last:border-b-0"
                      onMouseDown={() => {
                        setSelectedAlert(a);
                        setAlertId(a.id);
                        setAlertSearch(`${a.type_alerte} — ${clientName}`);
                        setShowAlertDropdown(false);
                      }}
                    >
                      <div>
                        <div className="font-semibold text-[#111827]">
                          {a.type_alerte}
                        </div>
                        <div className="text-[10px] text-[#4B5563] mt-0.5">
                          Client: {clientName}
                        </div>
                        <div className="text-[10px] text-[#9CA3AF] font-mono mt-0.5">
                          UUID: {a.id}
                        </div>
                      </div>
                      <span
                        className={`text-[9px] font-bold px-2 py-0.5 rounded ${
                          a.statut === "OPEN"
                            ? "bg-red-50 text-red-700"
                            : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {a.statut}
                      </span>
                    </div>
                  );
                })
              ) : (
                <div className="px-4 py-3 text-xs text-[#9CA3AF] text-center">
                  Aucune alerte trouvée pour "{alertSearch}"
                </div>
              )}
            </div>
          )}
          {selectedAlert && (
            <div className="text-[11px] text-[#4B5563] bg-[#F9FAFB] p-2.5 rounded-lg border border-[#E5E7EB] mt-2">
              <span className="font-semibold">Alerte sélectionnée :</span>{" "}
              {selectedAlert.type_alerte} <br />
              <span className="font-mono text-[9px] text-[#9CA3AF]">
                UUID : {selectedAlert.id}
              </span>
            </div>
          )}
        </div>
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

        {loadingSearchData ? (
          <Card>
            <div className="flex flex-col items-center justify-center py-10 space-y-3 font-sans">
              <Loader2 className="w-8 h-8 text-[#1E3A8A] animate-spin" />
              <span className="text-xs text-[#6B7280]">
                Chargement des référentiels de recherche...
              </span>
            </div>
          </Card>
        ) : (
          EXPORTS.map(
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
                    <h3 className="font-display font-semibold text-lg text-[#111827] mb-1">
                      {title}
                    </h3>
                    <p className="text-xs font-normal font-sans text-[#4B5563] mb-4 leading-relaxed">
                      {desc}
                    </p>
                    {content}
                    <Button
                      className="mt-4"
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
          )
        )}
      </div>
    </Layout>
  );
}
