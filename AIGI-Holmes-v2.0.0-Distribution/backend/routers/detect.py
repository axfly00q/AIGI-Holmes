"""
AIGI-Holmes backend — detection API routes.
"""

import asyncio
import base64
import io
import json
import os
from functools import partial

from fastapi import APIRouter, Depends, Query, UploadFile, File, BackgroundTasks
from PIL import Image
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.cache import get_cached_result, set_cached_result
from backend.database import get_db
from backend.dependencies import get_optional_user, require_role
from backend.exceptions import ImageFormatError
from backend.job_store import create_job, get_job, cleanup_job
from backend.models.detection import DetectionRecord
from backend.models.user import User
from detect import (
    MODEL_VERSION,
    async_download_image,
    async_fetch_image_urls,
    async_fetch_page_content,
    detect_batch,
    detect_image,
    validate_public_url,
)
from detect_text import extract_images_from_file
from backend.clip_classify import classify_image, classify_text_image_consistency

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
    category: str | None = None
    consistency: dict | None = None


class DetectUrlResponse(BaseModel):
    count: int
    results: list[UrlResultItem]
    page_title: str | None = None
    page_summary: str | None = None
    overall_score: float | None = None
    dimensions: dict | None = None


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
        page_content = await async_fetch_page_content(url)
    except ValueError as exc:
        raise ImageFormatError(str(exc))

    img_urls = page_content["img_urls"]
    page_title = page_content.get("title", "")
    page_summary = page_content.get("summary", "")
    article_text = page_content.get("article_text", "")

    if not img_urls:
        raise ImageFormatError("未在页面中找到图片（尝试直接上传图片）。")

    results: list[dict] = []
    consistency_scores: list[float] = []
    category_counts: dict[str, int] = {}
    total_confidence: float = 0
    fake_count: int = 0

    for i, img_url in enumerate(img_urls, 1):
        img = await async_download_image(img_url)
        if img is None:
            continue

        det = await _run_detect(img)

        # CLIP classification
        loop = asyncio.get_running_loop()
        category = await loop.run_in_executor(None, classify_image, img)
        category_counts[category] = category_counts.get(category, 0) + 1

        # Text-image consistency
        consistency = None
        if article_text:
            consistency = await loop.run_in_executor(
                None, classify_text_image_consistency, img, page_summary or article_text[:200]
            )
            consistency_scores.append(consistency["score"])

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
            "category": category,
            "consistency": consistency,
        }
        results.append(item)
        total_confidence += det["confidence"]
        if det["label"] == "FAKE":
            fake_count += 1

        # persist
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        await _save_record(db, det, _image_sha256(img_bytes.getvalue()), user, image_url=img_url)

    if not results:
        raise ImageFormatError("下载图片失败，请检查网络或尝试直接上传图片。")

    # Calculate overall dimensions
    n = len(results)
    avg_confidence = round(total_confidence / n, 1) if n else 0
    avg_consistency = round(sum(consistency_scores) / len(consistency_scores), 1) if consistency_scores else 50
    real_ratio = round((n - fake_count) / n * 100, 1) if n else 0

    dimensions = {
        "authenticity": real_ratio,
        "confidence": avg_confidence,
        "consistency": avg_consistency,
        "image_count": n,
        "fake_count": fake_count,
        "real_count": n - fake_count,
        "categories": category_counts,
    }

    overall_score = round((real_ratio * 0.4 + avg_confidence * 0.3 + avg_consistency * 0.3), 1)

    return {
        "count": n,
        "results": results,
        "page_title": page_title,
        "page_summary": page_summary,
        "overall_score": overall_score,
        "dimensions": dimensions,
    }


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


# ── WebSocket-driven batch detection ─────────────────────────────────────

_IMG_CONTENT_TYPES = ("image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp")
_TEXT_EXTS = (".html", ".htm", ".txt", ".pdf", ".docx")


