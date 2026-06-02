"""Product + supplier + business persistence helpers."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business import Business, Supplier
from app.models.invoice import Invoice, InvoiceItem
from app.models.product import Product, InventoryMovement

DEFAULT_BUSINESS_NAME = "Demo Shop"
_MATCH_THRESHOLD = 85  # rapidfuzz score (0-100)


def get_or_create_default_business(db: Session) -> Business:
    biz = db.execute(select(Business).limit(1)).scalar_one_or_none()
    if biz is None:
        biz = Business(name=DEFAULT_BUSINESS_NAME)
        db.add(biz)
        db.flush()
    return biz


def get_or_create_supplier(db: Session, business_id: int, name: Optional[str]) -> Optional[Supplier]:
    if not name:
        return None
    supplier = db.execute(
        select(Supplier).where(
            Supplier.business_id == business_id,
            Supplier.name == name,
        )
    ).scalar_one_or_none()
    if supplier is None:
        supplier = Supplier(business_id=business_id, name=name)
        db.add(supplier)
        db.flush()
    return supplier


def match_or_create_product(db: Session, business_id: int, raw_name: str) -> Product:
    """Fuzzy-match an extracted product name to an existing product, else create."""
    from rapidfuzz import fuzz, process

    candidates = db.execute(
        select(Product).where(Product.business_id == business_id)
    ).scalars().all()

    if candidates:
        names = {p.id: p.name for p in candidates}
        best = process.extractOne(
            raw_name, names, scorer=fuzz.token_sort_ratio
        )
        if best and best[1] >= _MATCH_THRESHOLD:
            matched_id = best[2]
            return next(p for p in candidates if p.id == matched_id)

    product = Product(business_id=business_id, name=raw_name, current_stock=0)
    db.add(product)
    db.flush()
    return product


def last_unit_price(db: Session, product_id: int, exclude_invoice_id: int) -> Optional[float]:
    """Most recent unit price for this product from a prior invoice."""
    row = db.execute(
        select(InvoiceItem.unit_price)
        .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
        .where(
            InvoiceItem.product_id == product_id,
            InvoiceItem.invoice_id != exclude_invoice_id,
            InvoiceItem.unit_price.is_not(None),
        )
        .order_by(Invoice.invoice_date.desc().nullslast(), InvoiceItem.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    return float(row) if row is not None else None


def list_products(db: Session, business_id: Optional[int] = None) -> list[Product]:
    stmt = select(Product).order_by(Product.id)
    if business_id is not None:
        stmt = stmt.where(Product.business_id == business_id)
    return list(db.execute(stmt).scalars().all())


def get_product(db: Session, product_id: int) -> Optional[Product]:
    return db.get(Product, product_id)


def price_history(db: Session, product_id: int) -> list[tuple]:
    """Unit-price history for a product, oldest → newest, from invoice items."""
    rows = db.execute(
        select(Invoice.invoice_date, InvoiceItem.unit_price)
        .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
        .where(
            InvoiceItem.product_id == product_id,
            InvoiceItem.unit_price.is_not(None),
        )
        .order_by(Invoice.invoice_date.asc().nullsfirst(), InvoiceItem.id.asc())
    ).all()
    return [(d, float(p)) for d, p in rows]


def adjust_stock(db: Session, product: Product, delta: float, reason: str, reference_id: int) -> None:
    product.current_stock = (product.current_stock or 0) + delta
    db.add(InventoryMovement(
        product_id=product.id,
        delta=delta,
        reason=reason,
        reference_id=reference_id,
    ))
