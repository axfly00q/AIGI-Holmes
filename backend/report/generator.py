"""
AIGI-Holmes backend — structured report generation from detection records.
"""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.detection import DetectionRecord
from backend.detection_result import record_presentation


async def generate_report(detection_id: int, db: AsyncSession) -> dict:
    """Build a structured report dict from a persisted DetectionRecord."""
    result = await db.execute(
        select(DetectionRecord).where(DetectionRecord.id == detection_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        return None  # type: ignore[return-value]

    probs = json.loads(record.probs_json)

    presentation = record_presentation(record)
    conclusion = presentation["verdict_label_zh"]
    suggestions = {
        "likely_ai_generated": "建议核实原始来源，并由人工复核后再决定是否标注为 AI 生成。",
        "likely_authentic": "模型倾向真实，但仍建议结合原始来源和上下文进行核验。",
        "inconclusive": "模型证据不足，建议人工复核或补充来源、元数据等证据。",
    }
    suggestion = suggestions.get(presentation["verdict_code"], "该记录来自旧模型，仅供历史参考，建议重新检测。")
    signals = json.loads(record.signals_json) if record.signals_json else []

    return {
        "id": record.id,
        "conclusion": conclusion,
        "label": record.label,
        "confidence": record.confidence,
        **presentation,
        "signals": signals,
        "probs": probs,
        "suggestion": suggestion,
        "model_version": record.model_version,
        "image_hash": record.image_hash,
        "image_url": record.image_url,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
