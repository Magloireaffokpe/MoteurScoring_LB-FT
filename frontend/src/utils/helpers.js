// src/utils/helpers.js
import { COLORS } from "../theme/colors";

/**
 * Retourne la couleur hex selon le score (0-100)
 * Utilisé dans ScorePanel, ClientsListPage
 */
export function scoreColor(score) {
  if (score >= 67) return COLORS.danger.DEFAULT; // ÉLEVÉ
  if (score >= 34) return COLORS.accent.DEFAULT; // MOYEN
  return COLORS.secondary.DEFAULT; // FAIBLE
}

/**
 * Retourne la catégorie selon le score
 * Cohérent avec seed_db.py → seed_risk_thresholds()
 */
export function scoreToCategory(score) {
  if (score >= 67) return "ÉLEVÉ";
  if (score >= 34) return "MOYEN";
  return "FAIBLE";
}

/**
 * Retourne la classe CSS de badge selon la catégorie
 */
export function categoryBadgeClass(cat) {
  const c = (cat || "").toUpperCase();
  if (c.includes("LEV")) return "badge-eleve";
  if (c === "MOYEN") return "badge-moyen";
  return "badge-faible";
}

/**
 * Retourne la classe CSS badge pour le risk_level d'une alerte
 */
export function riskLevelBadgeClass(level) {
  const map = {
    HIGH: "badge-eleve",
    MEDIUM: "badge-moyen",
    LOW: "badge-faible",
  };
  return map[(level || "").toUpperCase()] || "badge-faible";
}

/**
 * Retourne la classe CSS badge pour le risk_level d'une zone
 * Synchronisé avec RiskZone.risk_level du backend
 */
export function zoneBadgeClass(risk_level) {
  const map = {
    FAIBLE: "badge-faible",
    MOYEN: "badge-moyen",
    ELEVE: "badge-eleve",
    TRES_ELEVE: "badge-eleve",
  };
  return map[(risk_level || "").toUpperCase()] || "badge-faible";
}

/**
 * Télécharge un Blob en tant que fichier
 */
export function downloadBlob(data, filename, mimeType) {
  const url = URL.createObjectURL(new Blob([data], { type: mimeType }));
  const a = Object.assign(document.createElement("a"), {
    href: url,
    download: filename,
  });
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Debounce une fonction (utilisé pour la recherche)
 */
export function debounce(fn, delay = 400) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Truncate un UUID pour l'affichage
 */
export function truncateUUID(uuid, length = 8) {
  if (!uuid) return "—";
  return uuid.slice(0, length) + "…";
}
