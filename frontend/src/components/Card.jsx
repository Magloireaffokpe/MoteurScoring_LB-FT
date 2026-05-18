// src/components/Card.jsx
import { clsx } from "clsx";

/**
 * @param {string} title    - Titre optionnel de la card
 * @param {ReactNode} action - Élément action (bouton, lien) en haut à droite
 * @param {boolean} noPad   - Désactive le padding interne (pour les tableaux)
 * @param {string} className - Classes supplémentaires
 */
export function Card({ title, action, children, className, noPad = false }) {
  return (
    <div
      className={clsx(
        "bg-white rounded-xl border border-[#E5E7EB] shadow-sm overflow-hidden",
        !noPad && "p-5",
        className,
      )}
    >
      {(title || action) && (
        <div
          className={clsx(
            "flex items-center justify-between",
            !noPad ? "mb-4" : "px-5 py-3 border-b border-[#E5E7EB]",
          )}
        >
          {title && (
            <h3 className="text-xl font-semibold text-[#111827] font-display">
              {title}
            </h3>
          )}
          {action && <div>{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
}
