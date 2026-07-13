"""News text classification API routes."""

from __future__ import annotations

import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user, get_optional_user
from backend.models.detection import NewsClassificationRecord
from backend.models.user import User
from backend.news_text_classify.service import (
    PredictionResult,
    get_news_classifier_service,
    text_hash,
)

router = APIRouter(prefix="/api/text-classify", tags=["news-text-classification"])


class NewsClassifyRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field("", max_length=100000)
    model_key: str = Field("best", max_length=32)


class ProbabilityItem(BaseModel):
    label: str
    score: float


class KeywordItem(BaseModel):
    word: str
    score: float


class NewsClassifyResponse(BaseModel):
    category: str
    confidence: float
    probabilities: list[ProbabilityItem]
    keywords: list[KeywordItem]
    model_key: str
    model_name: str
    model_version: str
    detection_id: Optional[int] = None


class NewsBatchItem(BaseModel):
    row: int
    title: str
    content_preview: str
    result: NewsClassifyResponse


class NewsBatchResponse(BaseModel):
    count: int
    results: list[NewsBatchItem]


def _prediction_to_response(pred: PredictionResult, detection_id: int | None = None) -> NewsClassifyResponse:
    return NewsClassifyResponse(
        category=pred.category,
        confidence=pred.confidence,
        probabilities=[ProbabilityItem(**row) for row in pred.probabilities],
        keywords=[KeywordItem(**row) for row in pred.keywords],
        model_key=pred.model_key,
        model_name=pred.model_name,
        model_version=pred.model_version,
        detection_id=detection_id,
    )


async def _save_record(
    db: AsyncSession,
    user: Optional[User],
    title: str,
    content: str,
    pred: PredictionResult,
) -> NewsClassificationRecord | None:
    if user is None:
        return None
    record = NewsClassificationRecord(
        user_id=user.id,
        text_hash=text_hash(title, content),
        title=title.strip()[:300],
        content_preview=(content or "").strip()[:500] or None,
        category=pred.category,
        confidence=pred.confidence,
        probs_json=json.dumps(pred.probabilities, ensure_ascii=False),
        keywords_json=json.dumps(pred.keywords, ensure_ascii=False),
        model_key=pred.model_key,
        model_version=pred.model_version,
    )
    db.add(record)
    await db.flush()
    return record


@router.get("/models")
async def api_get_text_classify_models():
    """Return model metadata and training metrics."""
    return get_news_classifier_service().model_options()


@router.get("/experiments")
async def api_get_text_classify_experiments():
    """Return course-style experiment metrics for the news classifier."""
    return get_news_classifier_service().experiment_report()


@router.post("/predict", response_model=NewsClassifyResponse)
async def api_text_classify_predict(
    body: NewsClassifyRequest,
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Classify one news title/body into one of the configured news categories."""
    try:
        pred = get_news_classifier_service().predict(
            title=body.title,
            content=body.content,
            model_key=body.model_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record = await _save_record(db, user, body.title, body.content, pred)
    if record is not None:
        await db.commit()
        await db.refresh(record)
    return _prediction_to_response(pred, record.id if record else None)


def _decode_csv(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="CSV 编码无法识别，请使用 UTF-8 或 GB18030。")


@router.post("/batch", response_model=NewsBatchResponse)
async def api_text_classify_batch(
    file: UploadFile = File(...),
    model_key: str = Form("best"),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Classify a CSV file with fixed columns: title, content."""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="CSV 文件为空。")
    text = _decode_csv(raw)
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = {name.strip() for name in (reader.fieldnames or []) if name}
    if "title" not in fieldnames or "content" not in fieldnames:
        raise HTTPException(status_code=400, detail="CSV 必须包含 title,content 两列。")

    rows = list(reader)
    if len(rows) > 100:
        raise HTTPException(status_code=400, detail="单次批量分类最多支持 100 条。")

    service = get_news_classifier_service()
    results: list[NewsBatchItem] = []
    try:
        for idx, row in enumerate(rows, start=1):
            title = (row.get("title") or "").strip()
            content = (row.get("content") or "").strip()
            if not title:
                continue
            pred = service.predict(title=title, content=content, model_key=model_key)
            record = await _save_record(db, user, title, content, pred)
            results.append(
                NewsBatchItem(
                    row=idx,
                    title=title,
                    content_preview=content[:80],
                    result=_prediction_to_response(pred, record.id if record else None),
                )
            )
        if user is not None:
            await db.commit()
            for item in results:
                # IDs were assigned during flush; no refresh is required for the response.
                pass
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return NewsBatchResponse(count=len(results), results=results)


@router.get("/history")
async def api_text_classify_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    category: str = Query("", description="按新闻类别过滤"),
    search: str = Query("", description="按标题搜索"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current user's news classification history."""
    base = select(NewsClassificationRecord).where(NewsClassificationRecord.user_id == user.id)
    if category:
        base = base.where(NewsClassificationRecord.category == category)
    if search:
        base = base.where(NewsClassificationRecord.title.ilike(f"%{search}%"))

    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    q = base.order_by(NewsClassificationRecord.created_at.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "records": [
            {
                "id": r.id,
                "title": r.title,
                "content_preview": r.content_preview or "",
                "category": r.category,
                "confidence": r.confidence,
                "model_key": r.model_key,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
