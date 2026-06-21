from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, TIMESTAMP, func

from app.core.database import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(64), nullable=False, unique=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    used = Column(Boolean, server_default="false", nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
