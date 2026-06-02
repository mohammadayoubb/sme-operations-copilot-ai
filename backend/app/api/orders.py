from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.repositories import order_repo
from app.schemas.order import (
    OrderDetailOut,
    OrderExtractRequest,
    OrderItemOut,
    OrderListItem,
    OrderStatusUpdate,
)
from app.services import order_service
from app.services.order_service import GuardrailError

logger = get_logger(__name__)

router = APIRouter(prefix="/api/orders", tags=["Orders"])


def _to_detail(db: Session, order) -> OrderDetailOut:
    items = order_repo.get_items(db, order.id)
    detail = OrderDetailOut.model_validate(order)
    detail.items = [OrderItemOut.model_validate(i) for i in items]
    return detail


@router.post("/extract", response_model=OrderDetailOut, status_code=201)
def extract_order(payload: OrderExtractRequest, db: Session = Depends(get_db)):
    """Extract a structured order from a pasted WhatsApp/Instagram message,
    persist it, and (for a new order) deduct inventory — all in one transaction."""
    try:
        order = order_service.extract_and_create_order(db, payload.message, payload.source)
        db.commit()
        detail = _to_detail(db, order)
        return detail
    except GuardrailError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("order_extract_failed", err=str(exc))
        raise HTTPException(422, f"Could not extract a valid order: {exc}")


@router.get("/", response_model=list[OrderListItem])
def list_orders(db: Session = Depends(get_db)):
    return order_repo.list_orders(db)


@router.get("/{order_id}", response_model=OrderDetailOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = order_repo.get(db, order_id)
    if order is None:
        raise HTTPException(404, "Order not found")
    return _to_detail(db, order)


@router.patch("/{order_id}/status", response_model=OrderListItem)
def update_order_status(order_id: int, payload: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = order_repo.get(db, order_id)
    if order is None:
        raise HTTPException(404, "Order not found")
    order.status = payload.status
    db.commit()
    db.refresh(order)
    return order
