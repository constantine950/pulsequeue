export type WorkerStatus = "active" | "stale" | "stopped";

export interface Worker {
  id: string;
  hostname: string;
  pid: number;
  status: WorkerStatus;
  queues: string[];
  concurrency: number;
  last_heartbeat_at: string;
  jobs_processed: number;
  jobs_failed: number;
  started_at: string;
}
