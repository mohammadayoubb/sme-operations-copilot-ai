"""Order persistence helpers."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem


def create_order(
    db: Session,
    business_id: int,
    *,
    source: str,
    raw_message: str,
    extracted_json: dict,
    delivery_area: Optional[str],
    payment_method: Optional[str],
    status: str = "pending",
    confidence_score: float = 1.0,
    review_status: str = "auto_approved",
) -> Order:
    order = Order(
        business_id=business_id,
        source=source,
        raw_message=raw_message,
        extracted_json=extracted_json,
        delivery_area=delivery_area,
        payment_method=payment_method,
        status=status,
        confidence_score=confidence_score,
        review_status=review_status,
    )
    db.add(order)
    db.flush()
    return order


def add_item(
    db: Session,
    order_id: int,
    *,
    product_id: Optional[int],
    product_name: str,
    quantity: float,
    color: Optional[str],
    size: Optional[str],
    notes: Optional[str] = None,
) -> OrderItem:
    item = OrderItem(
        order_id=order_id,
        product_id=product_id,
        product_name=product_name,
        quantity=quantity,
        color=color,
        size=size,
        notes=notes,
    )
    db.add(item)
    return item


def get(db: Session, order_id: int) -> Optional[Order]:
    return db.get(Order, order_id)


def list_orders(db: Session, business_id: Optional[int] = None) -> list[Order]:
    stmt = select(Order).order_by(Order.created_at.desc(), Order.id.desc())
    if business_id is not None:
        stmt = stmt.where(Order.business_id == business_id)
    return list(db.execute(stmt).scalars().all())


def list_review_queue(db: Session, business_id: Optional[int] = None) -> list[Order]:
    stmt = (
        select(Order)
        .where(Order.review_status == "needs_review")
        .order_by(Order.confidence_score.asc(), Order.created_at.desc())
    )
    if business_id is not None:
        stmt = stmt.where(Order.business_id == business_id)
    return list(db.execute(stmt).scalars().all())


def get_items(db: Session, order_id: int) -> list[OrderItem]:
    return list(
        db.execute(
            select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.id)
        ).scalars().all()
    )
