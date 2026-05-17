// src/components/Button.jsx
import { clsx } from "clsx";
import { Loader2 } from "lucide-react";

const VARIANTS = {
  primary:
    "bg-[#1E3A8A] hover:bg-[#2D4FA8] text-white shadow-sm active:scale-[.98]",
  secondary:
    "bg-[#10B981] hover:bg-[#34D399] text-white shadow-sm active:scale-[.98]",
  danger: "bg-[#EF4444] hover:bg-[#DC2626] text-white active:scale-[.98]",
  ghost:
    "bg-transparent hover:bg-[#F3F4F6] text-[#6B7280] border border-[#E5E7EB]",
  outline:
    "bg-transparent hover:bg-[#EEF2FF] text-[#1E3A8A] border border-[#1E3A8A]",
};

const SIZES = {
  sm: "px-3 py-1.5 text-xs rounded-lg",
  md: "px-4 py-2 text-sm rounded-xl",
  lg: "px-6 py-3 text-base rounded-xl",
};

/**
 * @param {'primary'|'secondary'|'danger'|'ghost'|'outline'} variant
 * @param {'sm'|'md'|'lg'} size
 * @param {boolean} loading
 * @param {boolean} fullWidth
 */
export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  fullWidth = false,
  children,
  className,
  disabled,
  ...props
}) {
  return (
    <button
      disabled={loading || disabled}
      className={clsx(
        "inline-flex items-center justify-center gap-2 font-semibold",
        "transition-all duration-200 cursor-pointer",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        VARIANTS[variant] || VARIANTS.primary,
        SIZES[size] || SIZES.md,
        fullWidth && "w-full",
        className,
      )}
      {...props}
    >
      {loading && <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />}
      {children}
    </button>
  );
}
