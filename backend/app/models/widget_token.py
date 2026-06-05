import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP, func

from app.core.database import Base


class WidgetToken(Base):
    __tablename__ = "widget_tokens"

    token = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    label = Column(String(255), nullable=False, default="My Widget")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
