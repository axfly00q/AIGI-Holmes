"""
AIGI-Holmes backend — admin dashboard API routes.
"""

import asyncio
import os
import urllib.request
from datetime import datetime, timedelta
from typing import Optional

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import require_role
from backend.models.detection import DetectionRecord
from backend.models.feedback import FeedbackRecord
from backend.models.user import User

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/stats")
async def get_dashboard_stats(_=Depends(require_role("admin"))):
    # 连接到数据库
    async with aiosqlite.connect("aigi_holmes.db") as db:
        # 总用户数
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        # 总检测数
        cursor = await db.execute("SELECT COUNT(*) FROM detection_records")
        total_detections = (await cursor.fetchone())[0]
        
        # 今日检测数
        cursor = await db.execute("SELECT COUNT(*) FROM detection_records WHERE DATE(created_at) = DATE('now')")
        today_detections = (await cursor.fetchone())[0]
        
        # 最近7天每日检测量
        daily_stats = []
        for i in range(7):
            cursor = await db.execute(
                "SELECT DATE(created_at), COUNT(*) FROM detection_records WHERE DATE(created_at) = DATE('now', ?)",
                (f"-{6-i} days",)
            )
            row = await cursor.fetchone()
            date_str = (datetime.now().date() - timedelta(days=6-i)).strftime("%Y-%m-%d")
            count = row[1] if row else 0
            daily_stats.append({"date": date_str, "count": count})
        
        # 造假率 Top 5
        cursor = await db.execute("""
            SELECT image_url, COUNT(*) as total, 
                   SUM(CASE WHEN confidence > 50 THEN 1 ELSE 0 END) as fake_count
            FROM detection_records 
            WHERE image_url IS NOT NULL 
            GROUP BY image_url 
            ORDER BY COUNT(*) DESC 
            LIMIT 5
        """)
        rows = await cursor.fetchall()
        scenes = []
        for row in rows:
            url = row[0]
            total = row[1]
            fake = row[2] or 0
            fake_rate = round(fake / total * 100, 1) if total > 0 else 0
            scenes.append({
                "source": url[:50] + "..." if len(url) > 50 else url,
                "total": total,
                "fake_rate": fake_rate
            })
    
    return {
        "total_users": total_users,
        "total_detections": total_detections,
        "today_detections": today_detections,
        "daily_stats": daily_stats,
        "top_fake_scenes": scenes
    }


@router.get("/users")
async def get_all_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=100),
    role: Optional[str] = Query(None, max_length=20),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """获取所有用户列表（分页 / 用户名搜索 / 角色筛选）"""
    offset = (page - 1) * page_size

    # Build dynamic filter
    conditions = []
    if search:
        conditions.append(User.username.ilike(f"%{search}%"))
    if role in ("admin", "auditor", "user"):
        conditions.append(User.role == role)

    base_q = select(User)
    if conditions:
        base_q = base_q.where(and_(*conditions))

    total = await db.scalar(select(func.count()).select_from(base_q.subquery()))

    result = await db.execute(
        base_q
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    users = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "role": u.role,
                "created_at": u.created_at.isoformat()
            }
            for u in users
        ],
    }



@router.get("/detections")
async def get_all_detections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=100),
    label: Optional[str] = Query(None, max_length=10),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """获取所有检测记录（分页 / 来源搜索 / 标签筛选）"""
    offset = (page - 1) * page_size

    conditions = []
    if search:
        conditions.append(
            or_(
                DetectionRecord.image_url.ilike(f"%{search}%"),
                DetectionRecord.label.ilike(f"%{search}%"),
            )
        )
    if label in ("FAKE", "REAL"):
        conditions.append(DetectionRecord.label == label)

    base_q = select(DetectionRecord)
    if conditions:
        base_q = base_q.where(and_(*conditions))

    total = await db.scalar(select(func.count()).select_from(base_q.subquery()))

    result = await db.execute(
        base_q
        .order_by(DetectionRecord.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    records = result.scalars().all()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "detections": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "image_url": r.image_url[:80] + "..." if r.image_url and len(r.image_url) > 80 else r.image_url,
                "label": r.label,
                "confidence": r.confidence,
                "model_version": r.model_version,
                "created_at": r.created_at.isoformat()
            }
            for r in records
        ]
    }


# ---------------------------------------------------------------------------
# Per-image error-rate statistics
# ---------------------------------------------------------------------------

