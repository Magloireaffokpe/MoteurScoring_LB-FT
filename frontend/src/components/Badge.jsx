// src/components/Badge.jsx
import { clsx } from "clsx";

const BADGE_CLASSES = {
  // Catégories de risque (score)
  FAIBLE: "badge bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]",
  MOYEN: "badge bg-[#FFFBEB] text-[#D97706] border border-[#FDE68A]",
  ÉLEVÉ: "badge bg-[#FEF2F2] text-[#DC2626] border border-[#FECACA]",
  ELEVE: "badge bg-[#FEF2F2] text-[#DC2626] border border-[#FECACA]",
  // Statuts alerte
  OPEN: "badge bg-[#FEF2F2] text-[#DC2626] border border-[#FECACA]",
  UNDER_REVIEW: "badge bg-[#FFFBEB] text-[#D97706] border border-[#FDE68A]",
  CLOSED: "badge bg-[#F3F4F6] text-[#6B7280] border border-[#E5E7EB]",
  // KYC levels
  LOW: "badge bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]",
  MEDIUM: "badge bg-[#FFFBEB] text-[#D97706] border border-[#FDE68A]",
  HIGH: "badge bg-[#FEF2F2] text-[#DC2626] border border-[#FECACA]",
  // PEP
  PEP: "badge bg-[#EEF2FF] text-[#1E3A8A] border border-[#C7D2FE]",
  // Statuts client
  ACTIVE: "badge bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]",
  INACTIVE: "badge bg-[#F3F4F6] text-[#6B7280] border border-[#E5E7EB]",
  SUSPENDED: "badge bg-[#FEF2F2] text-[#DC2626] border border-[#FECACA]",
};

/**
 * @param {string} type  - Clé de style (FAIBLE, MOYEN, ÉLEVÉ, OPEN, PEP, etc.)
 * @param {string} className - Classes supplémentaires
 */
export function Badge({ type, children, className }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold font-sans",
        BADGE_CLASSES[type] ||
          "badge bg-gray-100 text-gray-600 border border-gray-200",
        className,
      )}
    >
      {children}
    </span>
  );
}
