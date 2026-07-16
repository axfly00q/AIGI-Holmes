"""Persisted image provenance jobs and their evidence."""

import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ProvenanceJob(Base):
    __tablename__ = "provenance_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    detection_id: Mapped[int] = mapped_column(ForeignKey("detection_records.id"), index=True)
    target_image_url: Mapped[str] = mapped_column(Text)
    source_page_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    query_text: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    phase: Mapped[str] = mapped_column(String(32), default="queued")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    conclusion_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    conclusion_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    earliest_source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    earliest_published_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    match_count: Mapped[int] = mapped_column(Integer, default=0)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ProvenanceEvidence(Base):
    __tablename__ = "provenance_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("provenance_jobs.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    source_page_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    match_type: Mapped[str] = mapped_column(String(24), index=True)
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    phash_distance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clip_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    orb_inliers: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    published_display: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_evidence: Mapped[str] = mapped_column(String(16), default="unknown")
    date_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fetch_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
