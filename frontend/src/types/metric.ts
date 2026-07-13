export interface QueueDepth {
  high: number;
  normal: number;
  low: number;
  scheduled: number;
}

export interface Metrics {
  timestamp: string;
  queue_depth: QueueDepth;
  jobs: Record<string, number>;
  failure_rate_pct: number;
  avg_runtime_seconds: number | null;
  throughput_last_hour: number;
  active_workers: number;
  retries: {
    total_last_hour: number;
    avg_backoff_seconds: number;
  };
}
