from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=True)  # NULL for superadmin
    username = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), server_default="owner")  # owner / staff / superadmin
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
