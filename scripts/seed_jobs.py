"""
scripts/seed_jobs.py

Seeds the queue with jobs at all three priority levels to verify
that the worker executes high -> normal -> low in order.

Usage (with server running):
    python scripts/seed_jobs.py
"""

import json
import sys
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"


def post_job(task_name: str, payload: dict, priority: str, label: str) -> dict:
    data = json.dumps({
        "task_name": task_name,
        "payload": payload,
        "priority": priority,
    }).encode()

    req = urllib.request.Request(
        f"{BASE_URL}/jobs",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            print(f"  [{priority:6}] {label} -> {result['id']}")
            return result
    except urllib.error.HTTPError as e:
        print(f"  ERROR: {e.code} {e.read().decode()}", file=sys.stderr)
        return {}


def main():
    print("=== PulseQueue Priority Test ===")
    print(f"Target: {BASE_URL}\n")
    print("Enqueueing LOW then NORMAL then HIGH.")
    print("Worker should execute HIGH -> NORMAL -> LOW.\n")

    post_job("noop", {"msg": "low-1"},    "low",    "Low job 1")
    post_job("noop", {"msg": "low-2"},    "low",    "Low job 2")
    post_job("noop", {"msg": "low-3"},    "low",    "Low job 3")
    post_job("noop", {"msg": "normal-1"}, "normal", "Normal job 1")
    post_job("noop", {"msg": "normal-2"}, "normal", "Normal job 2")
    post_job("noop", {"msg": "high-1"},   "high",   "High job 1")
    post_job("send_email", {"to": "vip@example.com"}, "high", "High email")

    print("\nDone. Watch the worker terminal for execution order.")
    print(f'\nVerify: curl "{BASE_URL}/jobs?limit=20"')


if __name__ == "__main__":
    main()
