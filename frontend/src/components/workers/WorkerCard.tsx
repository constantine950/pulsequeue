import clsx from "clsx";
import type { Worker } from "../../types/worker";

function timeSince(iso: string) {
  const secs = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (secs < 60) return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  return `${Math.floor(secs / 3600)}h ago`;
}

function uptime(startIso: string) {
  const secs = Math.floor((Date.now() - new Date(startIso).getTime()) / 1000);
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

const statusColor: Record<string, string> = {
  active: "bg-success",
  stale: "bg-warning",
  stopped: "bg-muted",
};

export function WorkerCard({ worker }: { worker: Worker }) {
  const successRate =
    worker.jobs_processed + worker.jobs_failed > 0
      ? Math.round(
          (worker.jobs_processed /
            (worker.jobs_processed + worker.jobs_failed)) *
            100,
        )
      : null;

  const heartbeatSecs = Math.floor(
    (Date.now() - new Date(worker.last_heartbeat_at).getTime()) / 1000,
  );
  const heartbeatStale = heartbeatSecs > 20;

  return (
    <div className="card p-4 space-y-3">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span
              className={clsx(
                "w-2 h-2 rounded-full",
                statusColor[worker.status],
              )}
            />
            <span className="font-mono text-sm text-gray-200">
              {worker.hostname}
            </span>
          </div>
          <p className="text-xs text-muted font-mono mt-0.5">
            pid {worker.pid}
          </p>
        </div>
        <span
          className={clsx(
            "text-xs font-mono px-2 py-0.5 rounded",
            worker.status === "active"
              ? "text-success bg-success/10"
              : worker.status === "stale"
                ? "text-warning bg-warning/10"
                : "text-muted bg-border",
          )}
        >
          {worker.status}
        </span>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-surface rounded p-2">
          <p className="text-lg font-mono font-semibold text-gray-100">
            {worker.jobs_processed}
          </p>
          <p className="text-xs text-muted">done</p>
        </div>
        <div className="bg-surface rounded p-2">
          <p className="text-lg font-mono font-semibold text-danger">
            {worker.jobs_failed}
          </p>
          <p className="text-xs text-muted">failed</p>
        </div>
        <div className="bg-surface rounded p-2">
          <p className="text-lg font-mono font-semibold text-gray-100">
            {successRate !== null ? `${successRate}%` : "—"}
          </p>
          <p className="text-xs text-muted">success</p>
        </div>
      </div>

      {/* Footer */}
      <div className="flex justify-between text-xs font-mono text-muted">
        <span>up {uptime(worker.started_at)}</span>
        <span className={clsx(heartbeatStale && "text-warning")}>
          ♥ {timeSince(worker.last_heartbeat_at)}
        </span>
      </div>

      {/* Queues */}
      <div className="flex gap-1 flex-wrap">
        {worker.queues.map((q) => (
          <span
            key={q}
            className="text-xs font-mono px-1.5 py-0.5 bg-border rounded text-muted"
          >
            {q}
          </span>
        ))}
      </div>
    </div>
  );
}
