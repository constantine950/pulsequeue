import type { Metrics } from "../../types/metric";

const statusColors: Record<string, string> = {
  completed: "#34d399",
  failed: "#f87171",
  dead: "#a78bfa",
  queued: "#4f8ef7",
  running: "#34d399",
  retrying: "#fbbf24",
  scheduled: "#fbbf24",
  cancelled: "#8892a4",
};

function StatCard({
  label,
  value,
  sub,
  color = "text-gray-100",
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="card px-5 py-4">
      <p className="text-xs text-muted font-mono mb-1">{label}</p>
      <p className={`text-2xl font-mono font-semibold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-muted mt-0.5 font-mono">{sub}</p>}
    </div>
  );
}

export function MetricsDashboard({ metrics }: { metrics: Metrics }) {
  const {
    queue_depth,
    jobs,
    failure_rate_pct,
    avg_runtime_seconds,
    throughput_last_hour,
    active_workers,
    retries,
  } = metrics;

  const totalQueued = queue_depth.high + queue_depth.normal + queue_depth.low;
  const totalJobs = Object.values(jobs).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-6">
      {/* Top stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard
          label="active workers"
          value={active_workers}
          color={active_workers > 0 ? "text-success" : "text-muted"}
        />
        <StatCard
          label="queued now"
          value={totalQueued}
          sub={`${queue_depth.high}h · ${queue_depth.normal}n · ${queue_depth.low}l`}
          color={totalQueued > 0 ? "text-primary" : "text-gray-100"}
        />
        <StatCard
          label="failure rate (1h)"
          value={`${failure_rate_pct}%`}
          color={
            failure_rate_pct > 20
              ? "text-danger"
              : failure_rate_pct > 5
                ? "text-warning"
                : "text-success"
          }
        />
        <StatCard
          label="throughput (1h)"
          value={throughput_last_hour}
          sub={
            avg_runtime_seconds
              ? `avg ${avg_runtime_seconds.toFixed(2)}s`
              : undefined
          }
        />
      </div>

      {/* Second row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="total jobs" value={totalJobs} />
        <StatCard
          label="completed"
          value={jobs.completed ?? 0}
          color="text-success"
        />
        <StatCard
          label="failed / dead"
          value={(jobs.failed ?? 0) + (jobs.dead ?? 0)}
          color="text-danger"
        />
        <StatCard
          label="retries (1h)"
          value={retries.total_last_hour}
          sub={`avg backoff ${retries.avg_backoff_seconds}s`}
        />
      </div>

      {/* Job status breakdown */}
      <div className="card p-5">
        <p className="text-xs text-muted font-mono mb-4">
          job status breakdown
        </p>
        <div className="space-y-2">
          {Object.entries(jobs)
            .sort(([, a], [, b]) => b - a)
            .map(([status, count]) => {
              const pct = totalJobs > 0 ? (count / totalJobs) * 100 : 0;
              return (
                <div key={status} className="flex items-center gap-3">
                  <span className="w-20 text-xs font-mono text-muted shrink-0">
                    {status}
                  </span>
                  <div className="flex-1 bg-surface rounded-full h-2 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${pct}%`,
                        backgroundColor: statusColors[status] ?? "#8892a4",
                      }}
                    />
                  </div>
                  <span className="w-12 text-xs font-mono text-gray-300 text-right shrink-0">
                    {count}
                  </span>
                </div>
              );
            })}
        </div>
      </div>

      {/* Queue depth by priority */}
      <div className="card p-5">
        <p className="text-xs text-muted font-mono mb-4">
          queue depth by priority
        </p>
        <div className="grid grid-cols-4 gap-3 text-center">
          {[
            { label: "high", value: queue_depth.high, color: "#f87171" },
            { label: "normal", value: queue_depth.normal, color: "#4f8ef7" },
            { label: "low", value: queue_depth.low, color: "#8892a4" },
            {
              label: "scheduled",
              value: queue_depth.scheduled,
              color: "#fbbf24",
            },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-surface rounded p-3">
              <p className="text-xl font-mono font-semibold" style={{ color }}>
                {value}
              </p>
              <p className="text-xs text-muted mt-1">{label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
