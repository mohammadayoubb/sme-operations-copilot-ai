"""Sales history persistence helpers (read side feeds the forecasting models)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sales import Sale


def get_sales_history(
    db: Session, product_id: int, days: Optional[int] = None
) -> list[Sale]:
    """All sales rows for a product, oldest → newest, optionally last `days`."""
    stmt = select(Sale).where(Sale.product_id == product_id).order_by(Sale.sale_date.asc(), Sale.id.asc())
    if days is not None:
        cutoff = date.today() - timedelta(days=days)
        stmt = stmt.where(Sale.sale_date >= cutoff)
    return list(db.execute(stmt).scalars().all())


def get_all_sales(db: Session, business_id: Optional[int] = None) -> list[Sale]:
    """Every sale (optionally for one business) — used to train the model."""
    stmt = select(Sale).order_by(Sale.product_id, Sale.sale_date.asc())
    if business_id is not None:
        stmt = stmt.where(Sale.business_id == business_id)
    return list(db.execute(stmt).scalars().all())


def product_ids_with_sales(db: Session, business_id: Optional[int] = None) -> list[int]:
    stmt = select(Sale.product_id).distinct()
    if business_id is not None:
        stmt = stmt.where(Sale.business_id == business_id)
    return [pid for (pid,) in db.execute(stmt).all() if pid is not None]
