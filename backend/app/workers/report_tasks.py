from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.workers.report_tasks.generate_weekly_report", queue="reports")
def generate_weekly_report() -> dict:
    """Scheduled (Mon 8am) + on-demand background job: aggregate -> narrate -> save."""
    from app.core.database import SessionLocal
    from app.services import report_service

    logger.info("generate_weekly_report_started")
    with SessionLocal() as db:
        try:
            report = report_service.generate(db)
            db.commit()
            logger.info("generate_weekly_report_done", report_id=report.id)
            return {"status": "completed", "report_id": report.id}
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            logger.error("generate_weekly_report_failed", err=str(exc))
            return {"status": "failed", "error": str(exc)}
