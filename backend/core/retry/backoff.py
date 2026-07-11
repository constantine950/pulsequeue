from __future__ import annotations

import random
from backend.config import settings


def compute_backoff(attempt: int) -> int:
    base = settings.retry_base_delay
    max_delay = settings.retry_max_delay

    delay = min(base * (2 ** (attempt - 1)), max_delay)

    if settings.retry_jitter:
        jitter = delay * 0.25
        delay = delay + random.uniform(-jitter, jitter)

    return max(1, int(delay))
