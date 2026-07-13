import { WorkerCard } from "./WorkerCard";
import type { Worker } from "../../types/worker";

export function WorkerList({
  workers,
  loading,
}: {
  workers: Worker[];
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-32 text-muted text-sm font-mono">
        loading…
      </div>
    );
  }

  if (workers.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-muted text-sm font-mono">
        no workers registered
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
      {workers.map((w) => (
        <WorkerCard key={w.id} worker={w} />
      ))}
    </div>
  );
}
