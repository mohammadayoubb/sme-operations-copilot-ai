"""Drift monitoring service.

Queries sales history from the DB, computes PSI across the baseline and
recent windows, stores a DriftSignal row, and returns a summary.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.drift import PSI_ALERT, PSI_WARNING, compute_psi, psi_status
from app.models.drift import DriftSignal
from app.models.sales import Sale

BASELINE_DAYS = 60
RECENT_DAYS = 7


def _daily_totals(db: Session, start: date, end: date) -> list[float]:
    """Return list of per-day total quantities sold in [start, end]."""
    rows = (
        db.query(Sale.sale_date, Sale.quantity)
        .filter(Sale.sale_date >= start, Sale.sale_date <= end)
        .all()
    )
    daily: dict[date, float] = defaultdict(float)
    for row in rows:
        daily[row.sale_date] += float(row.quantity or 0)
    return list(daily.values())


def run_drift_check(db: Session) -> DriftSignal:
    """Compute PSI between baseline and recent windows, persist and return the signal."""
    today = date.today()
    recent_start = today - timedelta(days=RECENT_DAYS)
    baseline_start = today - timedelta(days=BASELINE_DAYS + RECENT_DAYS)
    baseline_end = today - timedelta(days=RECENT_DAYS + 1)

    baseline = _daily_totals(db, baseline_start, baseline_end)
    recent = _daily_totals(db, recent_start, today)

    psi = compute_psi(baseline, recent)
    status = psi_status(psi)

    signal = DriftSignal(
        psi_score=psi,
        status=status,
        baseline_days=BASELINE_DAYS,
        recent_days=RECENT_DAYS,
        feature_stats={
            "daily_sales_volume": {
                "psi": psi,
                "status": status,
                "baseline_n_days": len(baseline),
                "recent_n_days": len(recent),
                "thresholds": {"warning": PSI_WARNING, "alert": PSI_ALERT},
            }
        },
    )
    db.add(signal)
    return signal


def get_latest(db: Session) -> Optional[DriftSignal]:
    return (
        db.query(DriftSignal)
        .order_by(DriftSignal.run_at.desc())
        .first()
    )
