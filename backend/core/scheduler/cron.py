from __future__ import annotations

from datetime import datetime, timezone

from croniter import croniter, CroniterBadCronError


def next_run(cron_expression: str, after: datetime | None = None) -> datetime:
    """
    Return the next datetime a cron expression fires after `after`.
    Defaults to now if after is not provided.
    Raises ValueError on invalid cron expression.
    """
    base = after or datetime.now(timezone.utc)

    try:
        itr = croniter(cron_expression, base)
        nxt = itr.get_next(datetime)
        # Ensure timezone-aware
        if nxt.tzinfo is None:
            nxt = nxt.replace(tzinfo=timezone.utc)
        return nxt
    except CroniterBadCronError as e:
        raise ValueError(f"Invalid cron expression '{cron_expression}': {e}")


def is_valid(cron_expression: str) -> bool:
    """Return True if the cron expression is syntactically valid."""
    return croniter.is_valid(cron_expression)


def describe(cron_expression: str) -> str:
    """
    Return a human-readable description of a cron expression.
    Best-effort — falls back to the raw expression if parsing fails.
    """
    parts = cron_expression.strip().split()
    if len(parts) != 5:
        return cron_expression

    minute, hour, dom, month, dow = parts

    if cron_expression == "* * * * *":
        return "Every minute"
    if minute.startswith("*/") and all(p == "*" for p in [hour, dom, month, dow]):
        return f"Every {minute[2:]} minutes"
    if minute == "0" and hour.isdigit() and all(p == "*" for p in [dom, month, dow]):
        return f"Every day at {int(hour):02d}:00 UTC"
    if minute == "0" and hour.isdigit() and dom == "*" and month == "*" and dow.isdigit():
        days = ["Sunday", "Monday", "Tuesday",
                "Wednesday", "Thursday", "Friday", "Saturday"]
        return f"Every {days[int(dow)]} at {int(hour):02d}:00 UTC"

    return cron_expression
