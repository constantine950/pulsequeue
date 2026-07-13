import { api } from "./client";
import type { Job, JobListResponse, RetryAttempt } from "../types/job";

export const jobsApi = {
  list: (params?: {
    status?: string;
    task_name?: string;
    limit?: number;
    offset?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.task_name) q.set("task_name", params.task_name);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    const qs = q.toString() ? `?${q}` : "";
    return api.get<JobListResponse>(`/jobs${qs}`);
  },

  get: (id: string) => api.get<Job>(`/jobs/${id}`),
  retries: (id: string) => api.get<RetryAttempt[]>(`/jobs/${id}/retries`),
  cancel: (id: string) => api.delete<{ cancelled: string }>(`/jobs/${id}`),
  requeue: (id: string) => api.post<Job>(`/jobs/${id}/requeue`, {}),
  dead: (limit = 50) => api.get<JobListResponse>(`/jobs/dead?limit=${limit}`),
  purgeDead: () => api.delete<{ purged: number }>("/jobs/dead"),

  create: (body: {
    task_name: string;
    payload?: Record<string, unknown>;
    priority?: string;
    max_retries?: number;
    timeout_seconds?: number;
    run_at?: string;
  }) => api.post<Job>("/jobs", body),
};
