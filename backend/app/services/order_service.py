"""Order processing orchestration.

Flow (runs synchronously inside the API request):
    guardrail scan  →  LLM extraction  →  Pydantic validation
         →  confidence scoring
              ↓ high confidence (≥ 0.75)          ↓ low confidence
              auto-commit: create order + deduct   review queue: create order,
              inventory + emit low-stock alerts    NO stock deduction
The caller (API endpoint) owns commit/rollback. If anything raises before the
commit, nothing is persisted.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.ai import extraction
from app.ai.confidence import CONFIDENCE_THRESHOLD, compute_confidence
from app.core.logging import get_logger
from app.models.insight import Alert
from app.models.order import Order
from app.repositories import order_repo, product_repo
from app.security import guardrails

logger = get_logger(__name__)


class GuardrailError(ValueError):
    """Raised when user input fails a guardrail check (e.g. prompt injection)."""


def _deduct_inventory_for_order(db: Session, order: Order, extracted, business_id: int) -> list[str]:
    """Deduct stock for each item in a new_order. Returns low-stock alert messages."""
    low_stock_alerts: list[str] = []
    for item in extracted.items:
        product = product_repo.match_or_create_product(db, business_id, item.product)

        order_repo.add_item(
            db,
            order.id,
            product_id=product.id,
            product_name=item.product,
            quantity=item.quantity,
            color=item.color,
            size=item.size,
        )

        product_repo.adjust_stock(
            db, product, -item.quantity, reason="order", reference_id=order.id
        )

        if (product.current_stock or 0) <= (product.reorder_level or 0):
            msg = (
                f"{product.name} is low on stock "
                f"({product.current_stock} left) after order #{order.id}."
            )
            low_stock_alerts.append(msg)
            db.add(Alert(
                business_id=business_id,
                type="low_stock",
                message=msg,
                product_id=product.id,
            ))
    return low_stock_alerts


def extract_and_create_order(
    db: Session, message: str, source: str = "whatsapp", business_id: int = 1
) -> Order:
    """Extract a structured order from a customer message and persist it.

    High-confidence extractions auto-commit with inventory deduction.
    Low-confidence extractions are parked in the review queue — no inventory
    is touched until a human approves.

    Caller manages commit/rollback. Returns the created Order (flushed, with id).
    """
    message = (message or "").strip()
    if not message:
        raise ValueError("message cannot be empty")

    # 1. Guardrail: block obvious prompt-injection attempts before the LLM sees it
    safe, reason = guardrails.is_safe_input(message)
    if not safe:
        logger.warning("order_input_blocked", reason=reason)
        raise GuardrailError(reason or "Input rejected by guardrails.")

    # 2. LLM extraction + validation (raises on bad output → caller rolls back)
    extracted = extraction.extract_order(message)

    # 3. Confidence scoring (pure Python — deterministic)
    confidence = compute_confidence(extracted)
    needs_review = (extracted.intent == "new_order") and (confidence < CONFIDENCE_THRESHOLD)
    review_status = "needs_review" if needs_review else "auto_approved"
    status = "pending_review" if needs_review else "pending"

    # 4. Persist header
    order = order_repo.create_order(
        db,
        business_id,
        source=source,
        raw_message=message,
        extracted_json=extracted.model_dump(),
        delivery_area=extracted.delivery_area,
        payment_method=extracted.payment_method,
        status=status,
        confidence_score=confidence,
        review_status=review_status,
    )

    # 5. High-confidence new orders deduct inventory immediately.
    #    Low-confidence orders park in the review queue — no stock touched yet.
    #    Non-new-order intents (inquiry, complaint, other) never touch inventory.
    low_stock_alerts: list[str] = []
    if extracted.intent == "new_order" and not needs_review:
        low_stock_alerts = _deduct_inventory_for_order(db, order, extracted, business_id)

    logger.info(
        "order_extracted",
        order_id=order.id,
        intent=extracted.intent,
        items=len(extracted.items),
        confidence=confidence,
        review_status=review_status,
        low_stock_alerts=len(low_stock_alerts),
    )
    return order


def approve_order(db: Session, order_id: int, business_id: int | None = None) -> Order:
    """Approve a queued order: deduct inventory and mark as approved.

    Caller manages commit/rollback.
    """
    order = order_repo.get(db, order_id)
    if order is None or (business_id is not None and order.business_id != business_id):
        raise ValueError(f"Order {order_id} not found")
    if order.review_status != "needs_review":
        raise ValueError(f"Order {order_id} is not in the review queue (status: {order.review_status})")

    from app.schemas.order import ExtractedOrder
    extracted = ExtractedOrder.model_validate(order.extracted_json)
    business_id = order.business_id

    _deduct_inventory_for_order(db, order, extracted, business_id)

    order.review_status = "approved"
    order.status = "pending"
    db.flush()

    logger.info("order_approved", order_id=order_id)
    return order


def reject_order(db: Session, order_id: int, business_id: int | None = None) -> Order:
    """Reject a queued order without touching inventory.

    Caller manages commit/rollback.
    """
    order = order_repo.get(db, order_id)
    if order is None or (business_id is not None and order.business_id != business_id):
        raise ValueError(f"Order {order_id} not found")
    if order.review_status != "needs_review":
        raise ValueError(f"Order {order_id} is not in the review queue (status: {order.review_status})")

    order.review_status = "rejected"
    order.status = "cancelled"
    db.flush()

    logger.info("order_rejected", order_id=order_id)
    return order
