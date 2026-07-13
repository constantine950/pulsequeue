import { api } from "./client";
import type { Worker } from "../types/worker";

export const workersApi = {
  list: () => api.get<Worker[]>("/workers"),
  active: () => api.get<Worker[]>("/workers/active"),
  get: (id: string) => api.get<Worker>(`/workers/${id}`),
};
