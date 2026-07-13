import { useState, useEffect, useCallback } from "react";
import { jobsApi } from "../api/jobs";
import type { Job, JobListResponse } from "../types/job";

export function useJobs(params?: {
  status?: string;
  task_name?: string;
  limit?: number;
  offset?: number;
  autoRefresh?: boolean;
  intervalMs?: number;
}) {
  const [data, setData] = useState<JobListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    try {
      const res = await jobsApi.list(params);
      setData(res);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch jobs");
    } finally {
      setLoading(false);
    }
  }, [params?.status, params?.task_name, params?.limit, params?.offset]);

  useEffect(() => {
    fetch();
    if (params?.autoRefresh) {
      const id = setInterval(fetch, params.intervalMs ?? 4000);
      return () => clearInterval(id);
    }
  }, [fetch, params?.autoRefresh, params?.intervalMs]);

  return { data, error, loading, refresh: fetch };
}
