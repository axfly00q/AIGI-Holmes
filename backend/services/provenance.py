"""Image provenance discovery, matching and timeline extraction."""

from __future__ import annotations

import asyncio
import datetime as dt
import io
import json
import logging
import math
import re
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

import httpx
import numpy as np
from bs4 import BeautifulSoup
from PIL import Image
from sqlalchemy import delete, select

from backend.clip_classify import compare_image_similarity
from backend.database import async_session_factory
from backend.models.provenance import ProvenanceEvidence, ProvenanceJob
from backend.routers.search import _validate_proxy_url
from backend.services.serper import search_images

logger = logging.getLogger(__name__)

MAX_CANDIDATES = 12
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_PAGE_BYTES = 2 * 1024 * 1024
_JOB_SEMAPHORE = asyncio.Semaphore(2)


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


def _perceptual_hash(image: Image.Image) -> int:
    """Return a compact 63-bit DCT perceptual hash."""
    import cv2

    gray = np.asarray(image.convert("L").resize((32, 32), Image.Resampling.LANCZOS), dtype=np.float32)
    dct = cv2.dct(gray)[:8, :8].flatten()[1:]
    median = float(np.median(dct))
    value = 0
    for bit in dct > median:
        value = (value << 1) | int(bit)
    return value


def _orb_geometry(first: Image.Image, second: Image.Image) -> tuple[int, float]:
    """Return RANSAC inlier count and inlier ratio for local feature matches."""
    import cv2

    def prepared(image: Image.Image) -> np.ndarray:
        image = image.convert("L")
        image.thumbnail((900, 900), Image.Resampling.LANCZOS)
        return np.asarray(image)

    a, b = prepared(first.copy()), prepared(second.copy())
    orb = cv2.ORB_create(nfeatures=1200)
    key_a, desc_a = orb.detectAndCompute(a, None)
    key_b, desc_b = orb.detectAndCompute(b, None)
    if desc_a is None or desc_b is None or len(key_a) < 8 or len(key_b) < 8:
        return 0, 0.0

    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(desc_a, desc_b, k=2)
    good = [m for pair in pairs if len(pair) == 2 for m, n in [pair] if m.distance < 0.75 * n.distance]
    if len(good) < 8:
        return 0, 0.0
    src = np.float32([key_a[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([key_b[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    _matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    if mask is None:
        return 0, 0.0
    inliers = int(mask.ravel().sum())
    return inliers, inliers / max(len(good), 1)


def compare_images(target: Image.Image, candidate: Image.Image) -> dict:
    """Classify a candidate as same, cropped, visually similar or unrelated."""
    phash_distance = (_perceptual_hash(target) ^ _perceptual_hash(candidate)).bit_count()
    clip_similarity = compare_image_similarity(target, candidate)
    orb_inliers, orb_ratio = _orb_geometry(target, candidate)

    clip_ok = clip_similarity is None or clip_similarity >= 0.82
    if phash_distance <= 10 and clip_ok:
        match_type = "same_image"
    elif clip_similarity is not None and clip_similarity >= 0.82 and orb_inliers >= 15 and orb_ratio >= 0.25:
        match_type = "cropped_version"
    elif clip_similarity is not None and clip_similarity >= 0.75:
        match_type = "visually_similar"
    else:
        match_type = "unrelated"

    phash_score = max(0.0, 1.0 - phash_distance / 32.0)
    clip_score = clip_similarity if clip_similarity is not None else phash_score
    geometry_score = min(1.0, orb_inliers / 30.0)
    combined = 100.0 * (0.45 * phash_score + 0.35 * clip_score + 0.20 * geometry_score)
    return {
        "match_type": match_type,
        "similarity_score": round(max(0.0, min(100.0, combined)), 1),
        "phash_distance": phash_distance,
        "clip_similarity": round(clip_similarity, 4) if clip_similarity is not None else None,
        "orb_inliers": orb_inliers,
    }


async def _validate_url(url: str) -> None:
    await asyncio.to_thread(_validate_proxy_url, url)


async def _fetch_limited(url: str, max_bytes: int, expected: str) -> tuple[bytes, str, str]:
    """Fetch a public URL with redirect, type and response-size validation."""
    current = url
    async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
        for _ in range(4):
            await _validate_url(current)
            async with client.stream(
                "GET",
                current,
                headers={"User-Agent": "AIGI-Holmes/3.0 provenance verifier"},
            ) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("重定向缺少目标地址")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if expected == "image" and not content_type.startswith("image/"):
                    raise ValueError("候选地址返回的不是图片")
                if expected == "html" and content_type and not (
                    "html" in content_type or "xhtml" in content_type
                ):
                    raise ValueError("来源地址返回的不是网页")
                declared = response.headers.get("content-length")
                if declared and int(declared) > max_bytes:
                    raise ValueError("响应内容过大")
                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("响应内容过大")
                    chunks.append(chunk)
                return b"".join(chunks), content_type, str(response.url)
    raise ValueError("重定向次数过多")


async def download_public_image(url: str) -> Image.Image:
    raw, _content_type, _final_url = await _fetch_limited(url, MAX_IMAGE_BYTES, "image")
    image = Image.open(io.BytesIO(raw))
    image.load()
    if image.width < 64 or image.height < 64:
        raise ValueError("候选图片尺寸过小")
    return image.convert("RGB")


def _parse_date(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    now = _utcnow()
    relative = re.search(
        r"(\d+)\s*(minute|hour|day|week|month)s?\s+ago|"
        r"(\d+)\s*(分钟|小时|天|周|个月)前",
        text,
        re.I,
    )
    if relative:
        amount = int(relative.group(1) or relative.group(3))
        unit = (relative.group(2) or relative.group(4) or "").lower()
        days = {"day": 1, "week": 7, "month": 30, "天": 1, "周": 7, "个月": 30}.get(unit)
        if days:
            return now - dt.timedelta(days=amount * days)
        minutes = amount * (60 if unit in {"hour", "小时"} else 1)
        return now - dt.timedelta(minutes=minutes)
    try:
        normalized = text.replace("Z", "+00:00")
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError, OverflowError):
            match = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", text)
            if not match:
                return None
            parsed = dt.datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return parsed


def _jsonld_dates(value) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"datePublished", "uploadDate"} and child:
                found.append(str(child))
            else:
                found.extend(_jsonld_dates(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_jsonld_dates(child))
    return found


def extract_publication_metadata(html: str, fallback_date: str | None = None) -> dict:
    """Extract publication time with an explicit evidence grade."""
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    reliable: list[tuple[str, str]] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            for value in _jsonld_dates(json.loads(script.string or "")):
                reliable.append((value, "JSON-LD datePublished"))
        except (json.JSONDecodeError, TypeError):
            continue
    for selector, source in [
        ('meta[property="article:published_time"]', "article:published_time"),
        ('meta[name="date"]', "meta date"),
        ('meta[name="pubdate"]', "meta pubdate"),
    ]:
        tag = soup.select_one(selector)
        if tag and tag.get("content"):
            reliable.append((tag["content"], source))
    for value, source in reliable:
        parsed = _parse_date(value)
        if parsed:
            return {
                "title": title,
                "published_at": parsed,
                "published_display": value,
                "date_evidence": "reliable",
                "date_source": source,
            }

    time_tag = soup.find("time", attrs={"datetime": True})
    if time_tag:
        parsed = _parse_date(time_tag.get("datetime"))
        if parsed:
            return {
                "title": title,
                "published_at": parsed,
                "published_display": time_tag.get("datetime"),
                "date_evidence": "reference",
                "date_source": "time datetime",
            }

    parsed_fallback = _parse_date(fallback_date)
    return {
        "title": title,
        "published_at": parsed_fallback,
        "published_display": fallback_date,
        "date_evidence": "reference" if parsed_fallback else "unknown",
        "date_source": "搜索摘要日期" if parsed_fallback else None,
    }


async def fetch_page_metadata(url: str, fallback_date: str | None = None) -> dict:
    try:
        raw, _content_type, _final_url = await _fetch_limited(url, MAX_PAGE_BYTES, "html")
        return extract_publication_metadata(raw.decode("utf-8", errors="replace"), fallback_date)
    except Exception as exc:
        return {
            "title": "",
            "published_at": _parse_date(fallback_date),
            "published_display": fallback_date,
            "date_evidence": "reference" if _parse_date(fallback_date) else "unknown",
            "date_source": "搜索摘要日期" if _parse_date(fallback_date) else None,
            "fetch_error": str(exc)[:200],
        }


def _candidate_values(item: dict) -> tuple[str, str | None, str, str | None]:
    image_url = item.get("imageUrl") or item.get("contentUrl") or item.get("thumbnailUrl") or ""
    page_url = item.get("link") or item.get("hostPageUrl") or item.get("sourceUrl")
    title = item.get("title") or item.get("name") or ""
    search_date = item.get("date") or item.get("datePublished")
    return image_url, page_url, title, search_date


async def _set_progress(job_id: int, phase: str, progress: float) -> None:
    async with async_session_factory() as db:
        job = await db.get(ProvenanceJob, job_id)
        if job:
            job.status = "running"
            job.phase = phase
            job.progress = progress
            await db.commit()


async def _save_evidence(job_id: int, rank: int, item: dict, match: dict, metadata: dict) -> None:
    image_url, page_url, search_title, _search_date = _candidate_values(item)
    domain = urlparse(page_url or image_url).hostname
    async with async_session_factory() as db:
        db.add(ProvenanceEvidence(
            job_id=job_id,
            rank=rank,
            source_page_url=page_url,
            image_url=image_url,
            title=metadata.get("title") or search_title or None,
            domain=domain,
            match_type=match["match_type"],
            similarity_score=match.get("similarity_score", 0.0),
            phash_distance=match.get("phash_distance"),
            clip_similarity=match.get("clip_similarity"),
            orb_inliers=match.get("orb_inliers", 0),
            published_at=metadata.get("published_at"),
            published_display=metadata.get("published_display"),
            date_evidence=metadata.get("date_evidence", "unknown"),
            date_source=metadata.get("date_source"),
            fetch_error=metadata.get("fetch_error"),
        ))
        await db.commit()


async def run_provenance_job(job_id: int) -> None:
    """Execute one persisted provenance job and retain partial evidence."""
    async with _JOB_SEMAPHORE:
        try:
            async with async_session_factory() as db:
                job = await db.get(ProvenanceJob, job_id)
                if not job:
                    return
                target_url = job.target_image_url
                source_page_url = job.source_page_url
                query_text = job.query_text
                await db.execute(delete(ProvenanceEvidence).where(ProvenanceEvidence.job_id == job_id))
                await db.commit()

            await _set_progress(job_id, "searching", 8)
            target = await download_public_image(target_url)

            # The checked page is baseline evidence and is not counted in the 12 search candidates.
            if source_page_url:
                baseline_meta = await fetch_page_metadata(source_page_url)
                await _save_evidence(job_id, 0, {
                    "imageUrl": target_url,
                    "link": source_page_url,
                    "title": baseline_meta.get("title", ""),
                }, {
                    "match_type": "same_image",
                    "similarity_score": 100.0,
                    "phash_distance": 0,
                    "clip_similarity": 1.0,
                    "orb_inliers": 0,
                }, baseline_meta)

            search_data = await search_images(q=query_text, page=0)
            raw_items = search_data.get("images") or search_data.get("value") or []
            items: list[dict] = []
            seen: set[str] = {target_url}
            for item in raw_items:
                image_url, _page_url, _title, _date = _candidate_values(item)
                if not image_url or image_url in seen:
                    continue
                seen.add(image_url)
                items.append(item)
                if len(items) >= MAX_CANDIDATES:
                    break

            async with async_session_factory() as db:
                job = await db.get(ProvenanceJob, job_id)
                if job:
                    job.candidate_count = len(items)
                    await db.commit()

            for index, item in enumerate(items, 1):
                await _set_progress(job_id, "matching", 15 + 55 * index / max(len(items), 1))
                image_url, page_url, _title, search_date = _candidate_values(item)
                metadata: dict = {"date_evidence": "unknown"}
                try:
                    candidate = await download_public_image(image_url)
                    match = await asyncio.to_thread(compare_images, target, candidate)
                    if match["match_type"] in {"same_image", "cropped_version"} and page_url:
                        await _set_progress(job_id, "building_timeline", 70 + 20 * index / max(len(items), 1))
                        metadata = await fetch_page_metadata(page_url, search_date)
                    elif search_date:
                        metadata = extract_publication_metadata("", search_date)
                except Exception as exc:
                    match = {
                        "match_type": "unrelated",
                        "similarity_score": 0.0,
                        "phash_distance": None,
                        "clip_similarity": None,
                        "orb_inliers": 0,
                    }
                    metadata = {"date_evidence": "unknown", "fetch_error": str(exc)[:200]}
                await _save_evidence(job_id, index, item, match, metadata)

            await _set_progress(job_id, "summarizing", 94)
            async with async_session_factory() as db:
                job = await db.get(ProvenanceJob, job_id)
                evidence = (await db.execute(
                    select(ProvenanceEvidence).where(
                        ProvenanceEvidence.job_id == job_id,
                        ProvenanceEvidence.match_type.in_(["same_image", "cropped_version"]),
                    )
                )).scalars().all()
                external = [e for e in evidence if e.rank > 0]
                dated = [e for e in evidence if e.published_at is not None]
                dated.sort(key=lambda item: item.published_at)
                earliest = dated[0] if dated else None
                baseline = next((e for e in evidence if e.rank == 0), None)

                if not external:
                    code = "no_verified_match"
                    conclusion = "未找到可验证的同图来源。"
                elif not any(e.published_at for e in external):
                    code = "matches_without_date"
                    conclusion = "找到同图来源，但发布时间证据不足。"
                elif baseline and baseline.published_at and earliest and earliest.published_at < baseline.published_at:
                    code = "earlier_source_found"
                    conclusion = "找到较早来源；以下为当前可发现的最早来源。"
                else:
                    code = "verified_matches_found"
                    conclusion = "找到可验证的同图来源；以下为当前可发现的最早来源。"

                if job:
                    job.status = "completed"
                    job.phase = "completed"
                    job.progress = 100
                    job.conclusion_code = code
                    job.conclusion_text = conclusion
                    job.match_count = len(evidence)
                    job.earliest_source_url = earliest.source_page_url if earliest else None
                    job.earliest_published_at = earliest.published_at if earliest else None
                    job.completed_at = _utcnow()
                    await db.commit()
        except Exception as exc:
            logger.exception("Provenance job %s failed", job_id)
            async with async_session_factory() as db:
                job = await db.get(ProvenanceJob, job_id)
                if job:
                    job.status = "failed"
                    job.phase = "failed"
                    job.conclusion_code = "failed"
                    job.conclusion_text = "来源核验失败。"
                    job.error_message = str(exc)[:300]
                    job.completed_at = _utcnow()
                    await db.commit()


def phase_label(phase: str) -> str:
    return {
        "queued": "等待开始",
        "searching": "正在搜索候选来源",
        "matching": "正在验证是否为同一图片",
        "building_timeline": "正在提取来源时间",
        "summarizing": "正在整理核验结论",
        "completed": "核验完成",
        "failed": "核验失败",
    }.get(phase, "正在核验")
