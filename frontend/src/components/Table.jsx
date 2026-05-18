// src/components/Table.jsx
import { clsx } from "clsx";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Loader } from "./Loader";

/**
 * Tableau de données réutilisable
 *
 * @param {Array<{key, label, render?, width?, align?}>} columns
 * @param {Array<object>} data
 * @param {boolean} loading
 * @param {string}  emptyText
 * @param {function} onRowClick - (row) => void
 */
export function Table({
  columns,
  data,
  loading,
  emptyText = "Aucune donnée",
  onRowClick,
}) {
  if (loading) return <Loader text="Chargement des données…" />;

  return (
    <div className="overflow-x-auto w-full">
      <table className="w-full text-sm min-w-[700px]">
        <thead>
          <tr className="bg-[#F9FAFB]">
            {columns.map((col) => (
              <th
                key={col.key}
                style={col.width ? { width: col.width } : {}}
                className={clsx(
                  "px-4 py-3 text-left text-xs font-semibold font-sans",
                  "text-[#6B7280] uppercase tracking-wider",
                  "border-b border-[#E5E7EB]",
                  col.align === "center" && "text-center",
                  col.align === "right" && "text-right",
                )}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {!data?.length ? (
            <tr>
              <td
                colSpan={columns.length}
                className="text-center py-12 text-[#9CA3AF] text-sm"
              >
                {emptyText}
              </td>
            </tr>
          ) : (
            data.map((row, i) => (
              <tr
                key={row.id || i}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={clsx(
                  "border-b border-[#E5E7EB]/60",
                  "hover:bg-[#F9FAFB] transition-colors duration-100",
                  onRowClick && "cursor-pointer",
                  i % 2 === 0 ? "bg-white" : "bg-[#FAFAFA]",
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={clsx(
                      "px-4 py-3 text-sm font-normal text-[#111827] font-sans",
                      col.align === "center" && "text-center",
                      col.align === "right" && "text-right",
                    )}
                  >
                    {col.render
                      ? col.render(row[col.key], row)
                      : (row[col.key] ?? "—")}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Composant de pagination autonome
 *
 * @param {number}   total    - Nombre total d'éléments
 * @param {number}   page     - Page courante (1-indexed)
 * @param {number}   pageSize - Éléments par page
 * @param {function} onChange - (newPage: number) => void
 */
export function Pagination({ total, page, pageSize, onChange }) {
  const totalPages = Math.ceil(total / pageSize);
  if (totalPages <= 1) return null;

  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  // Calcule les pages à afficher (fenêtre de 5)
  const start = Math.max(1, Math.min(page - 2, totalPages - 4));
  const pages = Array.from(
    { length: Math.min(5, totalPages) },
    (_, i) => start + i,
  );

  return (
    <div className="flex items-center justify-between pt-4 px-1">
      <p className="text-xs text-[#9CA3AF]">
        {from}–{to} sur{" "}
        <span className="font-semibold text-[#6B7280]">{total}</span>
      </p>

      <div className="flex items-center gap-1">
        <button
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          className="p-1.5 rounded-lg hover:bg-[#F3F4F6] disabled:opacity-40 transition-colors"
          aria-label="Page précédente"
        >
          <ChevronLeft className="w-4 h-4 text-[#6B7280]" />
        </button>

        {pages.map((p) => (
          <button
            key={p}
            onClick={() => onChange(p)}
            className={clsx(
              "w-8 h-8 rounded-lg text-xs font-semibold font-sans transition-colors",
              p === page
                ? "bg-[#1E3A8A] text-white"
                : "text-[#6B7280] hover:bg-[#F3F4F6]",
            )}
          >
            {p}
          </button>
        ))}

        <button
          onClick={() => onChange(page + 1)}
          disabled={page >= totalPages}
          className="p-1.5 rounded-lg hover:bg-[#F3F4F6] disabled:opacity-40 transition-colors"
          aria-label="Page suivante"
        >
          <ChevronRight className="w-4 h-4 text-[#6B7280]" />
        </button>
      </div>
    </div>
  );
}
