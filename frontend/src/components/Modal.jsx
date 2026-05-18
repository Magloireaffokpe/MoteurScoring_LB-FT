// src/components/Modal.jsx
import { useEffect } from "react";
import { clsx } from "clsx";
import { X } from "lucide-react";

const SIZES = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
  xl: "max-w-4xl",
};

/**
 * @param {boolean}  open    - Affiche ou cache le modal
 * @param {function} onClose - Callback de fermeture
 * @param {string}   title   - Titre dans l'en-tête
 * @param {'sm'|'md'|'lg'|'xl'} size
 */
export function Modal({
  open,
  onClose,
  title,
  children,
  size = "md",
  className,
}) {
  // Bloquer le scroll body quand le modal est ouvert
  useEffect(() => {
    if (open) document.body.style.overflow = "hidden";
    else document.body.style.overflow = "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  // Fermeture avec Echap
  useEffect(() => {
    const handler = (e) => {
      if (e.key === "Escape" && open) onClose?.();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panneau */}
      <div
        className={clsx(
          "relative bg-white rounded-2xl shadow-2xl w-full",
          "animate-[slideUp_0.25s_ease-out]",
          SIZES[size] || SIZES.md,
          className,
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E5E7EB]">
          <h2 className="text-base font-semibold text-[#111827]">{title}</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#9CA3AF] hover:text-[#111827] hover:bg-[#F3F4F6] transition-colors"
            aria-label="Fermer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Contenu */}
        <div className="px-6 py-5 overflow-y-auto max-h-[80vh]">{children}</div>
      </div>
    </div>
  );
}

/**
 * Pied de modal avec boutons d'action standardisés
 */
export function ModalFooter({ children }) {
  return (
    <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#E5E7EB] mt-4">
      {children}
    </div>
  );
}
