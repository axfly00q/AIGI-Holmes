"""
AIGI-Holmes backend — user profile management routes.
Handles: GET/PATCH /api/me (profile, username, password, deactivate)
"""

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import hash_password, verify_password
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.detection import DetectionRecord
from backend.models.user import User

router = APIRouter(prefix="/api/me", tags=["profile"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=64)
    bio: Optional[str] = Field(None, max_length=200)
    avatar_b64: Optional[str] = None  # base64 data-URL, client-side cropped


class ChangeUsernameRequest(BaseModel):
    new_username: str = Field(..., min_length=3, max_length=64)
    current_password: str = Field(..., min_length=1)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)


class PrivacyAgreeRequest(BaseModel):
    agreed: bool


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
async def get_my_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current user's full profile including detection count."""
    count_q = select(func.count()).where(DetectionRecord.user_id == user.id)
    total = (await db.execute(count_q)).scalar() or 0

    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_b64": user.avatar_b64,
        "role": user.role,
        "is_active": user.is_active,
        "privacy_agreed": user.privacy_agreed,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "detection_count": total,
    }


@router.patch("/profile")
async def update_my_profile(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update display_name, bio, and/or avatar."""
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.bio is not None:
        user.bio = body.bio
    if body.avatar_b64 is not None:
        # ~500 KB limit after base64 encoding
        if len(body.avatar_b64) > 700_000:
            raise HTTPException(status_code=400, detail="头像文件过大，请压缩后重试（最大约 500 KB）。")
        user.avatar_b64 = body.avatar_b64 if body.avatar_b64 else None
    await db.commit()
    return {"message": "个人资料已更新。"}


@router.patch("/username")
async def change_my_username(
    body: ChangeUsernameRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change username after verifying current password."""
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码错误。")

    existing = await db.execute(select(User).where(User.username == body.new_username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该用户名已被使用。")

    user.username = body.new_username
    await db.commit()
    return {"message": "用户名已更改。", "username": user.username}


@router.patch("/password")
async def change_my_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password after verifying old password."""
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误。")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": "密码已修改，请重新登录。"}


@router.patch("/privacy")
async def update_privacy_agreement(
    body: PrivacyAgreeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record user privacy agreement."""
    user.privacy_agreed = body.agreed
    await db.commit()
    return {"message": "已记录隐私协议状态。"}


@router.delete("")
async def deactivate_my_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-deactivate the account (sets is_active=False)."""
    user.is_active = False
    await db.commit()
    return {"message": "账号已停用，如需恢复请联系管理员。"}


# ── History helpers under /api/me ─────────────────────────────────────────────

@router.get("/history/stats")
async def get_my_history_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregate stats for current user's detection history."""
    from sqlalchemy import case

    total_q = select(func.count()).where(DetectionRecord.user_id == user.id)
    total = (await db.execute(total_q)).scalar() or 0

    fake_q = select(func.count()).where(
        DetectionRecord.user_id == user.id,
        DetectionRecord.label == "FAKE",
    )
    fake = (await db.execute(fake_q)).scalar() or 0

    real_q = select(func.count()).where(
        DetectionRecord.user_id == user.id,
        DetectionRecord.label == "REAL",
    )
    real = (await db.execute(real_q)).scalar() or 0

    return {"total": total, "fake": fake, "real": real}


@router.delete("/history")
async def clear_my_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all detection records for the current user."""
    from sqlalchemy import delete as sa_delete

    await db.execute(
        sa_delete(DetectionRecord).where(DetectionRecord.user_id == user.id)
    )
    await db.commit()
    return {"message": "检测历史已清除。"}


@router.get("/history/export")
async def export_my_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all detection records as a CSV file download."""
    q = (
        select(DetectionRecord)
        .where(DetectionRecord.user_id == user.id)
        .order_by(DetectionRecord.created_at.desc())
    )
    rows = (await db.execute(q)).scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "图片来源", "检测结果", "置信度(%)", "检测时间"])
    for r in rows:
        writer.writerow([
            r.id,
            r.image_url or "",
            r.label or "",
            f"{r.confidence:.1f}" if r.confidence is not None else "",
            r.created_at.isoformat() if r.created_at else "",
        ])

    buf.seek(0)
    filename = f"aigi_history_{user.username}.csv"
    return StreamingResponse(
        iter([buf.getvalue().encode("utf-8-sig")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
