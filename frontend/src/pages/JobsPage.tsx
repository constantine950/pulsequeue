import { useState } from "react";
import { useJobs } from "../hooks/useJobs";
import { JobList } from "../components/jobs/JobList";
import { JobDetail } from "../components/jobs/JobDetail";
import type { Job, JobStatus } from "../types/job";

const STATUS_FILTERS: { label: string; value: JobStatus | "" }[] = [
  { label: "All", value: "" },
  { label: "Queued", value: "queued" },
  { label: "Running", value: "running" },
  { label: "Completed", value: "completed" },
  { label: "Failed", value: "failed" },
  { label: "Retrying", value: "retrying" },
  { label: "Dead", value: "dead" },
  { label: "Scheduled", value: "scheduled" },
];

export default function JobsPage() {
  const [statusFilter, setStatusFilter] = useState<JobStatus | "">("");
  const [selected, setSelected] = useState<Job | null>(null);

  const { data, loading, refresh } = useJobs({
    status: statusFilter || undefined,
    limit: 100,
    autoRefresh: true,
    intervalMs: 3000,
  });

  const jobs = data?.items ?? [];

  function handleAction() {
    setSelected(null);
    refresh();
  }

  return (
    <div className="h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Jobs</h1>
        <span className="text-sm text-muted font-mono">
          {data?.total ?? 0} total
        </span>
      </div>

      {/* Status filter tabs */}
      <div className="flex gap-1 flex-wrap">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
              statusFilter === f.value
                ? "bg-primary text-white"
                : "bg-panel border border-border text-muted hover:text-gray-300"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Split pane */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Job list */}
        <div className="w-1/2 card overflow-auto">
          <JobList
            jobs={jobs}
            selectedId={selected?.id ?? null}
            onSelect={setSelected}
            loading={loading}
          />
        </div>

        {/* Detail panel */}
        <div className="w-1/2 card overflow-auto">
          {selected ? (
            <JobDetail
              job={selected}
              onCancel={handleAction}
              onRequeue={handleAction}
            />
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
