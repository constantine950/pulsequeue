import { api } from "./client";
import type { Metrics } from "../types/metric";

export const metricsApi = {
  snapshot: () => api.get<Metrics>("/metrics"),
  queue: () =>
    api.get<{ queue_depth: Record<string, number>; total_queued: number }>(
      "/metrics/queue",
    ),
  workers: () => api.get<{ active_workers: number }>("/metrics/workers"),
};