def _is_image_file(upload: UploadFile) -> bool:
    ct = (upload.content_type or "").lower()
    if ct.startswith("image/"):
        return True
    name = (upload.filename or "").lower()
    return any(name.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"))


def _is_text_file(upload: UploadFile) -> bool:
    name = (upload.filename or "").lower()
    return any(name.endswith(ext) for ext in _TEXT_EXTS)


@router.post("/detect-batch-init")
async def api_detect_batch_init(
    user: User = Depends(require_role("auditor", "admin")),
):
    job_id = create_job(user.id)
    return {"job_id": job_id}


async def _process_batch_run(
    job_id: str,
    uploads_data: list[dict],
    user_id: int,
):
    """Background coroutine: process uploaded files and push events to the job queue."""
    job = get_job(job_id)
    if job is None:
        return
    queue: asyncio.Queue = job["queue"]

    # Collect all (filename, pil_image, raw_bytes, source_file) tuples
    items: list[dict] = []

    for ud in uploads_data:
        filename = ud["filename"]
        raw = ud["content"]

        if ud["is_image"]:
            try:
                pil = Image.open(io.BytesIO(raw)).convert("RGB")
                items.append({"filename": filename, "image": pil, "raw": raw, "source": None})
            except Exception:
                continue
        elif ud["is_text"]:
            try:
                extracted = await extract_images_from_file(filename, raw)
                if not extracted:
                    await queue.put({
                        "type": "item_skip",
                        "filename": filename,
                        "reason": f"未从 {filename} 中提取到图片",
                    })
                    continue
                for idx, pil in enumerate(extracted):
                    buf = io.BytesIO()
                    pil.save(buf, format="JPEG")
                    items.append({
                        "filename": f"{filename}#img{idx + 1}",
                        "image": pil,
                        "raw": buf.getvalue(),
                        "source": filename,
                    })
            except Exception:
                await queue.put({
                    "type": "item_skip",
                    "filename": filename,
                    "reason": f"提取 {filename} 中的图片时出错",
                })
                continue
        else:
            await queue.put({
                "type": "item_skip",
                "filename": filename,
                "reason": "不支持的文件类型",
            })
            continue

    # Push start event
    await queue.put({"type": "start", "total": len(items)})

    # Process each image
    result_count = 0
    for i, item in enumerate(items):
        await queue.put({
            "type": "item",
            "index": i,
            "filename": item["filename"],
            "source": item["source"],
        })

        # Cache check
        cached = await get_cached_result(item["raw"])
        if cached:
            result = cached
        else:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, partial(detect_image, item["image"], with_cam=False)
            )
            cache_data = {k: v for k, v in result.items() if k != "cam_image"}
            await set_cached_result(item["raw"], cache_data)

        # CLIP content classification (runs in executor to avoid blocking)
        loop = asyncio.get_running_loop()
        category = await loop.run_in_executor(None, classify_image, item["image"])

        # Build thumbnail
        thumb_buf = io.BytesIO()
        thumb = item["image"].copy()
        thumb.thumbnail((400, 400))
        thumb.save(thumb_buf, format="JPEG", quality=80)
        b64 = base64.b64encode(thumb_buf.getvalue()).decode()

        result_count += 1
        await queue.put({
            "type": "result",
            "index": i,
            "filename": item["filename"],
            "source": item["source"],
            "result": {
                "label": result["label"],
                "label_zh": result["label_zh"],
                "confidence": round(result["confidence"], 1),
                "probs": [{**p, "score": round(p["score"], 1)} for p in result["probs"]],
                "thumbnail": f"data:image/jpeg;base64,{b64}",
                "category": category,
            },
        })

    await queue.put({"type": "complete", "count": result_count})
    # job_store 的 10 分钟定时器会自动清理，这里不提前删除
    # 否则 WS 在处理完成后才建立时会拿到 None（403）


