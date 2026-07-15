from __future__ import annotations

import asyncio
import random


async def send_email(payload: dict) -> dict:
    to = payload.get("to", "unknown")
    subject = payload.get("subject", "(no subject)")

    # Simulate network latency
    await asyncio.sleep(random.uniform(0.1, 0.5))

    # Simulate occasional failure for retry demo
    if random.random() < 0.2:
        raise ConnectionError(
            f"SMTP server refused connection while sending to {to}")

    return {
        "delivered_to": to,
        "subject": subject,
        "message_id": f"msg-{random.randint(10000, 99999)}@pulsequeue.local",
    }


async def generate_report(payload: dict) -> dict:
    report_type = payload.get("type", "generic")
    report_id = payload.get("report_id", 0)

    # Simulate heavy processing
    await asyncio.sleep(random.uniform(1.0, 3.0))

    return {
        "report_id": report_id,
        "type": report_type,
        "rows_processed": random.randint(1000, 50000),
        "output_path": f"/reports/{report_type}-{report_id}.pdf",
    }


async def resize_image(payload: dict) -> dict:
    image_url = payload.get("url", "")
    width = payload.get("width", 800)
    height = payload.get("height", 600)

    await asyncio.sleep(random.uniform(0.2, 1.0))

    return {
        "original_url": image_url,
        "resized_url": image_url.replace(".", f"-{width}x{height}."),
        "width": width,
        "height": height,
    }


async def send_webhook(payload: dict) -> dict:
    """Simulate outgoing webhook delivery."""
    url = payload.get("url", "")
    event = payload.get("event", "unknown")

    await asyncio.sleep(random.uniform(0.05, 0.3))

    # 10% failure rate
    if random.random() < 0.1:
        raise TimeoutError(f"Webhook delivery to {url} timed out after 30s")

    return {"url": url, "event": event, "http_status": 200}


async def noop(payload: dict) -> dict:
    """No-op task used for scheduler heartbeat and testing."""
    return {"msg": payload.get("msg", "ok")}


async def always_fail(payload: dict) -> dict:
    """Always raises — used to test retry and dead letter queue."""
    raise RuntimeError(f"Task always_fail intentionally failed: {payload}")


async def slow_task(payload: dict) -> dict:
    """Sleeps longer than default timeout — used to test timeout handling."""
    duration = payload.get("duration", 400)
    await asyncio.sleep(duration)
    return {"slept": duration}
