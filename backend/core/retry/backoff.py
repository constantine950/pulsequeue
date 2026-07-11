from __future__ import annotations

import random

from backend.config import settings


def compute_backoff(attempt: int) -> int:
    """
    Return delay in seconds before the next retry.

    attempt: how many times the job has already been attempted (1-based).
    """
    base = settings.retry_base_delay
    max_delay = settings.retry_max_delay

    delay = min(base * (2 ** (attempt - 1)), max_delay)

    if settings.retry_jitter:
        # ±25% jitter to spread out retry storms
        jitter = delay * 0.25
        delay = delay + random.uniform(-jitter, jitter)

    return max(1, int(delay))
