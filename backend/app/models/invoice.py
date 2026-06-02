from sqlalchemy import (
    Column, Integer, String, Float, Numeric, Text, Date, ForeignKey, TIMESTAMP, func,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    invoice_date = Column(Date)
    invoice_total = Column(Numeric(12, 2))
    currency = Column(String(10), server_default="USD")
    raw_ocr_text = Column(Text)
    extracted_json = Column(JSONB)
    status = Column(String(50), server_default="pending")  # pending, processed, failed
    file_path = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    product_name = Column(String(255))   # raw extracted name before matching
    quantity = Column(Float)
    unit_price = Column(Numeric(10, 4))
    total = Column(Numeric(12, 2))
    price_change_pct = Column(Float)     # vs. previous invoice from same supplier
