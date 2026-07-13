import { useMetrics } from "../../hooks/useMetrics";

export function Navbar() {
  const { data } = useMetrics(5000);

  return (
    <header className="border-b border-border px-6 py-3 flex items-center justify-between shrink-0">
      <span className="text-sm text-muted font-mono">PulseQueue</span>
      <div className="flex items-center gap-6 text-xs font-mono">
        <span className="text-muted">
          workers{" "}
          <span
            className={data?.active_workers ? "text-success" : "text-muted"}
          >
            {data?.active_workers ?? "—"}
          </span>
        </span>
        <span className="text-muted">
          failure rate{" "}
          <span
            className={
              !data
                ? "text-muted"
                : data.failure_rate_pct > 20
                  ? "text-danger"
                  : data.failure_rate_pct > 5
                    ? "text-warning"
                    : "text-success"
            }
          >
            {data ? `${data.failure_rate_pct}%` : "—"}
          </span>
        </span>
        <span className="text-muted">
          queue{" "}
          <span className="text-primary">
            {data
              ? Object.values(data.queue_depth).reduce((a, b) => a + b, 0)
              : "—"}
          </span>
        </span>
      </div>
    </header>
  );
}
