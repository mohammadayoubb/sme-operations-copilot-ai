"""Report persistence helpers."""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report import Report


def create_report(
    db: Session,
    business_id: int,
    *,
    period_start: date,
    period_end: date,
    summary_text: str,
    data_json: dict,
    report_type: str = "weekly",
) -> Report:
    report = Report(
        business_id=business_id,
        period_start=period_start,
        period_end=period_end,
        report_type=report_type,
        summary_text=summary_text,
        data_json=data_json,
    )
    db.add(report)
    db.flush()
    return report


def list_reports(db: Session, business_id: Optional[int] = None) -> list[Report]:
    stmt = select(Report).order_by(Report.created_at.desc(), Report.id.desc())
    if business_id is not None:
        stmt = stmt.where(Report.business_id == business_id)
    return list(db.execute(stmt).scalars().all())


def get_latest(db: Session, business_id: Optional[int] = None) -> Optional[Report]:
    stmt = select(Report).order_by(Report.created_at.desc(), Report.id.desc()).limit(1)
    if business_id is not None:
        stmt = stmt.where(Report.business_id == business_id)
    return db.execute(stmt).scalar_one_or_none()


def get(db: Session, report_id: int) -> Optional[Report]:
    return db.get(Report, report_id)
