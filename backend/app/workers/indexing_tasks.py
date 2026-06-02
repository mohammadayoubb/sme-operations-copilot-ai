from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.workers.indexing_tasks.index_document", queue="indexing")
def index_document(document_id: int) -> dict:
    logger.info("index_document_started", document_id=document_id)
    # TODO: chunk → embed → store in Chroma (Phase 4)
    return {"document_id": document_id, "status": "pending"}
