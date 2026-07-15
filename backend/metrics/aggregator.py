from __future__ import annotations

from datetime import datetime, timezone

import asyncpg

from backend.metrics.collector import (
    active_worker_count,
    avg_runtime_last_hour,
    failure_rate_last_hour,
    job_counts_by_status,
    queue_depths,
    retry_stats,
    throughput_last_hour,
)


async def get_snapshot(pool: asyncpg.Pool) -> dict:
    import asyncio

    (
        depths,
        counts,
        failure_rate,
        avg_runtime,
        throughput,
        workers,
        retries,
    ) = await asyncio.gather(
        queue_depths(pool),
        job_counts_by_status(pool),
        failure_rate_last_hour(pool),
        avg_runtime_last_hour(pool),
        throughput_last_hour(pool),
        active_worker_count(pool),
        retry_stats(pool),
    )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "queue_depth": depths,
        "jobs": counts,
        "failure_rate_pct": failure_rate,
        "avg_runtime_seconds": avg_runtime,
        "throughput_last_hour": throughput,
        "active_workers": workers,
        "retries": retries,
    }
