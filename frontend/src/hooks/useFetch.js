// src/hooks/useFetch.js
// Hook générique pour les appels API avec état loading/error/data
import { useState, useEffect, useCallback, useRef } from "react";

/**
 * @param {function} fetchFn - Fonction async retournant la donnée
 * @param {any[]} deps       - Dépendances (comme useEffect)
 * @returns {{ data, loading, error, refetch }}
 */
export function useFetch(fetchFn, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);
  const abortRef = useRef(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, []);

  const run = useCallback(async () => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    try {
      const result = await fetchFn({ signal: controller.signal });
      if (mountedRef.current) setData(result);
    } catch (err) {
      if (err?.name === "AbortError") return;
      if (mountedRef.current) setError(err);
    } finally {
      if (mountedRef.current && abortRef.current === controller) {
        setLoading(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
  }, [run]);

  return { data, loading, error, refetch: run };
}
