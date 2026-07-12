"""
core/scheduler/cron.py — filled fully on Day 16.
Stub provides next_run() so Day 15 schedule creation works.
"""

from __future__ import annotations

from datetime import datetime, timezone
from croniter import croniter


def next_run(cron_expression: str, after: datetime | None = None) -> datetime:
    """Return the next datetime a cron expression fires after `after` (default: now)."""
    base = after or datetime.now(timezone.utc)
    itr = croniter(cron_expression, base)
    return itr.get_next(datetime).replace(tzinfo=timezone.utc)
