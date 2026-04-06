"""
AIGI-Holmes backend — user feedback / misjudge report endpoints.

POST /api/feedback — submit a misjudge report for a single-image detection.
No authentication required; optionally associates report with logged-in user.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_optional_user
from backend.models.detection import DetectionRecord
from backend.models.feedback import FeedbackRecord
from backend.models.user import User

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    detection_id: int
    correct_label: str
    note: str = ""

    @field_validator("correct_label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        v = v.upper()
        if v not in ("FAKE", "REAL"):
            raise ValueError("correct_label must be FAKE or REAL")
        return v


@router.post("")
async def submit_feedback(
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """Record a misjudge report. Associates with the logged-in user when available."""
    result = await db.execute(
        select(DetectionRecord).where(DetectionRecord.id == body.detection_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="检测记录不存在")

    fb = FeedbackRecord(
        detection_id=body.detection_id,
        image_url=record.image_url,
        image_hash=record.image_hash,
        reported_label=record.label,
        correct_label=body.correct_label,
        note=body.note.strip()[:500] if body.note else None,
        user_id=user.id if user else None,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return {"message": "反馈已提交", "id": fb.id}
