// src/components/Loader.jsx
import { clsx } from "clsx";
import { Loader2 } from "lucide-react";

/**
 * @param {string}  text    - Texte affiché sous le spinner
 * @param {boolean} full    - Plein écran (centré verticalement)
 * @param {'sm'|'md'|'lg'} size
 */
export function Loader({ text = "Chargement…", full = false, size = "md" }) {
  const iconSize =
    { sm: "w-5 h-5", md: "w-8 h-8", lg: "w-12 h-12" }[size] || "w-8 h-8";

  if (full) {
    return (
      <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#F9FAFB]">
        <Loader2
          className={clsx(iconSize, "animate-spin text-[#1E3A8A] mb-3")}
        />
        <p className="text-sm text-[#6B7280] font-medium">{text}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3">
      <Loader2 className={clsx(iconSize, "animate-spin text-[#1E3A8A]")} />
      {text && <p className="text-sm text-[#6B7280]">{text}</p>}
    </div>
  );
}

/**
 * Spinner inline (sans texte, pour les boutons ou petits espaces)
 */
export function InlineLoader({ className }) {
  return (
    <Loader2
      className={clsx("w-4 h-4 animate-spin text-[#1E3A8A]", className)}
    />
  );
}
