"""Invoice processing orchestration.

Flow (runs inside the Celery worker):
    OCR  →  guardrail scan  →  LLM extraction  →  Pydantic validation
         →  single DB transaction:
              - update invoice header
              - create invoice items (with price-change %)
              - match/create products
              - update stock + inventory movements
              - raise price-increase alerts
On any failure the transaction is rolled back and the invoice is marked failed.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.ai import extraction, ocr
from app.core.logging import get_logger
from app.models.insight import Alert
from app.repositories import invoice_repo, product_repo
from app.security import guardrails

logger = get_logger(__name__)

PRICE_INCREASE_THRESHOLD_PCT = 5.0


def _parse_date(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    logger.warning("invoice_date_unparsed", raw=raw)
    return None


def process_invoice(db: Session, invoice_id: int) -> dict:
    """Process a pending invoice end-to-end. Caller manages commit/rollback."""
    invoice = invoice_repo.get(db, invoice_id)
    if invoice is None:
        raise ValueError(f"invoice {invoice_id} not found")

    # 1. OCR
    raw_text = ocr.extract_text(invoice.file_path)
    invoice.raw_ocr_text = raw_text
    if not raw_text.strip():
        raise ValueError("OCR produced no text")

    # 2. Guardrail: flag (but don't block) injection attempts inside the document
    if guardrails.detect_injection(raw_text):
        logger.warning("invoice_injection_flagged", invoice_id=invoice_id)
        db.add(Alert(
            business_id=invoice.business_id,
            type="security",
            message="Possible prompt-injection text detected inside uploaded invoice.",
        ))

    # 3. LLM extraction + validation (raises on bad output → rollback)
    extracted = extraction.extract_invoice(raw_text)

    # 4. Persist header
    supplier = product_repo.get_or_create_supplier(db, invoice.business_id, extracted.supplier)
    invoice.supplier_id = supplier.id if supplier else None
    invoice.invoice_date = _parse_date(extracted.date)
    invoice.invoice_total = extracted.invoice_total
    invoice.currency = extracted.currency or "USD"
    invoice.extracted_json = extracted.model_dump()

    # 5. Persist items + inventory + price comparison
    flagged_increases: list[str] = []
    for item in extracted.items:
        product = product_repo.match_or_create_product(db, invoice.business_id, item.name)

        prev_price = product_repo.last_unit_price(db, product.id, exclude_invoice_id=invoice.id)
        change_pct = None
        if prev_price and prev_price > 0:
            change_pct = round((item.unit_price - prev_price) / prev_price * 100, 2)

        total = item.total if item.total is not None else round(item.quantity * item.unit_price, 2)

        db.add(_build_item(invoice.id, product.id, item, total, change_pct))

        # stock in + audit movement
        product_repo.adjust_stock(db, product, item.quantity, reason="invoice", reference_id=invoice.id)
        product.cost_price = item.unit_price

        if change_pct is not None and change_pct >= PRICE_INCREASE_THRESHOLD_PCT:
            msg = f"{product.name} increased {change_pct}% vs. the previous invoice."
            flagged_increases.append(msg)
            db.add(Alert(
                business_id=invoice.business_id,
                type="price_increase",
                message=msg,
                product_id=product.id,
            ))

    invoice.status = "processed"

    logger.info(
        "invoice_processed",
        invoice_id=invoice_id,
        items=len(extracted.items),
        price_alerts=len(flagged_increases),
    )
    return {
        "invoice_id": invoice_id,
        "status": "processed",
        "items": len(extracted.items),
        "price_increases": flagged_increases,
    }


def _build_item(invoice_id, product_id, item, total, change_pct):
    from app.models.invoice import InvoiceItem

    return InvoiceItem(
        invoice_id=invoice_id,
        product_id=product_id,
        product_name=item.name,
        quantity=item.quantity,
        unit_price=item.unit_price,
        total=total,
        price_change_pct=change_pct,
    )
