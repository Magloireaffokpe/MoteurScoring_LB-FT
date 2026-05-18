// src/hooks/usePagination.js
import { useState, useCallback } from "react";

/**
 * @param {number} pageSize - Nombre d'items par page (défaut 25)
 * @returns {{ page, pageSize, skip, setPage, reset, paginationProps }}
 */
export function usePagination(pageSize = 25) {
  const [page, setPage] = useState(1);

  const skip = (page - 1) * pageSize;

  const reset = useCallback(() => setPage(1), []);

  // Props prêtes à passer au composant <Pagination>
  const paginationProps = useCallback(
    (total) => ({
      total,
      page,
      pageSize,
      onChange: setPage,
    }),
    [page, pageSize],
  );

  return { page, pageSize, skip, setPage, reset, paginationProps };
}
