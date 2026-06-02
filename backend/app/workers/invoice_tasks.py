from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.workers.invoice_tasks.process_invoice", queue="ocr")
def process_invoice(invoice_id: int) -> dict:
    """Background job: OCR + LLM extraction + DB save for one invoice.

    The whole save is one transaction — on any failure we roll back and mark
    the invoice 'failed' so the API can surface the error.
    """
    from app.core.database import SessionLocal
    from app.repositories import invoice_repo
    from app.services.invoice_service import process_invoice as run

    logger.info("process_invoice_started", invoice_id=invoice_id)
    with SessionLocal() as db:
        try:
            result = run(db, invoice_id)
            db.commit()
            logger.info("process_invoice_done", **result)
            return result
        except Exception as exc:  # noqa: BLE001 — we want to catch all and record
            db.rollback()
            logger.error("process_invoice_failed", invoice_id=invoice_id, error=str(exc))
            invoice = invoice_repo.get(db, invoice_id)
            if invoice is not None:
                invoice.status = "failed"
                db.commit()
            return {"invoice_id": invoice_id, "status": "failed", "error": str(exc)}
