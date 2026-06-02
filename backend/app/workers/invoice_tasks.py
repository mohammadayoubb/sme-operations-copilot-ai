from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.workers.invoice_tasks.process_invoice", queue="ocr")
def process_invoice(invoice_id: int) -> dict:
    logger.info("process_invoice_started", invoice_id=invoice_id)
    # TODO: OCR → LLM extraction → DB save (Phase 1)
    return {"invoice_id": invoice_id, "status": "pending"}
