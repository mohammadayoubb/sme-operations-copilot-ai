from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.logging import get_logger
from app.repositories import report_repo
from app.schemas.report import ReportListItem, ReportOut
from app.services import pdf_service, report_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/", response_model=list[ReportListItem])
def list_reports(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return report_repo.list_reports(db, current_user.business_id)


@router.get("/latest", response_model=ReportOut)
def get_latest_report(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    report = report_repo.get_latest(db, current_user.business_id)
    if report is None:
        raise HTTPException(404, "No reports generated yet")
    return report


@router.get("/{report_id}/pdf")
def export_report_pdf(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    report = report_repo.get(db, report_id)
    if report is None or report.business_id != current_user.business_id:
        raise HTTPException(404, "Report not found")
    if not report.data_json:
        raise HTTPException(422, "Report has no data yet — generate it first")

    try:
        pdf_bytes = pdf_service.build_report_pdf(report)
    except Exception as exc:
        logger.error("pdf_export_failed", report_id=report_id, err=str(exc))
        raise HTTPException(502, f"PDF generation failed: {exc}")

    period = f"{report.period_start}-{report.period_end}" if report.period_start else str(report_id)
    return Response(
        content=pdf_bytes,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'inline; filename="soukpilot-report-{period}.html"'},
    )


@router.post("/generate", response_model=ReportOut)
def generate_report(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        report = report_service.generate(db, current_user.business_id)
        db.commit()
        db.refresh(report)
        return report
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("report_generate_failed", err=str(exc))
        raise HTTPException(502, f"Could not generate the report: {exc}")
