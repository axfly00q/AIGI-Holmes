"""
ORM model — FeedbackRecord (user-reported misjudgements).
"""

import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class FeedbackRecord(Base):
    __tablename__ = "feedback_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    detection_id: Mapped[int | None] = mapped_column(
        ForeignKey("detection_records.id"), nullable=True, index=True
    )
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reported_label: Mapped[str] = mapped_column(String(8))   # model's original prediction
    correct_label: Mapped[str] = mapped_column(String(8))    # user-supplied correction
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    used_in_training: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
