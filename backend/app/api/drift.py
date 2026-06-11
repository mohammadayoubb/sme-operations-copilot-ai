from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.services import drift_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/drift", tags=["Drift"])


class DriftSignalOut(BaseModel):
    id: int
    run_at: datetime
    psi_score: float
    status: str
    baseline_days: Optional[int] = None
    recent_days: Optional[int] = None
    feature_stats: Optional[dict] = None

    model_config = {"from_attributes": True}


@router.get("/latest", response_model=Optional[DriftSignalOut])
def latest_drift(db: Session = Depends(get_db)):
    """Return the most recent drift signal, or null if none has been run yet."""
    return drift_service.get_latest(db)


@router.post("/run", response_model=DriftSignalOut, status_code=201)
def run_drift(db: Session = Depends(get_db)):
    """Run a drift check now and persist the result."""
    try:
        signal = drift_service.run_drift_check(db)
        db.commit()
        db.refresh(signal)
        return signal
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("drift_run_failed", err=str(exc))
        raise HTTPException(502, f"Drift check failed: {exc}")
