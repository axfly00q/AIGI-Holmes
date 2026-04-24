"""
AIGI-Holmes backend — authentication routes.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
)
from backend.config import get_settings
from backend.database import get_db
from backend.dependencies import require_role
from backend.exceptions import AuthError, ForbiddenError
from backend.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise AuthError("用户名已存在。")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id, user.role),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, body.username, body.password)
    if user is None:
        raise AuthError("用户名或密码错误。")

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id, user.role),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise AuthError("令牌类型无效。")
        user_id = int(payload["sub"])
    except Exception:
        raise AuthError("刷新令牌无效或已过期。")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthError("用户不存在。")

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id, user.role),
    )


# ── Role management ───────────────────────────────────────────────────────────

class ChangeRoleRequest(BaseModel):
    role: Literal["user", "auditor", "admin"]
    admin_password: str = Field(..., min_length=1, max_length=128)


@router.patch("/admin/users/{username}/role")
async def change_user_role(
    username: str,
    body: ChangeRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    if body.admin_password != get_settings().ADMIN_ROLE_PASSWORD:
        raise ForbiddenError("管理密码错误。")

    result = await db.execute(select(User).where(User.username == username))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在。")
    if target.id == current_user.id and body.role != "admin":
        raise HTTPException(status_code=400, detail="不能将当前管理员账号降级为非管理员。")
    target.role = body.role
    await db.commit()
    await db.refresh(target)
    return {"message": "角色修改成功。", "username": target.username, "role": target.role}
