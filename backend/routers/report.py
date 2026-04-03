"""
AIGI-Holmes backend — report API routes.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.exceptions import AppError
from backend.models.user import User
from backend.report.generator import generate_report
from backend.report.exporter import export_pdf, export_excel

router = APIRouter(prefix="/api/report", tags=["report"])


@router.post("/generate")
async def api_generate_report(
    detection_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await generate_report(detection_id, db)
    if report is None:
        raise AppError(404, "检测记录不存在。")
    return report


@router.get("/{report_id}/export")
async def api_export_report(
    report_id: int,
    format: str = Query("pdf", pattern="^(pdf|excel)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await generate_report(report_id, db)
    if report is None:
        raise AppError(404, "检测记录不存在。")

    if format == "pdf":
        content = export_pdf(report)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=report_{report_id}.pdf"},
        )
    else:
        content = export_excel(report)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=report_{report_id}.xlsx"},
        )
