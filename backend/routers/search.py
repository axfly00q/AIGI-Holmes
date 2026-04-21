"""
Search router: Serper.dev News + Image search with in-memory caching,
plus an image proxy endpoint to solve CORS / hotlink issues.
"""
import logging

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.services.serper import search_images, search_news
from backend.services.search_cache import image_cache, news_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


# ---------------------------------------------------------------------------
# News search
# ---------------------------------------------------------------------------
@router.get("/news")
async def news_search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    offset: int = Query(0, ge=0, description="页码偏移（0-indexed）"),
    count: int = Query(10, ge=1, le=50, description="每页条数"),
):
    """搜索新闻"""
    # Serper API 以页码为单位，不是 offset
    page = offset // max(count, 1)
    cache_key = {"q": q, "page": page, "count": count}
    cached = news_cache.get(cache_key)
    if cached is not None:
        return {"source": "cache", **cached}

    try:
        data = await search_news(q=q, page=page)
    except ValueError as exc:
        logger.error("Search config error: %s", exc)
        raise HTTPException(status_code=503, detail="搜索功能未配置或配额已用尽，请检查 SERPER_API_KEY")
    except httpx.HTTPStatusError as exc:
        logger.warning("Serper News API error: %s", exc.response.status_code)
        if exc.response.status_code == 403:
            raise HTTPException(status_code=503, detail="Serper API 密钥无效或已过期，请更新配置")
        elif exc.response.status_code == 429:
            raise HTTPException(status_code=503, detail="Serper API 请求过于频繁，请稍后再试")
        else:
            raise HTTPException(status_code=502, detail=f"Serper API 返回错误: {exc.response.status_code}")
    except Exception as exc:
        logger.exception("News search failed")
        raise HTTPException(status_code=502, detail=f"联网搜索失败: {str(exc)[:100]}")

    news_cache.set(cache_key, data)
    return {"source": "api", **data}


# ---------------------------------------------------------------------------
# Image search
# ---------------------------------------------------------------------------
@router.get("/images")
async def image_search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    offset: int = Query(0, ge=0, description="页码偏移（0-indexed）"),
    count: int = Query(20, ge=1, le=50, description="每页条数"),
):
    """搜索图片"""
    # Serper API 以页码为单位
    page = offset // max(count, 1)
    cache_key = {"q": q, "page": page, "count": count}
    cached = image_cache.get(cache_key)
    if cached is not None:
        return {"source": "cache", **cached}

    try:
        data = await search_images(q=q, page=page)
    except ValueError as exc:
        logger.error("Search config error: %s", exc)
        raise HTTPException(status_code=503, detail="搜索功能未配置或配额已用尽，请检查 SERPER_API_KEY")
    except httpx.HTTPStatusError as exc:
        logger.warning("Serper Image API error: %s", exc.response.status_code)
        if exc.response.status_code == 403:
            raise HTTPException(status_code=503, detail="Serper API 密钥无效或已过期，请更新配置")
        elif exc.response.status_code == 429:
            raise HTTPException(status_code=503, detail="Serper API 请求过于频繁，请稍后再试")
        else:
            raise HTTPException(status_code=502, detail=f"Serper API 返回错误: {exc.response.status_code}")
    except Exception as exc:
        logger.exception("Image search failed")
        raise HTTPException(status_code=502, detail=f"联网搜索失败: {str(exc)[:100]}")

    image_cache.set(cache_key, data)
    return {"source": "api", **data}


# ---------------------------------------------------------------------------
# Image proxy — resolves CORS & hotlink restrictions
# ---------------------------------------------------------------------------
@router.get("/proxy/image")
async def proxy_image(url: str = Query(..., description="要代理的图片 URL")):
    """代理图片请求，解决跨域和反盗链问题"""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0 Safari/537.36"
                    ),
                    "Referer": "https://www.google.com/",
                },
            )
            content_type = r.headers.get("content-type", "image/jpeg")
            return StreamingResponse(r.aiter_bytes(), media_type=content_type)
    except Exception as exc:
        logger.warning("Image proxy failed for %s: %s", url, exc)
        raise HTTPException(status_code=502, detail="图片代理失败")
