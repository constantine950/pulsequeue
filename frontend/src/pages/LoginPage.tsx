import { useState } from "react";

interface Props {
  onLogin: (key: string) => void;
}

const DEMO_KEY = "pulsequeue-demo";

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

  function handleDemoLogin() {
    onLogin(DEMO_KEY);
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-6">
        {/* Logo */}
        <div className="text-center">
          <p className="text-primary font-mono font-bold text-2xl mb-2">
            ▶ PulseQueue
          </p>
          <p className="text-muted text-sm">
            Distributed background job orchestration
          </p>
        </div>

        {/* Demo banner */}
        <div className="card p-4 border-primary/30 bg-primary/5">
          <p className="text-xs text-primary font-mono font-semibold mb-2">
            🔓 Live demo available
          </p>
          <p className="text-xs text-muted mb-3 leading-relaxed">
            Explore the live system — real workers, real jobs, real metrics. Use
            the demo key below or click the button to jump straight in.
          </p>
          <div className="flex items-center gap-2 bg-surface rounded px-3 py-2 mb-3 border border-border">
            <code className="text-xs font-mono text-gray-200 flex-1 select-all">
              {DEMO_KEY}
            </code>
            <button
              onClick={() => navigator.clipboard?.writeText(DEMO_KEY)}
              className="text-xs text-muted hover:text-gray-300 font-mono transition-colors"
              title="Copy"
            >
              copy
            </button>
          </div>
          <button
            onClick={handleDemoLogin}
            className="w-full py-2 rounded bg-primary text-white text-sm font-mono hover:bg-primary/80 transition-colors"
          >
            Enter with demo key →
          </button>
        </div>

        {/* Divider */}
        <div className="flex items-center gap-3">
          <div className="flex-1 h-px bg-border" />
          <span className="text-xs text-muted font-mono">
            or enter your own key
          </span>
          <div className="flex-1 h-px bg-border" />
        </div>

        {/* Manual key form */}
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="your-api-key"
            className="w-full bg-surface border border-border rounded px-3 py-2 text-sm font-mono text-gray-200 focus:outline-none focus:border-primary"
          />
          {error && <p className="text-xs text-danger font-mono">{error}</p>}
          <button
            type="submit"
            disabled={loading || !key.trim()}
            className="w-full py-2 rounded border border-border text-muted text-sm font-mono hover:text-gray-300 hover:border-gray-500 disabled:opacity-50 transition-colors"
          >
            {loading ? "checking…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
