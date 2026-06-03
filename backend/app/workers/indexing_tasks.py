from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.workers.indexing_tasks.reindex_all_documents", queue="indexing")
def reindex_all_documents() -> dict:
    """Background job: rebuild the RAG document index from current business data."""
    from app.core.database import SessionLocal
    from app.services import rag_service

    logger.info("reindex_all_documents_started")
    with SessionLocal() as db:
        try:
            result = rag_service.index_all(db)
            logger.info(
                "reindex_all_documents_done",
                documents=result["documents_indexed"],
                chunks=result["chunks_indexed"],
            )
            return {"status": "completed", **result}
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            logger.error("reindex_all_documents_failed", err=str(exc))
            return {"status": "failed", "error": str(exc)}
