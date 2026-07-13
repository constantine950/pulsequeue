import clsx from "clsx";
import type { JobStatus } from "../../types/job";

const config: Record<JobStatus, { label: string; className: string }> = {
  queued: { label: "queued", className: "bg-primary/10 text-primary" },
  scheduled: { label: "scheduled", className: "bg-warning/10 text-warning" },
  running: {
    label: "running",
    className: "bg-success/10 text-success animate-pulse",
  },
  completed: { label: "done", className: "bg-success/10 text-success" },
  failed: { label: "failed", className: "bg-danger/10 text-danger" },
  retrying: { label: "retrying", className: "bg-warning/10 text-warning" },
  dead: { label: "dead", className: "bg-dead/10 text-dead" },
  cancelled: { label: "cancelled", className: "bg-border text-muted" },
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  const { label, className } = config[status] ?? config.failed;
  return <span className={clsx("badge", className)}>{label}</span>;
}
