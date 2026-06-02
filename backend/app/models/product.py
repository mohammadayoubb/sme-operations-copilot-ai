from sqlalchemy import Column, Integer, String, Float, Numeric, ForeignKey, TIMESTAMP, func

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    name = Column(String(255), nullable=False)
    sku = Column(String(100))
    current_stock = Column(Float, server_default="0")
    reorder_level = Column(Float, server_default="10")
    unit = Column(String(50))
    cost_price = Column(Numeric(10, 2))
    selling_price = Column(Numeric(10, 2))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    delta = Column(Float, nullable=False)          # +in / -out
    reason = Column(String(100))                   # invoice, order, sale, manual_adjustment
    reference_id = Column(Integer)                 # invoice_id or order_id
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
