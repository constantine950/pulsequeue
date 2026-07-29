import { useState } from "react";

interface Props {
  onLogin: (key: string) => void;
}

export default function LoginPage({ onLogin }: Props) {
  const [key, setKey] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!key.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/metrics", {
        headers: { "X-API-Key": key.trim() },
      });
      if (res.ok) {
        onLogin(key.trim());
      } else {
        setError("Invalid API key");
      }
    } catch {
      setError("Cannot reach API server");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-8">
        <div className="text-center">
          <p className="text-primary font-mono font-bold text-2xl mb-2">
            ▶ PulseQueue
          </p>
          <p className="text-muted text-sm">
            Enter your API key to access the dashboard
          </p>
        </div>

        <form onSubmit={handleSubmit} className="card p-6 space-y-4">
          <div>
            <label className="text-xs text-muted font-mono block mb-1.5">
              API Key
            </label>
            <input
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="your-api-key"
              autoFocus
              className="w-full bg-surface border border-border rounded px-3 py-2 text-sm font-mono text-gray-200 focus:outline-none focus:border-primary"
            />
          </div>

          {error && <p className="text-xs text-danger font-mono">{error}</p>}

          <button
            type="submit"
            disabled={loading || !key.trim()}
            className="w-full py-2 rounded bg-primary text-white text-sm font-mono hover:bg-primary/80 disabled:opacity-50 transition-colors"
          >
            {loading ? "checking…" : "Enter Dashboard"}
          </button>
        </form>

        <p className="text-center text-xs text-muted font-mono">
          No API key set?{" "}
          <a href="/metrics" className="text-primary hover:underline">
            skip login →
          </a>
        </p>
      </div>
    </div>
  );
}
