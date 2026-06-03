"""Pydantic schemas for weekly business reports."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class ReportOut(BaseModel):
    id: int
    period_start: Optional[date]
    period_end: Optional[date]
    report_type: str
    summary_text: Optional[str]
    data_json: Optional[dict] = None
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ReportListItem(BaseModel):
    id: int
    period_start: Optional[date]
    period_end: Optional[date]
    report_type: str
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}
