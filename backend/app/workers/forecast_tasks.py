from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.workers.forecast_tasks.retrain_forecasting_model", queue="forecasting")
def retrain_forecasting_model() -> dict:
    """Background job: feature-engineer all sales → train/compare models → save artifact."""
    from app.core.database import SessionLocal
    from app.services import forecasting_service

    logger.info("retrain_forecasting_model_started")
    with SessionLocal() as db:
        try:
            result = forecasting_service.train_and_save(db)
            logger.info(
                "retrain_forecasting_model_done",
                model=result["model_name"],
                path=result["model_path"],
            )
            return {
                "status": "completed",
                "model_name": result["model_name"],
                "metrics": result["metrics"],
                "trained_at": result["trained_at"],
                "n_train_rows": result["n_train_rows"],
                "model_path": result["model_path"],
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("retrain_forecasting_model_failed", err=str(exc))
            return {"status": "failed", "error": str(exc)}
