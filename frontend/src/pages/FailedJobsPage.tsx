import { useState, useCallback } from "react";
import { useJobs } from "../hooks/useJobs";
import { jobsApi } from "../api/jobs";
import { JobStatusBadge } from "../components/jobs/JobStatusBadge";
import { JobDetail } from "../components/jobs/JobDetail";
import type { Job } from "../types/job";

function RelativeTime({ iso }: { iso: string }) {
  const secs = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (secs < 60) return <>{secs}s ago</>;
  if (secs < 3600) return <>{Math.floor(secs / 60)}m ago</>;
  if (secs < 86400) return <>{Math.floor(secs / 3600)}h ago</>;
  return <>{Math.floor(secs / 86400)}d ago</>;
}

function FailedRow({
  job,
  selected,
  onSelect,
  onRequeue,
}: {
  job: Job;
  selected: boolean;
  onSelect: () => void;
  onRequeue: () => void;
}) {
  const [acting, setActing] = useState(false);

  async function handleRequeue(e: React.MouseEvent) {
    e.stopPropagation();
    setActing(true);
    try {
      await jobsApi.requeue(job.id);
      onRequeue();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Requeue failed");
    } finally {
      setActing(false);
    }
  }

  return (
    <tr
      onClick={onSelect}
      className={`border-b border-border cursor-pointer transition-colors hover:bg-border/30 ${
        selected ? "bg-border/50" : ""
      }`}
    >
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <JobStatusBadge status={job.status} />
        </div>
      </td>
      <td className="px-4 py-3 font-mono text-sm text-gray-200">
        {job.task_name}
      </td>
      <td className="px-4 py-3 font-mono text-xs text-muted">
        {job.id.slice(0, 8)}…
      </td>
      <td className="px-4 py-3 text-xs text-danger font-mono truncate max-w-xs">
        {job.error_message ?? "—"}
      </td>
      <td className="px-4 py-3 font-mono text-xs text-muted text-center">
        {job.attempt}
      </td>
      <td className="px-4 py-3 font-mono text-xs text-muted">
        <RelativeTime iso={job.updated_at} />
      </td>
      <td className="px-4 py-3 text-right">
        {job.status === "dead" && (
          <button
            onClick={handleRequeue}
            disabled={acting}
            className="px-2 py-1 text-xs rounded border border-primary text-primary hover:bg-primary/10 disabled:opacity-50 font-mono"
          >
            {acting ? "…" : "requeue"}
          </button>
        )}
      </td>
    </tr>
  );
}

export default function FailedJobsPage() {
  const [selected, setSelected] = useState<Job | null>(null);
  const [purging, setPurging] = useState(false);
  const [tab, setTab] = useState<"failed" | "dead">("dead");

  const { data, loading, refresh } = useJobs({
    status: tab,
    limit: 100,
    autoRefresh: true,
    intervalMs: 5000,
  });

  const jobs = data?.items ?? [];

  const handleRequeue = useCallback(() => {
    setSelected(null);
    refresh();
  }, [refresh]);

  async function handlePurgeDead() {
    if (
      !confirm(
        "Purge all entries from the dead letter queue? Jobs will remain in the database as dead.",
      )
    )
      return;
    setPurging(true);
    try {
      const res = await jobsApi.purgeDead();
      alert(`Purged ${res.purged} entries from DLQ`);
      refresh();
    } finally {
      setPurging(false);
    }
  }

  return (
    <div className="h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Failed Jobs</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted font-mono">
            {data?.total ?? 0} total
          </span>
          {tab === "dead" && (
            <button
              onClick={handlePurgeDead}
              disabled={purging || jobs.length === 0}
              className="px-3 py-1 text-xs rounded border border-danger text-danger hover:bg-danger/10 disabled:opacity-40 font-mono"
            >
              {purging ? "purging…" : "purge DLQ"}
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1">
        {(["dead", "failed"] as const).map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              setSelected(null);
            }}
            className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
              tab === t
                ? t === "dead"
                  ? "bg-dead text-white"
                  : "bg-danger text-white"
                : "bg-panel border border-border text-muted hover:text-gray-300"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="flex-1 flex gap-4 min-h-0">
        {/* Table */}
        <div className="flex-1 card overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center h-32 text-muted text-sm font-mono">
              loading…
            </div>
          ) : jobs.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-muted text-sm font-mono">
              no {tab} jobs — nice
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-xs text-muted font-mono">
                  <th className="px-4 py-2 text-left w-20">status</th>
                  <th className="px-4 py-2 text-left">task</th>
                  <th className="px-4 py-2 text-left">id</th>
                  <th className="px-4 py-2 text-left">error</th>
                  <th className="px-4 py-2 text-center w-16">tries</th>
                  <th className="px-4 py-2 text-left w-24">when</th>
                  <th className="px-4 py-2 w-20" />
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <FailedRow
                    key={job.id}
                    job={job}
                    selected={selected?.id === job.id}
                    onSelect={() => setSelected(job)}
                    onRequeue={handleRequeue}
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Detail */}
        <div className="w-80 card overflow-auto shrink-0">
          {selected ? (
            <JobDetail job={selected} onRequeue={handleRequeue} />
          ) : (
            <div className="flex items-center justify-center h-full text-muted text-sm font-mono">
              select a job
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
