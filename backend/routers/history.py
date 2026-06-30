"""
AIGI-Holmes backend — user detection history routes.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.detection import DetectionRecord
from backend.models.user import User

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
async def get_my_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    label: str = Query("", description="Filter by label: FAKE or REAL"),
    search: str = Query("", description="Search by image URL"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current user's detection history (paginated)."""
    base = select(DetectionRecord).where(DetectionRecord.user_id == user.id)

    if label:
        base = base.where(DetectionRecord.label == label)
    if search:
        base = base.where(DetectionRecord.image_url.ilike(f"%{search}%"))

    # Total count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginated results
    q = base.order_by(DetectionRecord.created_at.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "records": [
            {
                "id": r.id,
                "image_url": r.image_url,
                "label": r.label,
                "confidence": r.confidence,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
