// src/utils/formatters.js
// Synchronisé avec les champs exacts du modèle Customer (backend Marcos)

/**
 * Formate une date ISO en DD/MM/YYYY
 * Utilisé pour : date_naissance, date_expiration, date_ouverture, date_calcul
 */
export function formatDate(d) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/**
 * Formate un datetime ISO en DD/MM/YYYY HH:MM
 * Utilisé pour : date_creation, scored_at, created_at, timestamp
 */
export function formatDatetime(d) {
  if (!d) return "—";
  return new Date(d).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Formate un montant en XOF (revenus_declares, montant, solde_moyen)
 */
export function formatAmount(n, devise = "XOF") {
  if (n == null || n === "") return "—";
  const formatted = new Intl.NumberFormat("fr-FR", {
    maximumFractionDigits: 0,
  }).format(Number(n));
  return `${formatted} ${devise}`;
}

/**
 * Formate un pourcentage (kyc_completion, contributions C1..C6)
 */
export function formatPct(n) {
  if (n == null) return "—";
  return `${Number(n).toFixed(1)} %`;
}

/**
 * Formate le nom complet d'un client
 * Champs backend : nom (majuscules), prenom
 */
export function formatName(customer) {
  if (!customer) return "—";
  const prenom = customer.prenom || "";
  const nom = customer.nom || "";
  return `${prenom} ${nom}`.trim() || "—";
}

/**
 * Normalise la catégorie de risque pour l'affichage
 * 'ELEVE' (base) → 'ÉLEVÉ' (API/UI)
 */
export function normalizeCategory(cat) {
  const map = {
    ELEVE: "ÉLEVÉ",
    ÉLEVÉ: "ÉLEVÉ",
    MOYEN: "MOYEN",
    FAIBLE: "FAIBLE",
  };
  return map[(cat || "").toUpperCase()] || cat || "—";
}

/**
 * Formate le statut PEP (Customer.statut_pep booléen)
 */
export function formatPep(statut_pep) {
  return statut_pep ? "PEP" : "Non PEP";
}

/**
 * Formate le niveau KYC (Customer.kyc_level : LOW/MEDIUM/HIGH)
 */
export function formatKycLevel(level) {
  const map = { LOW: "Faible", MEDIUM: "Moyen", HIGH: "Élevé" };
  return map[level] || level || "—";
}

/**
 * Formate le niveau de risque profession (Customer.profession_risk)
 */
export function formatProfessionRisk(risk) {
  const map = { LOW: "Faible", MEDIUM: "Moyen", HIGH: "Élevé" };
  return map[risk] || risk || "—";
}

/**
 * Formate le statut d'une alerte
 */
export function formatAlertStatus(status) {
  const map = { OPEN: "Ouvert", UNDER_REVIEW: "En cours", CLOSED: "Fermé" };
  return map[status] || status || "—";
}

/**
 * Formate le risk_level d'une alerte (HIGH/MEDIUM/LOW)
 */
export function formatRiskLevel(level) {
  const map = { HIGH: "Élevé", MEDIUM: "Moyen", LOW: "Faible" };
  return map[level] || level || "—";
}

/**
 * Extrait les initiales d'un nom pour l'avatar
 */
export function getInitials(name) {
  if (!name) return "?";
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}
