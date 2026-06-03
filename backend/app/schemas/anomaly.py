from __future__ import annotations

from pydantic import BaseModel


class AnomalyAlert(BaseModel):
    product_id: int
    product_name: str
    anomaly_date: str        # ISO date string
    direction: str           # "spike" or "drop"
    actual_qty: float
    expected_qty: float
    z_score: float
    pct_deviation: float
    explanation: str         # LLM-generated plain-language explanation


class AnomalyResponse(BaseModel):
    alerts: list[AnomalyAlert]
    scanned_products: int
    window_days: int
