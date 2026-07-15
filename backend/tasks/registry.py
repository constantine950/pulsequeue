from __future__ import annotations

from backend.tasks.sample_tasks import (
    always_fail,
    generate_report,
    noop,
    resize_image,
    send_email,
    send_webhook,
    slow_task,
)

# task_name → async callable
REGISTRY: dict[str, callable] = {
    "send_email":      send_email,
    "generate_report": generate_report,
    "resize_image":    resize_image,
    "send_webhook":    send_webhook,
    "noop":            noop,
    "always_fail":     always_fail,
    "slow_task":       slow_task,
}


def get_task(task_name: str):
    """
    Look up a task function by name.
    Raises KeyError with a helpful message if not found.
    """
    if task_name not in REGISTRY:
        registered = ", ".join(sorted(REGISTRY.keys()))
        raise KeyError(
            f"Unknown task '{task_name}'. "
            f"Registered tasks: {registered}"
        )
    return REGISTRY[task_name]
