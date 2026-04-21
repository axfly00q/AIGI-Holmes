"""
AIGI-Holmes — 文本 AI 生成检测 + XAI 解释 API 路由
"""

import asyncio
import hashlib
import json
from functools import partial
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_optional_user
from backend.models.detection import TextDetectionRecord
from backend.models.user import User

router = APIRouter(prefix="/api/text", tags=["text-detection"])


# ── request / response schemas ───────────────────────────────────────────


class TextDetectRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000, description="待检测文本")
    xai_method: str = Field("lime", description="解释方法: lime, shap, both")
    num_features: int = Field(20, ge=5, le=50, description="LIME 特征数量上限")


class TokenWeight(BaseModel):
    token: str
    weight: float = 0.0
    contribution: float = 0.0
    shap_value: float = 0.0
    is_supporting_fake: bool = False
    is_important: bool = False


class ExplanationResult(BaseModel):
    method: str
    tokens: list[TokenWeight] = []
    top_positive: list[TokenWeight] = []
    top_negative: list[TokenWeight] = []
    intercept: float = 0.0
    model_score: float = 0.0
    base_value: float = 0.0
    r2_score: float = 0.0


class TextDetectResponse(BaseModel):
    label: str
    label_zh: str
    confidence: float
    probs: list[dict]
    explanations: dict = {}
    highlighted_html: str = ""
    visualization_data: dict = {}
    detection_id: Optional[int] = None


class TextDetectBatchRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=20)
    xai_method: str = Field("lime", description="解释方法: lime, shap, both, none")


class TextDetectBatchItem(BaseModel):
    index: int
    text_preview: str
    label: str
    label_zh: str
    confidence: float
    probs: list[dict]
    explanations: dict = {}
    highlighted_html: str = ""


class TextDetectBatchResponse(BaseModel):
    count: int
    results: list[TextDetectBatchItem]


# ── helpers ──────────────────────────────────────────────────────────────


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def _save_text_record(
    db: AsyncSession,
    text: str,
    result: dict,
    xai_method: str,
    explanations: dict,
    highlighted_html: str,
    user: Optional[User],
) -> TextDetectionRecord:
    detection = result.get("detection", result)
    record = TextDetectionRecord(
        user_id=user.id if user else None,
        text_hash=_text_sha256(text),
        text_content=text[:5000],  # 保存前 5000 字符
        label=detection.get("label", "UNKNOWN"),
        confidence=round(detection.get("confidence", 0.0), 2),
        probs_json=json.dumps(detection.get("probs", []), ensure_ascii=False),
        lime_json=json.dumps(explanations.get("lime", {}), ensure_ascii=False, default=str) if "lime" in explanations else None,
        shap_json=json.dumps(explanations.get("shap", {}), ensure_ascii=False, default=str) if "shap" in explanations else None,
        xai_method=xai_method,
        highlighted_html=highlighted_html[:20000] if highlighted_html else None,
        model_version="text-v1.0",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


# ── routes ───────────────────────────────────────────────────────────────


@router.post("/detect", response_model=TextDetectResponse)
async def api_text_detect(
    body: TextDetectRequest,
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    文本 AI 生成检测 + LIME/SHAP 可解释性分析

    - 检测输入文本是否由 AI 生成
    - 使用 LIME 或 SHAP 标注出影响判决的关键词汇
    - 返回高亮 HTML 和可视化数据
    """
    from backend.xai.service import get_xai_service

    xai = get_xai_service()

    # 对短文本直接解释，长文本分段
    if len(body.text) <= 512:
        result = await xai.async_explain(
            text=body.text,
            method=body.xai_method,
            num_features=body.num_features,
        )
    else:
        result = await xai.async_explain_long_text(
            text=body.text,
            method=body.xai_method,
            num_features=body.num_features,
        )

    detection = result.get("detection", {})
    explanations = result.get("explanations", {})
    highlighted_html = result.get("highlighted_html", "")
    vis_data = result.get("visualization_data", {})

    # 保存到数据库
    record = await _save_text_record(
        db, body.text, result, body.xai_method, explanations, highlighted_html, user
    )

    return TextDetectResponse(
        label=detection.get("label", "UNKNOWN"),
        label_zh=detection.get("label_zh", "未知"),
        confidence=detection.get("confidence", 0.0),
        probs=detection.get("probs", []),
        explanations=explanations,
        highlighted_html=highlighted_html,
        visualization_data=vis_data,
        detection_id=record.id,
    )


@router.post("/detect-batch", response_model=TextDetectBatchResponse)
async def api_text_detect_batch(
    body: TextDetectBatchRequest,
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """批量文本检测（可选 XAI 解释）"""
    from backend.xai.service import get_xai_service

    xai = get_xai_service()
    results = []

    for i, text in enumerate(body.texts):
        if not text.strip():
            continue

        if body.xai_method == "none":
            # 仅检测，不做解释
            from backend.text_detect import detect_text
            loop = asyncio.get_running_loop()
            det = await loop.run_in_executor(None, partial(detect_text, text=text))
            results.append(TextDetectBatchItem(
                index=i,
                text_preview=text[:100],
                label=det["label"],
                label_zh=det["label_zh"],
                confidence=det["confidence"],
                probs=det["probs"],
            ))
        else:
            result = await xai.async_explain(
                text=text, method=body.xai_method, num_features=15
            )
            detection = result.get("detection", {})
            results.append(TextDetectBatchItem(
                index=i,
                text_preview=text[:100],
                label=detection.get("label", "UNKNOWN"),
                label_zh=detection.get("label_zh", "未知"),
                confidence=detection.get("confidence", 0.0),
                probs=detection.get("probs", []),
                explanations=result.get("explanations", {}),
                highlighted_html=result.get("highlighted_html", ""),
            ))

    return TextDetectBatchResponse(count=len(results), results=results)


@router.get("/detection/{detection_id}")
async def api_get_text_detection(
    detection_id: int,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """获取文本检测记录（含 XAI 解释）"""
    from sqlalchemy import select

    result = await db.execute(
        select(TextDetectionRecord).where(TextDetectionRecord.id == detection_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="检测记录不存在")

    return {
        "id": record.id,
        "label": record.label,
        "confidence": record.confidence,
        "text_content": record.text_content,
        "probs": json.loads(record.probs_json) if record.probs_json else [],
        "xai_method": record.xai_method,
        "lime_explanation": json.loads(record.lime_json) if record.lime_json else None,
        "shap_explanation": json.loads(record.shap_json) if record.shap_json else None,
        "highlighted_html": record.highlighted_html,
        "model_version": record.model_version,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
