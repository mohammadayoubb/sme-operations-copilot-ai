from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.schemas.qa import IndexResponse, QARequest, QAResponse
from app.services import rag_service
from app.services.rag_service import GuardrailError

logger = get_logger(__name__)

router = APIRouter(prefix="/api/qa", tags=["Q&A"])


@router.post("/ask/stream")
def ask_stream(payload: QARequest, db: Session = Depends(get_db)):
    """Streaming version — yields sources immediately, then streams the LLM answer."""
    try:
        gen = rag_service.ask_stream(db, payload.question, top_k=payload.top_k)
        return StreamingResponse(gen, media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
    except GuardrailError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        logger.error("qa_stream_failed", err=str(exc))
        raise HTTPException(502, f"Stream failed: {exc}")


@router.post("/ask", response_model=QAResponse)
def ask_question(payload: QARequest, db: Session = Depends(get_db)):
    """Answer a business question grounded ONLY in the owner's indexed records."""
    try:
        result = rag_service.ask(db, payload.question, top_k=payload.top_k)
        return QAResponse(**result)
    except GuardrailError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.error("qa_ask_failed", err=str(exc))
        raise HTTPException(502, f"Could not answer the question: {exc}")


@router.post("/index", response_model=IndexResponse)
def trigger_indexing(db: Session = Depends(get_db)):
    """(Re)build the document index from current invoices, orders, and products.

    Runs synchronously (the dataset is small); the same work is also available as
    the `reindex_all_documents` Celery task for background/scheduled re-indexing.
    """
    try:
        result = rag_service.index_all(db)
        return IndexResponse(**result)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("qa_index_failed", err=str(exc))
        raise HTTPException(500, f"Indexing failed: {exc}")
