import { useState } from "react";
import { useWorkers } from "../hooks/useWorkers";
import { WorkerList } from "../components/workers/WorkerList";

export default function WorkersPage() {
  const [activeOnly, setActiveOnly] = useState(false);
  const { data: workers, loading } = useWorkers(activeOnly, 5000);

  const active = workers.filter((w) => w.status === "active");
  const stale = workers.filter((w) => w.status === "stale");
  const stopped = workers.filter((w) => w.status === "stopped");

  const totalProcessed = workers.reduce((s, w) => s + w.jobs_processed, 0);
  const totalFailed = workers.reduce((s, w) => s + w.jobs_failed, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Workers</h1>
        <label className="flex items-center gap-2 text-sm text-muted cursor-pointer select-none">
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={(e) => setActiveOnly(e.target.checked)}
            className="accent-primary"
          />
          active only
        </label>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "active", value: active.length, color: "text-success" },
          { label: "stale", value: stale.length, color: "text-warning" },
          { label: "processed", value: totalProcessed, color: "text-gray-100" },
          { label: "failed", value: totalFailed, color: "text-danger" },
        ].map(({ label, value, color }) => (
          <div key={label} className="card px-4 py-3 text-center">
            <p className={`text-2xl font-mono font-semibold ${color}`}>
              {value}
            </p>
            <p className="text-xs text-muted mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      <WorkerList workers={workers} loading={loading} />

      {!activeOnly && stopped.length > 0 && (
        <p className="text-xs text-muted font-mono text-center">
          {stopped.length} stopped worker{stopped.length !== 1 ? "s" : ""} not
          shown — toggle "active only" off to see all
        </p>
      )}
    </div>
  );
}
