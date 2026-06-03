from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.repositories import report_repo
from app.schemas.report import ReportListItem, ReportOut
from app.services import report_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/", response_model=list[ReportListItem])
def list_reports(db: Session = Depends(get_db)):
    return report_repo.list_reports(db)


@router.get("/latest", response_model=ReportOut)
def get_latest_report(db: Session = Depends(get_db)):
    report = report_repo.get_latest(db)
    if report is None:
        raise HTTPException(404, "No reports generated yet")
    return report


@router.post("/generate", response_model=ReportOut)
def generate_report(db: Session = Depends(get_db)):
    """Aggregate this week's numbers in Python, narrate with the LLM, and save."""
    try:
        report = report_service.generate(db)
        db.commit()
        db.refresh(report)
        return report
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("report_generate_failed", err=str(exc))
        raise HTTPException(502, f"Could not generate the report: {exc}")
