from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    source = Column(String(50))                 # whatsapp, instagram, manual
    raw_message = Column(Text)                   # original customer message
    extracted_json = Column(JSONB)              # validated LLM extraction output
    delivery_area = Column(String(255))
    payment_method = Column(String(100))         # cash_on_delivery, bank_transfer, other
    status = Column(String(50), server_default="pending")  # pending, pending_review, confirmed, fulfilled, cancelled
    confidence_score = Column(Float, server_default="1.0")  # [0,1] — below threshold routes to review queue
    review_status = Column(String(50), server_default="auto_approved")  # auto_approved, needs_review, approved, rejected
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    product_name = Column(String(255))           # raw extracted name before matching
    quantity = Column(Float)
    color = Column(String(100))
    size = Column(String(50))
    notes = Column(Text)
