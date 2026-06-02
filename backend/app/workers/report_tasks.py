from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.workers.report_tasks.generate_weekly_report", queue="reports")
def generate_weekly_report() -> dict:
    logger.info("generate_weekly_report_started")
    # TODO: aggregate → LLM narrative → save report (Phase 5)
    return {"status": "pending"}