@router.get("/image-stats/{detection_id}")
async def get_image_stats(
    detection_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """Return detection & feedback statistics for the image associated with detection_id."""
    result = await db.execute(
        select(DetectionRecord).where(DetectionRecord.id == detection_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="检测记录不存在")

    image_hash = record.image_hash
    image_url = record.image_url

    async with aiosqlite.connect("aigi_holmes.db") as conn:
        cur = await conn.execute(
            "SELECT COUNT(*) FROM detection_records WHERE image_hash = ?", (image_hash,)
        )
        total_detections = (await cur.fetchone())[0]

        cur = await conn.execute(
            "SELECT COUNT(*) FROM detection_records WHERE image_hash = ? AND label = 'FAKE'",
            (image_hash,),
        )
        fake_count = (await cur.fetchone())[0]

        cur = await conn.execute(
            "SELECT COUNT(*) FROM detection_records WHERE image_hash = ? AND label = 'REAL'",
            (image_hash,),
        )
        real_count = (await cur.fetchone())[0]

        # feedback_records table may not exist on very first startup; guard gracefully
        try:
            cur = await conn.execute(
                "SELECT COUNT(*) FROM feedback_records WHERE image_hash = ?", (image_hash,)
            )
            feedback_count = (await cur.fetchone())[0]

            cur = await conn.execute(
                """SELECT reported_label, correct_label, note, created_at
                   FROM feedback_records WHERE image_hash = ?
                   ORDER BY created_at DESC LIMIT 5""",
                (image_hash,),
            )
            fb_rows = await cur.fetchall()
        except Exception:
            feedback_count = 0
            fb_rows = []

    fake_rate = round(fake_count / total_detections * 100, 1) if total_detections > 0 else 0.0

    return {
        "detection_id": detection_id,
        "image_hash": image_hash,
        "image_url": image_url,
        "total_detections": total_detections,
        "fake_count": fake_count,
        "real_count": real_count,
        "fake_rate": fake_rate,
        "feedback_count": feedback_count,
        "recent_feedbacks": [
            {
                "reported_label": r[0],
                "correct_label": r[1],
                "note": r[2],
                "created_at": r[3],
            }
            for r in fb_rows
        ],
    }


# ---------------------------------------------------------------------------
# Feedback list
# ---------------------------------------------------------------------------

@router.get("/feedback")
async def get_feedback_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """Paginated list of user misjudge feedback records."""
    offset = (page - 1) * page_size

    total = await db.scalar(select(func.count()).select_from(select(FeedbackRecord).subquery()))
    result = await db.execute(
        select(FeedbackRecord)
        .order_by(FeedbackRecord.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    records = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "feedbacks": [
            {
                "id": r.id,
                "detection_id": r.detection_id,
                "image_url": (
                    r.image_url[:60] + "..." if r.image_url and len(r.image_url) > 60 else r.image_url
                ),
                "reported_label": r.reported_label,
                "correct_label": r.correct_label,
                "note": r.note,
                "user_id": r.user_id,
                "used_in_training": r.used_in_training,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ],
    }


# ---------------------------------------------------------------------------
# Integrate feedback images into training dataset
# ---------------------------------------------------------------------------

async def _download_to(url: str, path: str) -> None:
    """Download *url* to *path* in a thread-pool to keep the event loop free."""
    await asyncio.to_thread(urllib.request.urlretrieve, url, path)


@router.post("/feedback/integrate")
async def integrate_feedback_to_training(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """
    For each unused feedback record, download the image (if image_url exists) and
    save it under data/feedback/{FAKE|REAL}/ so that finetune.py can pick it up.
    Records without image_url are still marked as integrated (skipped from download).
    """
    result = await db.execute(
        select(FeedbackRecord)
        .where(FeedbackRecord.used_in_training == 0)
    )
    pending = result.scalars().all()

    if not pending:
        return {"integrated": 0, "skipped": 0, "message": "没有待集成的反馈数据"}

    integrated = 0
    skipped = 0

    for fb in pending:
        try:
            # Skip download if no image_url, but still mark as integrated
            if fb.image_url:
                label_dir = os.path.join("data", "feedback", fb.correct_label)
                os.makedirs(label_dir, exist_ok=True)
                filename = f"{fb.image_hash or fb.id}.jpg"
                filepath = os.path.join(label_dir, filename)
                if not os.path.exists(filepath):
                    await _download_to(fb.image_url, filepath)
            fb.used_in_training = 1
            integrated += 1
        except Exception:
            skipped += 1

    await db.commit()
    return {
        "integrated": integrated,
        "skipped": skipped,
        "message": f"成功集成 {integrated} 条反馈，跳过 {skipped} 条（下载失败）",
    }


# ---------------------------------------------------------------------------
# Admin template page
# ---------------------------------------------------------------------------

from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pathlib import Path

# 使用相对路径，适配不同项目环境
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))

@router.get("/page")
async def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})
