"""RAG indexing + Q&A orchestration.

Indexing turns the owner's structured business data (invoices, orders, products +
sales) into plain-text summary documents, stores them in the `documents` table,
then chunks + embeds them into the vector store. Ask runs guardrails, then the
retrieve → ground → answer flow in `app.ai.rag`.
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

def index_all(db: Session, business_id: Optional[int] = None) -> dict:
    """(Re)build the document table + vector index from current business data."""
    business = product_repo.get_or_create_default_business(db)
    bid = business_id or business.id

    # Clean slate so re-indexing never leaves stale rows/vectors.
    db.query(Document).filter(Document.business_id == bid).delete(synchronize_session=False)
    vector_store.reset_collection()

    collected = _collect_documents(db, bid)

    # Persist document rows, then chunk + embed each.
    ids, texts, metadatas = [], [], []
    for source_type, source_id, content in collected:
        doc = Document(business_id=bid, source_type=source_type, source_id=source_id, content=content)
        db.add(doc)
        db.flush()  # need doc.id
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
        vector_store.upsert(ids, vectors, texts, metadatas)

    db.commit()
    logger.info("rag_indexed", documents=len(collected), chunks=len(texts))
    return {"status": "indexed", "documents_indexed": len(collected), "chunks_indexed": len(texts)}


def ask(db: Session, question: str, top_k: int = 5) -> dict:
    """Guardrail the question, then run the grounded RAG flow."""
    question = (question or "").strip()
    if not question:
        raise ValueError("question cannot be empty")

    safe, reason = guardrails.is_safe_input(question)
    if not safe:
        logger.warning("qa_question_blocked", reason=reason)
        raise GuardrailError(reason or "Question rejected by guardrails.")

    result = rag.answer_question(question, top_k=top_k)
    logger.info("qa_answered", grounded=result["grounded"], sources=len(result["sources"]))
    return result
