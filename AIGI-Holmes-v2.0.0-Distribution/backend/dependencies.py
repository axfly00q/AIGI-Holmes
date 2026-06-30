"""
AIGI-Holmes backend — FastAPI dependency injection for auth & permissions.
"""

from fastapi import Depends, Header
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import decode_token
from backend.database import get_db
from backend.exceptions import AuthError, ForbiddenError
from backend.models.user import User


async def get_current_user(
    authorization: str = Header(..., description="Bearer <token>"),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise AuthError("请提供有效的认证令牌。")
    token = authorization[7:]
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise AuthError("令牌类型无效。")
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise AuthError("令牌无效或已过期。")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthError("用户不存在。")
    return user


async def get_optional_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Like get_current_user but returns None when no token is provided."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return await get_current_user(authorization=authorization, db=db)
    except AuthError:
        return None


def require_role(*allowed_roles: str):
    """Return a dependency that checks the user has one of the allowed roles."""

    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise ForbiddenError(f"需要角色: {', '.join(allowed_roles)}")
        return user

    return checker