@router.post("/detect-batch-run")
async def api_detect_batch_run(
    job_id: str = Query(...),
    files: list[UploadFile] = File(...),
    user: User = Depends(require_role("auditor", "admin")),
):
    job = get_job(job_id)
    if job is None or job["user_id"] != user.id:
        raise ImageFormatError("任务不存在或已过期。")

    # Read all upload content so the XHR completes and
    # upload-progress reaches 100% before background processing starts.
    uploads_data: list[dict] = []
    for upload in files[:50]:
        raw = await upload.read()
        if not raw:
            continue
        uploads_data.append({
            "filename": upload.filename or "unknown",
            "content": raw,
            "is_image": _is_image_file(upload),
            "is_text": _is_text_file(upload),
        })

    if not uploads_data:
        raise ImageFormatError("未上传有效文件。")

    # Launch processing as a background asyncio task so the HTTP response
    # returns immediately — progress is streamed via WebSocket.
    asyncio.create_task(_process_batch_run(job_id, uploads_data, user.id))

    return {"status": "processing", "file_count": len(uploads_data)}


# ── AI Analysis Endpoints ───────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    question: str


@router.get("/detection/{detection_id}/analyze")
async def api_analyze_detection(
    detection_id: int,
    question: str = Query(..., min_length=1, max_length=500),
    session_id: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    流式返回豆包AI对检测结果的分析。
    使用Server-Sent Events (SSE) 进行流式传输。
    支持多轮对话（通过session_id传入时获取历史上下文）。
    """
    from fastapi.responses import StreamingResponse
    from backend.config import get_settings
    from backend.llm.doubao_client import DoubaoClient
    from backend.session_store import get_or_create_session

    # 获取检测记录
    stmt = select(DetectionRecord).where(DetectionRecord.id == detection_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise ImageFormatError(f"检测记录 {detection_id} 不存在")

    # 转换为字典
    record_dict = {
        "label": record.label,
        "label_zh": "AI生成" if record.label == "FAKE" else "真实照片",
        "confidence": record.confidence,
        "probs": json.loads(record.probs_json) if record.probs_json else [],
    }

    # 初始化豆包客户端
    settings = get_settings()
    if not settings.DOUBAO_API_KEY:
        raise ImageFormatError("豆包AI服务未配置")

    client = DoubaoClient(settings.DOUBAO_API_KEY, model=settings.DOUBAO_MODEL)

    # 获取或创建会话
    if not session_id:
        import time
        session_id = "session_" + str(detection_id) + "_" + str(int(time.time() * 1000))

    session = get_or_create_session(session_id)

    async def event_generator():
        """SSE事件生成器，支持多轮对话"""
        full_response = ""
        try:
            # 获取该检测的历史对话，用于上下文
            conversation_history = None
            history = session.get_history_for_detection(detection_id)
            if history:
                # 转换为豆包API需要的消息格式
                conversation_history = []
                for entry in history:
                    conversation_history.append({
                        "role": "user",
                        "content": entry["question"]
                    })
                    conversation_history.append({
                        "role": "assistant",
                        "content": entry["answer"]
                    })

            async for chunk in client.stream_analysis(
                user_question=question,
                detection_result=record_dict,
                image_info=f"来源URL: {record.image_url}" if record.image_url else "",
                conversation_history=conversation_history,
            ):
                if chunk == "[DONE]":
                    # 添加到会话历史
                    session.add_entry(detection_id, question, full_response)
                    yield f"data: [DONE]\n\n"
                else:
                    full_response += chunk
                    # SSE格式：data: <content>\n\n
                    yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
        except Exception as e:
            import logging
            logging.error(f"Stream analysis error: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/image/download")
async def api_download_image(
    url: str = Query(..., min_length=1),
):
    """
    下载图片文件（支持跨域转发下载）。
    应用SSRF防护，拒绝私有IP和本地地址。
    """
    from fastapi.responses import StreamingResponse

    # SSRF 防护
    try:
        validate_public_url(url)
    except ValueError as e:
        raise ImageFormatError(f"URL验证失败：{str(e)}")

    # 下载图片
    img = await async_download_image(url)
    if img is None:
        raise ImageFormatError("无法下载图片")

    # 转为字节流
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="image/png",
        headers={"Content-Disposition": "attachment; filename=image.png"},
    )


@router.get("/detection/{detection_id}/analysis-history")
async def api_get_analysis_history(
    detection_id: int,
    session_id: str = Query(None),
):
    """
    获取指定检测的分析历史（用于多轮对话）。
    需要session_id才能获取该会话的历史。
    """
    from backend.session_store import get_session

    if not session_id:
        return {
            "detection_id": detection_id,
            "session_id": None,
            "history": [],
            "message": "未提供session_id"
        }

    session = get_session(session_id)
    if not session:
        return {
            "detection_id": detection_id,
            "session_id": session_id,
            "history": [],
            "message": "会话已过期或不存在"
        }

    history = session.get_history_for_detection(detection_id)
    return {
        "detection_id": detection_id,
        "session_id": session_id,
        "history": history,
    }


@router.get("/images/batch-download")
async def api_batch_download_images(
    urls: str = Query(..., min_length=1),
):
    """
    批量下载图片并打包为ZIP文件。
    urls 参数支持JSON数组格式：["url1", "url2", ...] 或逗号分隔格式：url1,url2,...
    """
    from fastapi.responses import FileResponse
    import zipfile
    import tempfile
    from datetime import datetime
    import shutil

    # 解析URL列表
    try:
        if urls.startswith('['):
            url_list = json.loads(urls)
        else:
            url_list = [u.strip() for u in urls.split(',') if u.strip()]
    except (json.JSONDecodeError, ValueError) as e:
        raise ImageFormatError(f"URLs格式无效：{str(e)}")

    if not url_list:
        raise ImageFormatError("未提供任何URL")

    if len(url_list) > 50:
        raise ImageFormatError("最多支持50张图片")

    # 创建临时ZIP文件
    zip_filename = f"images_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, zip_filename)

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            success_count = 0
            for i, url in enumerate(url_list, 1):
                try:
                    # SSRF防护
                    validate_public_url(url)
                    # 下载图片
                    img = await async_download_image(url)
                    if img:
                        # 保存为PNG
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        zf.writestr(f"image_{i:02d}.png", buf.getvalue())
                        success_count += 1
                except Exception as e:
                    import logging
                    logging.warning(f"Failed to download image {i}: {str(e)}")
                    # 跳过无法下载的图片，继续处理下一个

        if success_count == 0:
            raise ImageFormatError("无法下载任何图片")

        # 返回ZIP文件
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=zip_filename,
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )

    except ImageFormatError:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise ImageFormatError(f"批量下载失败：{str(e)}")


class TranslateRequest(BaseModel):
    text: str


@router.post("/translate")
async def api_translate(body: TranslateRequest):
    """
    将文本翻译为中文（使用豆包AI）。
    """
    from fastapi.responses import StreamingResponse
    from backend.config import get_settings
    import httpx

    settings = get_settings()
    if not settings.DOUBAO_API_KEY:
        raise ImageFormatError("豆包AI服务未配置")

    text = body.text.strip()
    if not text:
        raise ImageFormatError("文本不能为空")

    messages = [
        {
            "role": "system",
            "content": "你是一名专业翻译。请将用户提供的英文新闻摘要翻译成中文，保持专业和准确，直接输出译文，不加任何解释。",
        },
        {"role": "user", "content": text},
    ]

    headers = {
        "Authorization": f"Bearer {settings.DOUBAO_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.DOUBAO_MODEL,
        "messages": messages,
        "stream": True,
    }

    async def event_gen():
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                async with client.stream(
                    "POST",
                    "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                    json=payload,
                    headers=headers,
                ) as response:
                    if response.status_code != 200:
                        body_text = await response.aread()
                        err_msg = f'API错误 {response.status_code}: {body_text.decode(errors="replace")[:200]}'
                        yield f"data: {json.dumps({'error': err_msg}, ensure_ascii=False)}\n\n"
                        return
                    async for line in response.aiter_lines():
                        if not line.strip() or not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            data = json.loads(data_str)
                            content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                yield f"data: {json.dumps({'chunk': content}, ensure_ascii=False)}\n\n"
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
