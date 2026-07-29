export default function LandingPage() {
  return (
    <div className="min-h-screen bg-surface text-gray-100 font-sans flex flex-col">
      {/* Nav */}
      <nav className="border-b border-border px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-primary font-mono font-bold text-lg">
            ▶ PulseQueue
          </span>
        </div>
        <div className="flex items-center gap-6">
          <a
            href="#features"
            className="text-sm text-muted hover:text-gray-300 transition-colors"
          >
            Features
          </a>
          <a
            href="#stack"
            className="text-sm text-muted hover:text-gray-300 transition-colors"
          >
            Stack
          </a>
          <a
            href="/metrics"
            className="px-4 py-1.5 rounded bg-primary text-white text-sm font-mono hover:bg-primary/80 transition-colors"
          >
            Dashboard →
          </a>
        </div>
      </nav>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-6 py-24 gap-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-border text-xs font-mono text-muted mb-2">
          <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
          production-grade · self-hosted · open source
        </div>

        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight max-w-3xl leading-tight">
          Background jobs, <span className="text-primary">done right</span>
        </h1>

        <p className="text-lg text-muted max-w-xl leading-relaxed">
          PulseQueue is a distributed job orchestration system that queues,
          schedules, retries, and monitors async tasks across workers — built
          from scratch in Python and React.
        </p>

        <div className="flex flex-wrap gap-4 justify-center">
          <a
            href="/metrics"
            className="px-6 py-3 rounded-lg bg-primary text-white font-mono hover:bg-primary/80 transition-colors text-sm"
          >
            Open Dashboard →
          </a>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="px-6 py-3 rounded-lg border border-border text-muted hover:text-gray-300 hover:border-gray-500 transition-colors font-mono text-sm"
          >
            View Source
          </a>
        </div>

        {/* Live stats strip */}
        <LiveStats />
      </section>

      {/* Features */}
      <section id="features" className="px-8 py-20 max-w-5xl mx-auto w-full">
        <h2 className="text-2xl font-bold text-center mb-12">
          Everything a job system needs
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f) => (
            <div key={f.title} className="card p-5 space-y-2">
              <div className="text-2xl">{f.icon}</div>
              <h3 className="font-semibold text-gray-100">{f.title}</h3>
              <p className="text-sm text-muted leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Stack */}
      <section id="stack" className="px-8 py-20 border-t border-border">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-12">Tech stack</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
            {STACK.map((s) => (
              <div key={s.name} className="card p-4 space-y-2">
                <p className="text-2xl">{s.icon}</p>
                <p className="font-mono text-sm text-gray-200">{s.name}</p>
                <p className="text-xs text-muted">{s.role}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-8 py-20 border-t border-border text-center">
        <h2 className="text-2xl font-bold mb-4">See it running live</h2>
        <p className="text-muted mb-8">
          The dashboard shows real jobs, real workers, and real metrics — all
          running right now.
        </p>
        <a
          href="/metrics"
          className="inline-block px-8 py-3 rounded-lg bg-primary text-white font-mono hover:bg-primary/80 transition-colors"
        >
          Open Dashboard →
        </a>
      </section>

      {/* Footer */}
      <footer className="border-t border-border px-8 py-6 flex items-center justify-between text-xs text-muted font-mono">
        <span>▶ PulseQueue</span>
        <span>Python · FastAPI · Redis · PostgreSQL · React</span>
      </footer>
    </div>
  );
}

// Live stats from the API

import { useEffect, useState } from "react";

function LiveStats() {
  const [stats, setStats] = useState<{
    active_workers: number;
    jobs_completed: number;
    failure_rate: number;
  } | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/api/metrics");
        const data = await res.json();
        setStats({
          active_workers: data.active_workers,
          jobs_completed: data.jobs?.completed ?? 0,
          failure_rate: data.failure_rate_pct,
        });
      } catch {}
    }
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  const items = [
    {
      label: "active workers",
      value: stats?.active_workers ?? "—",
      color: "text-success",
    },
    {
      label: "jobs completed",
      value: stats?.jobs_completed ?? "—",
      color: "text-primary",
    },
    {
      label: "failure rate",
      value: stats ? `${stats.failure_rate}%` : "—",
      color: "text-warning",
    },
  ];

  return (
    <div className="flex flex-wrap gap-8 justify-center mt-4 p-6 rounded-xl border border-border bg-panel">
      {items.map(({ label, value, color }) => (
        <div key={label} className="text-center">
          <p className={`text-3xl font-mono font-bold ${color}`}>{value}</p>
          <p className="text-xs text-muted mt-1">{label}</p>
        </div>
      ))}
      <div className="flex items-center gap-1.5 text-xs text-muted font-mono self-center">
        <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
        live
      </div>
    </div>
  );
}

// Data

const FEATURES = [
  {
    icon: "⚡",
    title: "Priority queues",
    desc: "Three Redis-backed queues — high, normal, low. Workers always drain high before normal before low.",
  },
  {
    icon: "🔁",
    title: "Retry with backoff",
    desc: "Failed jobs retry automatically with exponential backoff and jitter. Configurable per job.",
  },
  {
    icon: "💀",
    title: "Dead letter queue",
    desc: "Jobs that exhaust retries move to the DLQ. Inspect, requeue, or purge from the dashboard.",
  },
  {
    icon: "🕐",
    title: "Scheduled jobs",
    desc: "Delay execution to a future time or set recurring cron expressions. Scheduler polls every second.",
  },
  {
    icon: "📊",
    title: "Live metrics",
    desc: "Queue depth, failure rate, throughput, and average runtime — all computed from Postgres in real time.",
  },
  {
    icon: "🫀",
    title: "Worker heartbeat",
    desc: "Workers write heartbeats every 10s. Stale workers are detected and their jobs recovered automatically.",
  },
  {
    icon: "⏱️",
    title: "Timeout protection",
    desc: "Every job has a configurable timeout. Stuck jobs are killed and retried like any other failure.",
  },
  {
    icon: "🐳",
    title: "Docker ready",
    desc: "Full stack runs with docker compose up — Postgres, Redis, API, worker, scheduler, and dashboard.",
  },
  {
    icon: "🎯",
    title: "Task registry",
    desc: "Register any async Python function as a task. Workers resolve task names to callables at runtime.",
  },
];

const STACK = [
  { icon: "🐍", name: "FastAPI", role: "API server" },
  { icon: "🐘", name: "PostgreSQL", role: "Job store" },
  { icon: "⚡", name: "Redis", role: "Queue backend" },
  { icon: "⚛️", name: "React", role: "Dashboard" },
  { icon: "🎨", name: "Tailwind", role: "Styling" },
  { icon: "📦", name: "asyncpg", role: "DB driver" },
  { icon: "🐳", name: "Docker", role: "Containers" },
  { icon: "📈", name: "Recharts", role: "Charts" },
];
