from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    period_start = Column(Date)
    period_end = Column(Date)
    report_type = Column(String(50), server_default="weekly")
    summary_text = Column(Text)            # LLM-written narrative
    data_json = Column(JSONB)             # the aggregated numbers (computed in Python)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
