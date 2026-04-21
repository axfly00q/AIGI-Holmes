"""
ORM model — DetectionRecord.
"""

import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class DetectionRecord(Base):
    __tablename__ = "detection_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    image_hash: Mapped[str] = mapped_column(String(64), index=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    label: Mapped[str] = mapped_column(String(8))
    confidence: Mapped[float] = mapped_column(Float)
    probs_json: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TextDetectionRecord(Base):
    """文本 AI 生成检测记录（含 XAI 解释结果）"""
    __tablename__ = "text_detection_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    text_hash: Mapped[str] = mapped_column(String(64), index=True)
    text_content: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(String(8))
    confidence: Mapped[float] = mapped_column(Float)
    probs_json: Mapped[str] = mapped_column(Text)
    lime_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    shap_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    xai_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    highlighted_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
