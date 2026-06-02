from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.workers.forecast_tasks.retrain_forecasting_model", queue="forecasting")
def retrain_forecasting_model() -> dict:
    logger.info("retrain_forecasting_model_started")
    # TODO: feature engineering → train → save artifact (Phase 3)
    return {"status": "pending"}
