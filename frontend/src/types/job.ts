export type JobStatus =
  | "queued"
  | "scheduled"
  | "running"
  | "completed"
  | "failed"
  | "retrying"
  | "dead"
  | "cancelled";

export type JobPriority = "high" | "normal" | "low";

export interface Job {
  id: string;
  task_name: string;
  payload: Record<string, unknown>;
  status: JobStatus;
  priority: JobPriority;
  queue: string;
  run_at: string;
  scheduled_for: string | null;
  worker_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  timeout_seconds: number;
  max_retries: number;
  attempt: number;
  result: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  duration_seconds: number | null;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  limit: number;
  offset: number;
}

export interface RetryAttempt {
  id: string;
  job_id: string;
  attempt: number;
  error_message: string;
  retried_at: string;
  next_retry_at: string | null;
  backoff_seconds: number;
}
