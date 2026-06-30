"""
Bing Search API client for news and image search.
"""
import os

import httpx


def _get_key() -> str:
    key = os.getenv("BING_API_KEY", "").strip()
    if not key:
        raise ValueError("BING_API_KEY 未配置，请在 .env 文件中设置")
    return key


_HEADERS_TEMPLATE = {"Ocp-Apim-Subscription-Key": ""}


async def search_news(
    q: str,
    freshness: str | None = None,
    offset: int = 0,
    count: int = 10,
) -> dict:
    """Call Bing News Search API."""
    key = _get_key()
    params: dict = {"q": q, "offset": offset, "count": count, "mkt": "zh-CN"}
    if freshness:
        params["freshness"] = freshness

    async with httpx.AsyncClient(timeout=12) as client:
        r = await client.get(
            "https://api.bing.microsoft.com/v7.0/news/search",
            headers={"Ocp-Apim-Subscription-Key": key},
            params=params,
        )
        r.raise_for_status()
        return r.json()


async def search_images(
    q: str,
    size: str | None = None,
    color: str | None = None,
    offset: int = 0,
    count: int = 20,
) -> dict:
    """Call Bing Image Search API."""
    key = _get_key()
    params: dict = {"q": q, "offset": offset, "count": count, "mkt": "zh-CN"}
    if size:
        params["size"] = size    # Small / Medium / Large / Wallpaper
    if color:
        params["color"] = color  # Black / Blue / Brown / Gray / Green / Orange / Pink / Purple / Red / Teal / White / Yellow / ColorOnly / Monochrome

    async with httpx.AsyncClient(timeout=12) as client:
        r = await client.get(
            "https://api.bing.microsoft.com/v7.0/images/search",
            headers={"Ocp-Apim-Subscription-Key": key},
            params=params,
        )
        r.raise_for_status()
        return r.json()
