from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.logging import get_logger
from app.schemas.anomaly import AnomalyResponse
from app.services import anomaly_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/anomaly", tags=["Anomaly Detection"])


@router.get("/alerts", response_model=AnomalyResponse)
def get_anomaly_alerts(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        result = anomaly_service.detect_all(db, current_user.business_id)
        return AnomalyResponse(**result)
    except Exception as exc:
        logger.error("anomaly_scan_failed", err=str(exc))
        raise HTTPException(500, f"Anomaly scan failed: {exc}")
