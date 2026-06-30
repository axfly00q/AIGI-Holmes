"""
AIGI-Holmes backend — Redis cache layer using image perceptual hash as key.
"""

import hashlib
import json

import redis.asyncio as aioredis

from backend.config import get_settings

_CACHE_TTL = 3600  # 1 hour
_KEY_PREFIX = "aigi:detect:"

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _redis


def _image_hash_key(image_bytes: bytes) -> str:
    """SHA256 of the raw image bytes — deterministic cache key."""
    digest = hashlib.sha256(image_bytes).hexdigest()
    return f"{_KEY_PREFIX}{digest}"


async def get_cached_result(image_bytes: bytes) -> dict | None:
    try:
        r = await get_redis()
        key = _image_hash_key(image_bytes)
        data = await r.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


async def set_cached_result(image_bytes: bytes, result: dict) -> None:
    try:
        r = await get_redis()
        key = _image_hash_key(image_bytes)
        await r.set(key, json.dumps(result, ensure_ascii=False), ex=_CACHE_TTL)
    except Exception:
        pass


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.close()
        _redis = None
