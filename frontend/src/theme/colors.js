// src/theme/colors.js
// Palette officielle RiskGuard — synchronisée avec tailwind.config.js

export const COLORS = {
  primary: {
    DEFAULT: "#1E3A8A",
    light: "#2D4FA8",
    dark: "#152D6E",
    50: "#EEF2FF",
  },
  secondary: {
    DEFAULT: "#10B981",
    light: "#34D399",
    dark: "#059669",
    50: "#ECFDF5",
  },
  accent: { DEFAULT: "#F59E0B", light: "#FCD34D", dark: "#D97706" },
  danger: {
    DEFAULT: "#EF4444",
    light: "#FCA5A5",
    dark: "#DC2626",
    50: "#FEF2F2",
  },
  navy: { DEFAULT: "#1B2A6B" },
  surface: { DEFAULT: "#FFFFFF", soft: "#F9FAFB", muted: "#F3F4F6" },
  border: { DEFAULT: "#E5E7EB", strong: "#D1D5DB" },
  text: { primary: "#111827", secondary: "#6B7280", muted: "#9CA3AF" },
};

// Couleur de score selon la valeur (0-100)
export function scoreColor(score) {
  if (score >= 67) return COLORS.danger.DEFAULT;
  if (score >= 34) return COLORS.accent.DEFAULT;
  return COLORS.secondary.DEFAULT;
}

// Couleur de fond de catégorie
export const CATEGORY_COLORS = {
  FAIBLE: { bg: "#ECFDF5", text: "#059669", border: "#A7F3D0" },
  MOYEN: { bg: "#FFFBEB", text: "#D97706", border: "#FDE68A" },
  ÉLEVÉ: { bg: "#FEF2F2", text: "#DC2626", border: "#FECACA" },
  ELEVE: { bg: "#FEF2F2", text: "#DC2626", border: "#FECACA" },
};
