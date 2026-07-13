import { useState, useEffect, useCallback } from "react";
import { workersApi } from "../api/workers";
import type { Worker } from "../types/worker";

export function useWorkers(activeOnly = false, intervalMs = 5000) {
  const [data, setData] = useState<Worker[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    try {
      const res = activeOnly
        ? await workersApi.active()
        : await workersApi.list();
      setData(res);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch workers");
    } finally {
      setLoading(false);
    }
  }, [activeOnly]);

  useEffect(() => {
    fetch();
    const id = setInterval(fetch, intervalMs);
    return () => clearInterval(id);
  }, [fetch, intervalMs]);

  return { data, error, loading, refresh: fetch };
}
