"""
AIGI-Holmes backend — detection API routes.
"""

import asyncio
import base64
import io
import json
from functools import partial

from fastapi import APIRouter, Depends, Query, UploadFile, File
from PIL import Image
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import get_cached_result, set_cached_result
from backend.database import get_db
from backend.dependencies import get_optional_user, require_role
from backend.exceptions import ImageFormatError
from backend.models.detection import DetectionRecord
from backend.models.user import User
from detect import (
    MODEL_VERSION,
    async_download_image,
    async_fetch_image_urls,
    detect_batch,
    detect_image,
    validate_public_url,
)

router = APIRouter(prefix="/api", tags=["detection"])


# ── request / response schemas ───────────────────────────────────────────


class DetectUrlRequest(BaseModel):
    url: str


class ProbItem(BaseModel):
    label: str
    label_zh: str
    score: float


class ExplanationItem(BaseModel):
    level: str
    summary: str
    clues: list[str]
    disclaimer: str


class DetectResponse(BaseModel):
    label: str
    label_zh: str
    confidence: float
    probs: list[ProbItem]
    explanation: ExplanationItem | None = None
    cam_image: str | None = None
    detection_id: int | None = None


class UrlResultItem(BaseModel):
    index: int
    url: str
    label: str
    label_zh: str
    confidence: float
    probs: list[ProbItem]
    thumbnail: str


class DetectUrlResponse(BaseModel):
    count: int
    results: list[UrlResultItem]


# ── helpers ──────────────────────────────────────────────────────────────


async def _run_detect(img: Image.Image, with_cam: bool = False) -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(detect_image, img, with_cam=with_cam))


async def _run_detect_batch(images: list[Image.Image]) -> list[dict]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, detect_batch, images)


async def _save_record(
    db: AsyncSession, result: dict, image_hash: str, user: User | None, image_url: str | None = None
) -> DetectionRecord:
    record = DetectionRecord(
        user_id=user.id if user else None,
        image_hash=image_hash,
        image_url=image_url,
        label=result["label"],
        confidence=round(result["confidence"], 2),
        probs_json=json.dumps(result["probs"], ensure_ascii=False),
        model_version=MODEL_VERSION,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


def _image_sha256(raw: bytes) -> str:
    import hashlib
    return hashlib.sha256(raw).hexdigest()


# ── routes ───────────────────────────────────────────────────────────────


@router.post("/detect", response_model=DetectResponse)
async def api_detect(
    image: UploadFile = File(...),
    cam: int = Query(0, description="Set to 1 to include Grad-CAM heatmap"),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    raw = await image.read()
    if not raw:
        raise ImageFormatError("未上传图片")

    # cache check (skip if cam requested — cached result may lack cam_image)
    if not cam:
        cached = await get_cached_result(raw)
        if cached:
            return cached

    try:
        img = Image.open(io.BytesIO(raw))
    except Exception:
        raise ImageFormatError()

    result = await _run_detect(img, with_cam=bool(cam))

    # cache & persist (cache without cam_image to save space)
    cache_data = {k: v for k, v in result.items() if k != "cam_image"}
    await set_cached_result(raw, cache_data)
    record = await _save_record(db, result, _image_sha256(raw), user)

    return {**result, "detection_id": record.id}


@router.post("/detect-url", response_model=DetectUrlResponse)
async def api_detect_url(
    body: DetectUrlRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        raise ImageFormatError("请输入有效的新闻页面 URL（以 http 或 https 开头）。")

    try:
        img_urls = await async_fetch_image_urls(url)
    except ValueError as exc:
        raise ImageFormatError(str(exc))

    if not img_urls:
        raise ImageFormatError("未在页面中找到图片（尝试直接上传图片）。")

    results: list[dict] = []
    for i, img_url in enumerate(img_urls, 1):
        img = await async_download_image(img_url)
        if img is None:
            continue

        det = await _run_detect(img)

        # thumbnail
        buf = io.BytesIO()
        thumb = img.copy()
        thumb.thumbnail((400, 400))
        thumb.save(buf, format="JPEG", quality=80)
        b64 = base64.b64encode(buf.getvalue()).decode()

        item = {
            "index": i,
            "url": img_url,
            "label": det["label"],
            "label_zh": det["label_zh"],
            "confidence": round(det["confidence"], 1),
            "probs": [{**p, "score": round(p["score"], 1)} for p in det["probs"]],
            "explanation": det.get("explanation"),
            "thumbnail": f"data:image/jpeg;base64,{b64}",
        }
        results.append(item)

        # persist
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        await _save_record(db, det, _image_sha256(img_bytes.getvalue()), user, image_url=img_url)

    if not results:
        raise ImageFormatError("下载图片失败，请检查网络或尝试直接上传图片。")

    return {"count": len(results), "results": results}


@router.post("/detect-batch")
async def api_detect_batch(
    images: list[UploadFile] = File(...),
    user: User = Depends(require_role("auditor", "admin")),
    db: AsyncSession = Depends(get_db),
):
    pil_images: list[Image.Image] = []
    raw_list: list[bytes] = []

    for upload in images:
        raw = await upload.read()
        if not raw:
            continue
        try:
            pil_images.append(Image.open(io.BytesIO(raw)))
            raw_list.append(raw)
        except Exception:
            continue

    if not pil_images:
        raise ImageFormatError("未上传有效图片。")

    # check cache for each
    results: list[dict] = []
    uncached_indices: list[int] = []
    uncached_images: list[Image.Image] = []

    for idx, raw in enumerate(raw_list):
        cached = await get_cached_result(raw)
        if cached:
            results.append(cached)
        else:
            results.append(None)  # type: ignore[arg-type]
            uncached_indices.append(idx)
            uncached_images.append(pil_images[idx])

    # batch inference for uncached
    if uncached_images:
        batch_results = await _run_detect_batch(uncached_images)
        for i, idx in enumerate(uncached_indices):
            results[idx] = batch_results[i]
            await set_cached_result(raw_list[idx], batch_results[i])

    # persist all
    for idx, result in enumerate(results):
        await _save_record(db, result, _image_sha256(raw_list[idx]), user)

    return {"count": len(results), "results": results}
