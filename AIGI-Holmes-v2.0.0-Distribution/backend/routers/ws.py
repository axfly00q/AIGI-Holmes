"""
AIGI-Holmes backend — WebSocket endpoint for real-time batch-detection progress.

The client opens a WS connection after calling /api/detect-batch-init.
This endpoint authenticates via ``?token=<jwt>`` query-param, then streams
events from the job's asyncio.Queue until the job completes.
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError

from backend.auth import decode_token
from backend.job_store import get_job

router = APIRouter()
logger = logging.getLogger("backend.ws")


@router.websocket("/ws/detect/{job_id}")
async def ws_detect_progress(websocket: WebSocket, job_id: str, token: str = Query("")):
    # ── authenticate ──────────────────────────────────────────
    if not token:
        logger.info("WS rejected: missing token for job %s", job_id)
        await websocket.close(code=4001, reason="缺少 token")
        return

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001, reason="令牌类型无效")
            return
        user_id = int(payload["sub"])
        role = payload.get("role", "")
    except (JWTError, KeyError, ValueError):
        logger.info("WS rejected: invalid token for job %s", job_id)
        await websocket.close(code=4001, reason="令牌无效或已过期")
        return

    if role not in ("auditor", "admin"):
        logger.info("WS rejected: insufficient role '%s' for user %s on job %s", role, user_id, job_id)
        await websocket.close(code=4003, reason="权限不足")
        return

    # ── find job ──────────────────────────────────────────────
    job = get_job(job_id)
    if job is None or job["user_id"] != user_id:
        logger.info("WS rejected: job missing or ownership mismatch for job %s (expected user %s)", job_id, user_id)
        await websocket.close(code=4004, reason="任务不存在")
        return

    logger.info("WS accepted for job %s user %s", job_id, user_id)
    await websocket.accept()

    queue: asyncio.Queue = job["queue"]
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
            if event.get("type") == "complete":
                break
    except WebSocketDisconnect:
        logger.info("WS disconnected for job %s user %s", job_id, user_id)
    except Exception:
        logger.exception("WS exception for job %s user %s", job_id, user_id)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
