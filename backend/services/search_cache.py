"""
Simple in-memory TTL cache for Bing search results.
Keys are hashed from query parameter dicts.
"""
import hashlib
import json
import time
from typing import Any


class TTLCache:
    def __init__(self, ttl: int = 600):
        self._store: dict[str, tuple[Any, float]] = {}
        self.ttl = ttl

    def _key(self, params: dict) -> str:
        return hashlib.md5(
            json.dumps(params, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()

    def get(self, params: dict) -> Any | None:
        key = self._key(params)
        if key in self._store:
            value, ts = self._store[key]
            if time.time() - ts < self.ttl:
                return value
            del self._store[key]
        return None

    def set(self, params: dict, value: Any) -> None:
        self._store[self._key(params)] = (value, time.time())

    def clear(self) -> None:
        self._store.clear()


# Shared instances
news_cache = TTLCache(ttl=600)    # 10 minutes for news
image_cache = TTLCache(ttl=1800)  # 30 minutes for images
