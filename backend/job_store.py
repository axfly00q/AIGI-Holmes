"""
AIGI-Holmes backend — in-memory job store for batch-detection progress.

Each job has an asyncio.Queue that the detection endpoint pushes events into,
and the WebSocket endpoint consumes from.  Jobs auto-expire after 10 minutes.
"""

import asyncio
from uuid import uuid4

_jobs: dict[str, dict] = {}


def create_job(user_id: int) -> str:
    """Create a new job and return its ID."""
    job_id = uuid4().hex
    queue: asyncio.Queue = asyncio.Queue()
    _jobs[job_id] = {"queue": queue, "user_id": user_id}

    # Schedule automatic cleanup after 10 minutes
    loop = asyncio.get_running_loop()
    loop.call_later(600, _expire_job, job_id)
    return job_id


def get_job(job_id: str) -> dict | None:
    """Return the job dict or None if not found / expired."""
    return _jobs.get(job_id)


def cleanup_job(job_id: str) -> None:
    """Remove a completed job from the store."""
    _jobs.pop(job_id, None)


def _expire_job(job_id: str) -> None:
    """Called by the event-loop timer to garbage-collect stale jobs."""
    _jobs.pop(job_id, None)
