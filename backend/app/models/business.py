from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, func

from app.core.database import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    name = Column(String(255), nullable=False)
    contact = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
