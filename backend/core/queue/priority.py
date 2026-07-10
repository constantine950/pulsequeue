from backend.config import settings
from backend.models.job import JobPriority

# Map priority → Redis list key
QUEUE_KEYS: dict[JobPriority, str] = {
    JobPriority.high:   settings.queue_high,
    JobPriority.normal: settings.queue_normal,
    JobPriority.low:    settings.queue_low,
}

# Ordered list for worker polling — high checked first
POLL_ORDER: list[str] = [
    settings.queue_high,
    settings.queue_normal,
    settings.queue_low,
]


def queue_key_for(priority: JobPriority) -> str:
    """Return the Redis list key for a given priority."""
    return QUEUE_KEYS[priority]
