import clsx from "clsx";
import { JobStatusBadge } from "./JobStatusBadge";
import type { Job } from "../../types/job";

const priorityDot: Record<string, string> = {
  high: "bg-danger",
  normal: "bg-primary",
  low: "bg-muted",
};

function fmt(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function duration(s: number | null) {
  if (s === null) return null;
  if (s < 1) return `${Math.round(s * 1000)}ms`;
  return `${s.toFixed(2)}s`;
}

interface Props {
  job: Job;
  onClick: () => void;
  selected: boolean;
}

export function JobCard({ job, onClick, selected }: Props) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "w-full text-left px-4 py-3 border-b border-border transition-colors",
        "hover:bg-border/30 focus:outline-none",
        selected && "bg-border/50 border-l-2 border-l-primary",
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        <span
          className={clsx(
            "w-1.5 h-1.5 rounded-full shrink-0",
            priorityDot[job.priority],
          )}
        />
        <span className="font-mono text-sm text-gray-200 truncate flex-1">
          {job.task_name}
        </span>
        <JobStatusBadge status={job.status} />
      </div>
      <div className="flex items-center gap-3 text-xs text-muted font-mono pl-3.5">
        <span title="Job ID">{job.id.slice(0, 8)}…</span>
        <span>
          attempt {job.attempt}/{job.max_retries}
        </span>
        {job.duration_seconds !== null && (
          <span className="text-gray-400">
            {duration(job.duration_seconds)}
          </span>
        )}
        <span className="ml-auto">{fmt(job.created_at)}</span>
      </div>
      {job.error_message && (
        <p className="mt-1 text-xs text-danger truncate pl-3.5">
          {job.error_message}
        </p>
      )}
    </button>
  );
}
