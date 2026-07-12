from backend.config import settings
from backend.models.job import JobPriority

# Priority → Redis list key
QUEUE_KEYS: dict[JobPriority, str] = {
    JobPriority.high:   settings.queue_high,
    JobPriority.normal: settings.queue_normal,
    JobPriority.low:    settings.queue_low,
}

# Ordered list for BRPOP — high checked first
POLL_ORDER: list[str] = [
    settings.queue_high,
    settings.queue_normal,
    settings.queue_low,
]


def queue_key_for(priority: JobPriority) -> str:
    """Return the Redis list key for a given priority."""
    return QUEUE_KEYS[priority]


def priority_label(queue_key: str) -> str:
    """Reverse lookup — queue key → priority label (for logging)."""
    reverse = {v: k.value for k, v in QUEUE_KEYS.items()}
    return reverse.get(queue_key, "unknown")
