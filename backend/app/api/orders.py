from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
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
def extract_order(
    payload: OrderExtractRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        order = order_service.extract_and_create_order(
            db, payload.message, payload.source, current_user.business_id
        )
        db.commit()
        return _to_detail(db, order)
    except GuardrailError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("order_extract_failed", err=str(exc))
        raise HTTPException(422, f"Could not extract a valid order: {exc}")


@router.get("/review-queue", response_model=list[OrderDetailOut])
def get_review_queue(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    orders = order_repo.list_review_queue(db, current_user.business_id)
    return [_to_detail(db, o) for o in orders]


@router.post("/{order_id}/approve", response_model=OrderDetailOut)
def approve_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        order = order_service.approve_order(db, order_id, current_user.business_id)
        db.commit()
        return _to_detail(db, order)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("order_approve_failed", order_id=order_id, err=str(exc))
        raise HTTPException(500, f"Approval failed: {exc}")


@router.post("/{order_id}/reject", response_model=OrderDetailOut)
def reject_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        order = order_service.reject_order(db, order_id, current_user.business_id)
        db.commit()
        return _to_detail(db, order)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("order_reject_failed", order_id=order_id, err=str(exc))
        raise HTTPException(500, f"Rejection failed: {exc}")


@router.get("/", response_model=list[OrderListItem])
def list_orders(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return order_repo.list_orders(db, current_user.business_id)


@router.get("/{order_id}", response_model=OrderDetailOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    order = order_repo.get(db, order_id)
    if order is None or order.business_id != current_user.business_id:
        raise HTTPException(404, "Order not found")
    return _to_detail(db, order)


@router.patch("/{order_id}/status", response_model=OrderListItem)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    order = order_repo.get(db, order_id)
    if order is None or order.business_id != current_user.business_id:
        raise HTTPException(404, "Order not found")
    order.status = payload.status
    db.commit()
    db.refresh(order)
    return order
