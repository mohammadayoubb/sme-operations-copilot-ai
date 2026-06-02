"""Order processing orchestration.

Flow (runs synchronously inside the API request):
    guardrail scan  →  LLM extraction  →  Pydantic validation
         →  single DB transaction:
              - create order header
              - for a new_order: create order_items, match/create products,
                deduct stock + inventory movements, raise low-stock alerts
The caller (API endpoint) owns commit/rollback. If anything raises before the
commit, nothing is persisted.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.ai import extraction
from app.core.logging import get_logger
from app.models.insight import Alert
from app.models.order import Order
from app.repositories import order_repo, product_repo
from app.security import guardrails

logger = get_logger(__name__)


class GuardrailError(ValueError):
    """Raised when user input fails a guardrail check (e.g. prompt injection)."""


def extract_and_create_order(
    db: Session, message: str, source: str = "whatsapp"
) -> Order:
    """Extract a structured order from a customer message and persist it.

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

    # 3. Persist header
    business = product_repo.get_or_create_default_business(db)
    order = order_repo.create_order(
        db,
        business.id,
        source=source,
        raw_message=message,
        extracted_json=extracted.model_dump(),
        delivery_area=extracted.delivery_area,
        payment_method=extracted.payment_method,
        status="pending",
    )

    # 4. Only a confirmed new order touches inventory; inquiries/complaints are
    #    logged for follow-up but never deduct stock.
    low_stock_alerts: list[str] = []
    if extracted.intent == "new_order":
        for item in extracted.items:
            product = product_repo.match_or_create_product(db, business.id, item.product)

            order_repo.add_item(
                db,
                order.id,
                product_id=product.id,
                product_name=item.product,
                quantity=item.quantity,
                color=item.color,
                size=item.size,
            )

            # stock out + audit movement
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
                    business_id=business.id,
                    type="low_stock",
                    message=msg,
                    product_id=product.id,
                ))

    logger.info(
        "order_extracted",
        order_id=order.id,
        intent=extracted.intent,
        items=len(extracted.items),
        low_stock_alerts=len(low_stock_alerts),
    )
    return order
