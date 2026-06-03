from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.schemas.anomaly import AnomalyResponse
from app.services import anomaly_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/anomaly", tags=["Anomaly Detection"])


@router.get("/alerts", response_model=AnomalyResponse)
def get_anomaly_alerts(db: Session = Depends(get_db)):
    """Scan recent sales for statistical anomalies and return AI explanations.

    Uses a 14-day rolling z-score baseline. Flags any day in the past 7 days
    where sales deviated more than 2 standard deviations from the rolling mean.
    """
    try:
        result = anomaly_service.detect_all(db)
        return AnomalyResponse(**result)
    except Exception as exc:
        logger.error("anomaly_scan_failed", err=str(exc))
        raise HTTPException(500, f"Anomaly scan failed: {exc}")
