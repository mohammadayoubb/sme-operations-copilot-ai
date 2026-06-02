from sqlalchemy import Column, Integer, String, Float, Numeric, Date, ForeignKey, TIMESTAMP, func

from app.core.database import Base


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float)
    unit_price = Column(Numeric(10, 4))
    total = Column(Numeric(12, 2))
    sale_date = Column(Date, server_default=func.current_date())
    source = Column(String(50))                  # order, manual, pos
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
