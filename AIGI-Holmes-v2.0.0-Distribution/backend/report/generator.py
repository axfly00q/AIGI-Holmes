"""
AIGI-Holmes backend — structured report generation from detection records.
"""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.detection import DetectionRecord


async def generate_report(detection_id: int, db: AsyncSession) -> dict:
    """Build a structured report dict from a persisted DetectionRecord."""
    result = await db.execute(
        select(DetectionRecord).where(DetectionRecord.id == detection_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        return None  # type: ignore[return-value]

    probs = json.loads(record.probs_json)

    conclusion = "该图片为 AI 生成内容" if record.label == "FAKE" else "该图片为真实照片"
    suggestion = (
        "建议进一步核实图片来源，标注为 AI 生成内容。"
        if record.label == "FAKE"
        else "图片真实性评估通过，无需额外操作。"
    )

    return {
        "id": record.id,
        "conclusion": conclusion,
        "label": record.label,
        "confidence": record.confidence,
        "probs": probs,
        "suggestion": suggestion,
        "model_version": record.model_version,
        "image_hash": record.image_hash,
        "image_url": record.image_url,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
