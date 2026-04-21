"""
Serper.dev Search API client for news and image search.
https://serper.dev
"""
import os

import httpx


def _get_key() -> str:
    key = os.getenv("SERPER_API_KEY", "").strip()
    if not key:
        raise ValueError("SERPER_API_KEY 未配置，请在 .env 文件中设置")
    return key


async def search_news(
    q: str,
    page: int = 0,
    sort: str | None = None,
) -> dict:
    """Call Serper News Search API."""
    key = _get_key()
    payload = {
        "q": q,
        "page": page,
    }
    if sort:
        payload["sort"] = sort  # date, relevance

    async with httpx.AsyncClient(timeout=12) as client:
        r = await client.post(
            "https://google.serper.dev/news",
            headers={
                "X-API-Key": key,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        r.raise_for_status()
        return r.json()


async def search_images(
    q: str,
    page: int = 0,
) -> dict:
    """Call Serper Image Search API."""
    key = _get_key()
    payload = {
        "q": q,
        "page": page,
    }

    async with httpx.AsyncClient(timeout=12) as client:
        r = await client.post(
            "https://google.serper.dev/images",
            headers={
                "X-API-Key": key,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        r.raise_for_status()
        return r.json()
