import { useState, useEffect, useCallback } from "react";
import { metricsApi } from "../api/metrics";
import type { Metrics } from "../types/metric";

export function useMetrics(intervalMs = 3000) {
  const [data, setData] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    try {
      const m = await metricsApi.snapshot();
      setData(m);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch metrics");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
    const id = setInterval(fetch, intervalMs);
    return () => clearInterval(id);
  }, [fetch, intervalMs]);

  return { data, error, loading, refresh: fetch };
}
