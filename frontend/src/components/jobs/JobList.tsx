import { JobCard } from "./JobCard";
import type { Job } from "../../types/job";

interface Props {
  jobs: Job[];
  selectedId: string | null;
  onSelect: (job: Job) => void;
  loading: boolean;
}

export function JobList({ jobs, selectedId, onSelect, loading }: Props) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-32 text-muted text-sm font-mono">
        loading…
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-muted text-sm font-mono">
        no jobs yet
      </div>
    );
  }

  return (
    <div className="divide-y divide-border">
      {jobs.map((job) => (
        <JobCard
          key={job.id}
          job={job}
          selected={job.id === selectedId}
          onClick={() => onSelect(job)}
        />
      ))}
    </div>
  );
}
