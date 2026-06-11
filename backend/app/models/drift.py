from sqlalchemy import Column, Integer, Float, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class DriftSignal(Base):
    __tablename__ = "drift_signals"

    id = Column(Integer, primary_key=True)
    run_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    psi_score = Column(Float, nullable=False)
    status = Column(String(20), nullable=False)   # stable | warning | alert
    baseline_days = Column(Integer, default=60)
    recent_days = Column(Integer, default=7)
    feature_stats = Column(JSONB)                 # per-feature PSI breakdown
