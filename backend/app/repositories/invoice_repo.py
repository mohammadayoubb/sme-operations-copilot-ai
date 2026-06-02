"""Invoice persistence helpers."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceItem


def create_pending_invoice(db: Session, business_id: int, file_path: str) -> Invoice:
    invoice = Invoice(business_id=business_id, file_path=file_path, status="pending")
    db.add(invoice)
    db.flush()
    return invoice


def get(db: Session, invoice_id: int) -> Optional[Invoice]:
    return db.get(Invoice, invoice_id)


def list_invoices(db: Session, business_id: Optional[int] = None) -> list[Invoice]:
    stmt = select(Invoice).order_by(Invoice.created_at.desc())
    if business_id is not None:
        stmt = stmt.where(Invoice.business_id == business_id)
    return list(db.execute(stmt).scalars().all())


def get_items(db: Session, invoice_id: int) -> list[InvoiceItem]:
    return list(
        db.execute(
            select(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id)
        ).scalars().all()
    )
