import { useMetrics } from "../hooks/useMetrics";
import { MetricsDashboard } from "../components/metrics/MetricsDashboard";

export default function MetricsPage() {
  const { data, error, loading } = useMetrics(3000);

  if (loading)
    return (
      <div className="flex items-center justify-center h-48 text-muted text-sm font-mono">
        loading…
      </div>
    );

  if (error)
    return (
      <div className="flex items-center justify-center h-48 text-danger text-sm font-mono">
        {error}
      </div>
    );

  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Overview</h1>
        <span className="text-xs text-muted font-mono">
          updated {new Date(data.timestamp).toLocaleTimeString()}
        </span>
      </div>
      <MetricsDashboard metrics={data} />
    </div>
  );
}
