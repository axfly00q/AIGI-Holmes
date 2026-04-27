"""
Search router: Serper.dev News + Image search with in-memory caching,
plus an image proxy endpoint to solve CORS / hotlink issues.
"""
import ipaddress
import logging
import socket
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.services.serper import search_images, search_news
from backend.services.search_cache import image_cache, news_cache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SSRF guard — block requests to private / loopback / reserved IP ranges
# ---------------------------------------------------------------------------
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),   # link-local / cloud metadata
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),      # multicast
    ipaddress.ip_network("240.0.0.0/4"),      # reserved
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _validate_proxy_url(url: str) -> None:
    """Raise HTTPException 400 if the URL targets a private/reserved address."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="仅支持 http/https 协议的图片代理")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="无效的图片 URL")
    # Resolve to IP and check against blocked ranges
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="无法解析图片 URL 的域名")
    for family, _type, _proto, _canonname, sockaddr in addr_info:
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        for net in _BLOCKED_NETWORKS:
            if ip_obj in net:
                logger.warning("SSRF blocked: %s resolved to %s", hostname, ip_str)
                raise HTTPException(status_code=400, detail="不允许代理该地址的图片")

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
    # SSRF guard: 禁止代理内网 / 保留地址
    _validate_proxy_url(url)
    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            max_redirects=3,        # 限制重定向次数，防止重定向绕过
        ) as client:
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
            # 只允许代理图片类型，防止内容注入
            if not content_type.startswith(("image/", "application/octet-stream")):
                raise HTTPException(status_code=400, detail="目标 URL 返回的不是图片内容")
            return StreamingResponse(r.aiter_bytes(), media_type=content_type)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Image proxy failed for %s: %s", url, exc)
        raise HTTPException(status_code=502, detail="图片代理失败")
