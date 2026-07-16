"""Image provenance verification routes."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.detection import DetectionRecord
from backend.models.provenance import ProvenanceEvidence, ProvenanceJob
from backend.models.user import User
from backend.services.provenance import phase_label, run_provenance_job

router = APIRouter(prefix="/api/provenance", tags=["provenance"])


class ProvenanceJobCreate(BaseModel):
    detection_id: int
    source_page_url: str | None = None
    query_text: str | None = None
    force: bool = False


def _iso(value: dt.datetime | None) -> str | None:
    return value.isoformat() if value else None


def _serialize_evidence(item: ProvenanceEvidence) -> dict:
    return {
        "id": item.id,
        "rank": item.rank,
        "source_page_url": item.source_page_url,
        "image_url": item.image_url,
        "title": item.title,
        "domain": item.domain,
        "match_type": item.match_type,
        "similarity_score": item.similarity_score,
        "phash_distance": item.phash_distance,
        "clip_similarity": item.clip_similarity,
        "orb_inliers": item.orb_inliers,
        "published_at": _iso(item.published_at),
        "published_display": item.published_display,
        "date_evidence": item.date_evidence,
        "date_source": item.date_source,
        "fetch_error": item.fetch_error,
    }


async def _serialize_job(db: AsyncSession, job: ProvenanceJob, *, reused: bool = False) -> dict:
    rows = (await db.execute(
        select(ProvenanceEvidence)
        .where(ProvenanceEvidence.job_id == job.id)
        .order_by(ProvenanceEvidence.rank.asc())
    )).scalars().all()
    evidence = [_serialize_evidence(row) for row in rows]
    matched = [row for row in evidence if row["match_type"] in {"same_image", "cropped_version"}]
    timeline = sorted(
        matched,
        key=lambda row: (
            row["published_at"] is None,
            row["published_at"] or "",
            row["rank"],
        ),
    )
    earliest = timeline[0] if timeline else None
    return {
        "id": job.id,
        "detection_id": job.detection_id,
        "status": job.status,
        "phase": job.phase,
        "phase_label": phase_label(job.phase),
        "progress": job.progress,
        "conclusion_code": job.conclusion_code,
        "conclusion_text": job.conclusion_text,
        "earliest_source": earliest,
        "earliest_source_url": job.earliest_source_url,
        "earliest_published_at": _iso(job.earliest_published_at),
        "match_count": len(matched),
        "candidate_count": job.candidate_count,
        "target_image_url": job.target_image_url,
        "source_page_url": job.source_page_url,
        "query_text": job.query_text,
        "timeline": timeline,
        "evidence": evidence,
        "error_message": job.error_message,
        "created_at": _iso(job.created_at),
        "completed_at": _iso(job.completed_at),
        "reused": reused,
    }


@router.post("/jobs")
async def create_provenance_job(
    body: ProvenanceJobCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(DetectionRecord, body.detection_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="检测记录不存在。")
    if not record.image_url:
        raise HTTPException(status_code=400, detail="第一版来源核验仅支持新闻 URL 中提取的图片。")

    active = (await db.execute(
        select(ProvenanceJob)
        .where(
            ProvenanceJob.user_id == user.id,
            ProvenanceJob.status.in_(["queued", "running"]),
        )
        .order_by(desc(ProvenanceJob.created_at))
        .limit(1)
    )).scalar_one_or_none()
    if active:
        return await _serialize_job(db, active)

    cutoff = dt.datetime.now(dt.UTC).replace(tzinfo=None) - dt.timedelta(hours=24)
    if not body.force:
        cached = (await db.execute(
            select(ProvenanceJob)
            .where(
                ProvenanceJob.user_id == user.id,
                ProvenanceJob.detection_id == record.id,
                ProvenanceJob.status == "completed",
                ProvenanceJob.completed_at >= cutoff,
            )
            .order_by(desc(ProvenanceJob.completed_at))
            .limit(1)
        )).scalar_one_or_none()
        if cached:
            return await _serialize_job(db, cached, reused=True)

    query_text = (body.query_text or body.source_page_url or record.image_url or "").strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="缺少可用于搜索候选来源的关键词。")

    job = ProvenanceJob(
        user_id=user.id,
        detection_id=record.id,
        target_image_url=record.image_url,
        source_page_url=body.source_page_url,
        query_text=query_text[:300],
        status="queued",
        phase="queued",
        progress=0.0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(run_provenance_job, job.id)
    return await _serialize_job(db, job)


@router.get("/jobs/{job_id}")
async def get_provenance_job(
    job_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(ProvenanceJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="来源核验任务不存在。")
    return await _serialize_job(db, job)
