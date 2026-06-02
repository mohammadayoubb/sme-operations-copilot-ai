from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, TIMESTAMP, func

from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    type = Column(String(100))  # low_stock, price_increase, reorder
    message = Column(Text)
    product_id = Column(Integer, ForeignKey("products.id"))
    is_read = Column(Boolean, server_default="false")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class AIInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    type = Column(String(100))  # pricing, forecast, order, invoice
    reference_id = Column(Integer)
    insight_text = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
