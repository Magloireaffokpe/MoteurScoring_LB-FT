import { clsx } from "clsx";
import { useId } from "react";

const BASE_INPUT = [
  "w-full px-3 py-2.5 rounded-xl border bg-white text-sm",
  "text-[#111827] placeholder-[#9CA3AF]",
  "focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]/30 focus:border-[#1E3A8A]",
  "transition-all duration-200",
].join(" ");

const ERROR_INPUT =
  "border-[#EF4444] focus:ring-[#EF4444]/30 focus:border-[#EF4444]";
const NORMAL_INPUT = "border-[#E5E7EB]";

/**
 * Champ de saisie texte générique
 * @param {string} label    - Label affiché au-dessus
 * @param {string} error    - Message d'erreur (affiche le champ en rouge)
 * @param {boolean} required
 * @param {string} helper   - Texte d'aide sous le champ
 */
export function FormInput({
  label,
  error,
  required,
  helper,
  className,
  id: propId,
  ...props
}) {
  const generatedId = useId();
  const id = propId || props.name || generatedId;

  return (
    <div className={clsx("flex flex-col gap-1 font-sans", className)}>
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-[#374151]">
          {label}
          {required && <span className="text-[#EF4444] ml-0.5">*</span>}
        </label>
      )}
      <input
        id={id}
        className={clsx(BASE_INPUT, "font-sans", error ? ERROR_INPUT : NORMAL_INPUT)}
        {...props}
      />
      {error && <p className="text-xs font-medium text-[#EF4444] mt-1">{error}</p>}
      {!error && helper && (
        <p className="text-xs font-normal text-[#6B7280] mt-0.5">{helper}</p>
      )}
    </div>
  );
}

/**
 * Sélecteur déroulant
 */
export function FormSelect({
  label,
  error,
  required,
  helper,
  className,
  children,
  id: propId,
  ...props
}) {
  const generatedId = useId();
  const id = propId || props.name || generatedId;

  return (
    <div className={clsx("flex flex-col gap-1 font-sans", className)}>
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-[#374151]">
          {label}
          {required && <span className="text-[#EF4444] ml-0.5">*</span>}
        </label>
      )}
      <select
        id={id}
        className={clsx(
          BASE_INPUT,
          "font-sans",
          error ? ERROR_INPUT : NORMAL_INPUT,
          "cursor-pointer",
        )}
        {...props}
      >
        {children}
      </select>
      {error && <p className="text-xs font-medium text-[#EF4444] mt-1">{error}</p>}
      {!error && helper && (
        <p className="text-xs font-normal text-[#6B7280] mt-0.5">{helper}</p>
      )}
    </div>
  );
}

/**
 * Textarea
 */
export function FormTextarea({
  label,
  error,
  required,
  helper,
  className,
  rows = 3,
  id: propId,
  ...props
}) {
  const generatedId = useId();
  const id = propId || props.name || generatedId;

  return (
    <div className={clsx("flex flex-col gap-1 font-sans", className)}>
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-[#374151]">
          {label}
          {required && <span className="text-[#EF4444] ml-0.5">*</span>}
        </label>
      )}
      <textarea
        id={id}
        rows={rows}
        className={clsx(
          BASE_INPUT,
          "font-sans",
          "resize-none",
          error ? ERROR_INPUT : NORMAL_INPUT,
        )}
        {...props}
      />
      {error && <p className="text-xs font-medium text-[#EF4444] mt-1">{error}</p>}
      {!error && helper && (
        <p className="text-xs font-normal text-[#6B7280] mt-0.5">{helper}</p>
      )}
    </div>
  );
}
