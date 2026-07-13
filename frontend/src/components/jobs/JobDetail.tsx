import { useState, useEffect } from "react";
import { jobsApi } from "../../api/jobs";
import { JobStatusBadge } from "./JobStatusBadge";
import type { Job, RetryAttempt } from "../../types/job";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex gap-4 py-2 border-b border-border text-sm">
      <span className="w-32 shrink-0 text-muted font-mono">{label}</span>
      <span className="font-mono text-gray-300 break-all">{value ?? "—"}</span>
    </div>
  );
}

export function JobDetail({
  job,
  onCancel,
  onRequeue,
}: {
  job: Job;
  onCancel?: () => void;
  onRequeue?: () => void;
}) {
  const [retries, setRetries] = useState<RetryAttempt[]>([]);
  const [acting, setActing] = useState(false);

  useEffect(() => {
    jobsApi
      .retries(job.id)
      .then(setRetries)
      .catch(() => {});
  }, [job.id]);

  const canCancel = ["queued", "scheduled", "retrying"].includes(job.status);
  const canRequeue = job.status === "dead";

  async function handleCancel() {
    setActing(true);
    try {
      await jobsApi.cancel(job.id);
      onCancel?.();
    } finally {
      setActing(false);
    }
  }

  async function handleRequeue() {
    setActing(true);
    try {
      await jobsApi.requeue(job.id);
      onRequeue?.();
    } finally {
      setActing(false);
    }
  }

  return (
    <div className="p-4 overflow-auto h-full">
      <div className="flex items-center gap-3 mb-4">
        <span className="font-mono text-sm text-gray-200">{job.task_name}</span>
        <JobStatusBadge status={job.status} />
        <span className="ml-auto flex gap-2">
          {canCancel && (
            <button
              onClick={handleCancel}
              disabled={acting}
              className="px-3 py-1 text-xs rounded border border-danger text-danger hover:bg-danger/10 disabled:opacity-50 font-mono"
            >
              cancel
            </button>
          )}
          {canRequeue && (
            <button
              onClick={handleRequeue}
              disabled={acting}
              className="px-3 py-1 text-xs rounded border border-primary text-primary hover:bg-primary/10 disabled:opacity-50 font-mono"
            >
              requeue
            </button>
          )}
        </span>
      </div>

      <Row label="id" value={job.id} />
      <Row label="priority" value={job.priority} />
      <Row label="attempt" value={`${job.attempt} / ${job.max_retries}`} />
      <Row label="timeout" value={`${job.timeout_seconds}s`} />
      <Row label="created" value={new Date(job.created_at).toLocaleString()} />
      <Row
        label="started"
        value={
          job.started_at ? new Date(job.started_at).toLocaleString() : null
        }
      />
      <Row
        label="finished"
        value={
          job.completed_at ? new Date(job.completed_at).toLocaleString() : null
        }
      />
      <Row
        label="duration"
        value={
          job.duration_seconds !== null
            ? `${job.duration_seconds.toFixed(3)}s`
            : null
        }
      />
      <Row label="worker" value={job.worker_id?.slice(0, 8)} />

      {Object.keys(job.payload).length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-muted font-mono mb-1">payload</p>
          <pre className="text-xs bg-surface p-3 rounded overflow-auto text-gray-300 border border-border">
            {JSON.stringify(job.payload, null, 2)}
          </pre>
        </div>
      )}

      {job.result && (
        <div className="mt-3">
          <p className="text-xs text-muted font-mono mb-1">result</p>
          <pre className="text-xs bg-surface p-3 rounded overflow-auto text-success/80 border border-border">
            {JSON.stringify(job.result, null, 2)}
          </pre>
        </div>
      )}

      {job.error_message && (
        <div className="mt-3">
          <p className="text-xs text-muted font-mono mb-1">error</p>
          <pre className="text-xs bg-surface p-3 rounded overflow-auto text-danger border border-border whitespace-pre-wrap">
            {job.error_message}
          </pre>
        </div>
      )}

      {retries.length > 0 && (
        <div className="mt-4">
          <p className="text-xs text-muted font-mono mb-2">
            retry history ({retries.length})
          </p>
          <div className="space-y-2">
            {retries.map((r) => (
              <div
                key={r.id}
                className="text-xs font-mono bg-surface border border-border rounded p-2"
              >
                <div className="flex justify-between text-muted mb-1">
                  <span>attempt {r.attempt}</span>
                  <span>backoff {r.backoff_seconds}s</span>
                </div>
                <p className="text-danger truncate">{r.error_message}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
