"""RAG indexing + Q&A orchestration.

Indexing turns the owner's structured business data (invoices, orders, products +
sales) into plain-text summary documents, stores them in the `documents` table,
then chunks + embeds them into the vector store.

Parent-child chunking: the full document text (parent) lives in the `documents`
DB table. Small 400-char child chunks are stored in the vector store for precise
retrieval. On Q&A, we retrieve child hits, look up their parents, and pass the
full parent text to the LLM for richer context.

Ask runs guardrails, then hybrid retrieval (vector + BM25 rerank) → parent
lookup → grounded generation.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import embeddings, rag, vector_store
from app.core.logging import get_logger
from app.models.business import Supplier
from app.models.document import Document
from app.repositories import invoice_repo, order_repo, product_repo, sales_repo
from app.security import guardrails

logger = get_logger(__name__)


class GuardrailError(ValueError):
    """Raised when a question fails a guardrail check (e.g. prompt injection)."""


# ── Summary builders (plain Python — these become the indexed documents) ──

def _supplier_names(db: Session, business_id: int) -> dict[int, str]:
    rows = db.execute(select(Supplier).where(Supplier.business_id == business_id)).scalars().all()
    return {s.id: s.name for s in rows}


def _invoice_summary(db: Session, inv, suppliers: dict[int, str]) -> str:
    items = invoice_repo.get_items(db, inv.id)
    parts = []
    for it in items:
        seg = f"{it.product_name} x{it.quantity} @ ${it.unit_price}"
        if it.price_change_pct is not None:
            seg += f" ({it.price_change_pct:+.1f}% vs previous invoice)"
        parts.append(seg)
    supplier = suppliers.get(inv.supplier_id, "unknown supplier")
    items_str = "; ".join(parts) if parts else "no line items"
    return (
        f"Invoice #{inv.id} from supplier {supplier}, dated {inv.invoice_date}, "
        f"total {inv.invoice_total} {inv.currency}. Items: {items_str}."
    )


def _order_summary(db: Session, order) -> str:
    items = order_repo.get_items(db, order.id)
    parts = []
    for it in items:
        bits = [f"{it.quantity}x"]
        if it.color:
            bits.append(it.color)
        bits.append(it.product_name or "item")
        if it.size:
            bits.append(f"size {it.size}")
        parts.append(" ".join(bits))
    items_str = "; ".join(parts) if parts else "no items"
    return (
        f"Order #{order.id} via {order.source or 'unknown'}, status {order.status}, "
        f"delivery to {order.delivery_area or 'n/a'}, payment {order.payment_method or 'n/a'}. "
        f"Items: {items_str}."
    )


def _product_summary(db: Session, product) -> str:
    last7 = sum(float(s.quantity or 0) for s in sales_repo.get_sales_history(db, product.id, days=7))
    last30 = sum(float(s.quantity or 0) for s in sales_repo.get_sales_history(db, product.id, days=30))
    return (
        f"Product '{product.name}': current stock {product.current_stock}, "
        f"reorder level {product.reorder_level}, cost ${product.cost_price}, "
        f"selling ${product.selling_price}. Units sold last 7 days: {last7:g}, "
        f"last 30 days: {last30:g}."
    )


def _collect_documents(db: Session, business_id: int) -> list[tuple[str, int, str]]:
    """Return (source_type, source_id, content) tuples for everything to index."""
    suppliers = _supplier_names(db, business_id)
    docs: list[tuple[str, int, str]] = []

    for inv in invoice_repo.list_invoices(db, business_id):
        docs.append(("invoice", inv.id, _invoice_summary(db, inv, suppliers)))
    for order in order_repo.list_orders(db, business_id):
        docs.append(("order", order.id, _order_summary(db, order)))
    for product in product_repo.list_products(db, business_id):
        docs.append(("product", product.id, _product_summary(db, product)))

    return docs


# ── Public service API ───────────────────────────────────────────────

def ensure_indexed(db: Session, business_id: int) -> None:
    """Self-heal: if the vector index is empty for this business but the DB has
    data to index, build it on demand.

    The vector store is a local file. After a redeploy on a host without a
    persistent volume, that file is gone even though the SQL data remains — so a
    cold container would answer every question with "no data" until someone
    clicks Reindex. This makes the first question after a deploy rebuild the
    index automatically. Safe to call on every ask: it's a no-op once the index
    is warm (count > 0) or when there's genuinely nothing to index.
    """
    try:
        if vector_store.count(business_id) > 0:
            return
        collected = _collect_documents(db, business_id)
        if not collected:
            return  # nothing to index — genuine empty business
        logger.info("rag_autoindex_triggered", business_id=business_id)
        index_all(db, business_id)
    except Exception as exc:  # noqa: BLE001
        # Never let auto-indexing break a question; fall through to normal
        # retrieval (which will simply return no_data if still empty).
        logger.error("rag_autoindex_failed", business_id=business_id, err=str(exc))


def index_all(db: Session, business_id: int) -> dict:
    """(Re)build the document table + vector index from current business data.

    Uses parent-child chunking: full document text stored in the `documents` DB
    table (parent), small 400-char chunks embedded in the vector store (children).
    """
    # Clean slate so re-indexing never leaves stale rows/vectors.
    db.query(Document).filter(Document.business_id == business_id).delete(synchronize_session=False)
    vector_store.reset_collection(business_id)

    collected = _collect_documents(db, business_id)

    ids, texts, metadatas = [], [], []
    for source_type, source_id, content in collected:
        # Parent stored in DB for full-text lookup during Q&A.
        doc = Document(business_id=business_id, source_type=source_type, source_id=source_id, content=content)
        db.add(doc)
        db.flush()

        # Children: small chunks for precise vector retrieval.
        for ci, chunk in enumerate(rag.chunk_text(content)):
            ids.append(f"{source_type}:{source_id}:{ci}")
            texts.append(chunk)
            metadatas.append({
                "source_type": source_type,
                "source_id": source_id,
                "document_id": doc.id,
                "chunk": ci,
            })

    if texts:
        vectors = embeddings.embed_texts(texts)
        vector_store.upsert(ids, vectors, texts, metadatas, business_id=business_id)

    db.commit()
    logger.info("rag_indexed", business_id=business_id, documents=len(collected), chunks=len(texts))
    return {"status": "indexed", "documents_indexed": len(collected), "chunks_indexed": len(texts)}


def ask_stream(db: Session, question: str, business_id: int = 1, top_k: int = 5):
    """Streaming version of ask(). Yields SSE-formatted strings.

    SSE event types:
      sources  — retrieval complete {sources, grounded, retrieval_stats}
      text     — a streamed answer token {text}
      no_data  — nothing was retrieved {answer}
      error    — guardrail blocked {error}
    """
    import json as _json

    question = (question or "").strip()
    if not question:
        yield f'data: {_json.dumps({"type": "error", "error": "question cannot be empty"})}\n\n'
        return

    safe, reason = guardrails.is_safe_input(question)
    if not safe:
        logger.warning("qa_question_blocked", reason=reason)
        yield f'data: {_json.dumps({"type": "error", "error": reason or "Question rejected by guardrails."})}\n\n'
        return

    # Self-heal an empty/cold index (e.g. after a redeploy) before retrieving.
    ensure_indexed(db, business_id)

    hits, retrieval_stats = rag.retrieve_reranked(question, top_k=top_k, business_id=business_id)

    if not hits:
        yield f'data: {_json.dumps({"type": "no_data", "answer": rag.NO_DATA_ANSWER})}\n\n'
        return

    # Parent lookup
    seen_parents: dict[tuple, str] = {}
    for h in hits:
        meta = h.get("metadata") or {}
        st, sid = meta.get("source_type"), meta.get("source_id")
        if st and sid and (st, sid) not in seen_parents:
            doc = db.execute(
                select(Document).where(
                    Document.source_type == st,
                    Document.source_id == sid,
                )
            ).scalars().first()
            seen_parents[(st, sid)] = doc.content if doc else h.get("document", "")

    unique_texts = list(dict.fromkeys(seen_parents.values()))
    context = rag.build_context([{"document": t} for t in unique_texts])

    sources: list[dict] = []
    seen_keys: set[tuple] = set()
    for h in hits:
        meta = h.get("metadata") or {}
        st, sid = meta.get("source_type"), meta.get("source_id")
        key = (st, sid)
        if key not in seen_keys:
            seen_keys.add(key)
            dist = h.get("distance")
            sources.append({
                "source_type": st,
                "source_id": sid,
                "content": seen_parents.get(key, h.get("document", "")),
                "score": round(1.0 - float(dist), 4) if dist is not None else None,
            })

    retrieval_stats["parents_shown"] = len(sources)

    # Emit sources immediately so the UI can show them before the answer starts.
    yield f'data: {_json.dumps({"type": "sources", "sources": sources, "grounded": True, "retrieval_stats": retrieval_stats})}\n\n'

    # Stream LLM generation.
    from app.ai.prompts import RAG_QA_PROMPT
    from app.ai.llm import stream_text

    prompt = RAG_QA_PROMPT.format(context=context, question=question)
    full = ""
    for token in stream_text([{"role": "user", "content": prompt}]):
        full += token
        yield f'data: {_json.dumps({"type": "text", "text": token})}\n\n'

    logger.info("qa_answered_stream", grounded=True, sources=len(sources), chars=len(full))


def ask(db: Session, question: str, business_id: int = 1, top_k: int = 5) -> dict:
    """Guardrail → hybrid retrieval → parent lookup → grounded generation."""
    question = (question or "").strip()
    if not question:
        raise ValueError("question cannot be empty")

    safe, reason = guardrails.is_safe_input(question)
    if not safe:
        logger.warning("qa_question_blocked", reason=reason)
        raise GuardrailError(reason or "Question rejected by guardrails.")

    # Self-heal an empty/cold index (e.g. after a redeploy) before retrieving.
    ensure_indexed(db, business_id)

    # Hybrid retrieval: vector search × 3 candidates → BM25 rerank via RRF.
    hits, retrieval_stats = rag.retrieve_reranked(question, top_k=top_k, business_id=business_id)

    if not hits:
        return {
            "answer": rag.NO_DATA_ANSWER,
            "grounded": False,
            "sources": [],
            "retrieval_stats": retrieval_stats,
        }

    # Parent lookup: fetch full document text from DB for richer LLM context.
    seen_parents: dict[tuple, str] = {}
    for h in hits:
        meta = h.get("metadata") or {}
        st, sid = meta.get("source_type"), meta.get("source_id")
        if st and sid and (st, sid) not in seen_parents:
            doc = db.execute(
                select(Document).where(
                    Document.source_type == st,
                    Document.source_id == sid,
                )
            ).scalars().first()
            seen_parents[(st, sid)] = doc.content if doc else h.get("document", "")

    # Unique parent texts in hit order (dict preserves insertion order, Python 3.7+).
    unique_texts = list(dict.fromkeys(seen_parents.values()))
    context = rag.build_context([{"document": t} for t in unique_texts])
    answer = rag.generate_answer(question, context)

    # One source entry per unique parent, ordered by first child hit.
    sources: list[dict] = []
    seen_keys: set[tuple] = set()
    for h in hits:
        meta = h.get("metadata") or {}
        st, sid = meta.get("source_type"), meta.get("source_id")
        key = (st, sid)
        if key not in seen_keys:
            seen_keys.add(key)
            dist = h.get("distance")
            sources.append({
                "source_type": st,
                "source_id": sid,
                "content": seen_parents.get(key, h.get("document", "")),
                "score": round(1.0 - float(dist), 4) if dist is not None else None,
            })

    retrieval_stats["parents_shown"] = len(sources)
    logger.info("qa_answered", grounded=True, sources=len(sources), **retrieval_stats)

    return {
        "answer": answer,
        "grounded": True,
        "sources": sources,
        "retrieval_stats": retrieval_stats,
    }
