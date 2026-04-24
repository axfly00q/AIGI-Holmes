"""
ORM model — User.
"""

import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(16), default="user")  # user / auditor / admin
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Profile fields
    display_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    avatar_b64: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Privacy consent (recorded at registration)
    privacy_agreed: Mapped[bool] = mapped_column(Boolean, default=False)
