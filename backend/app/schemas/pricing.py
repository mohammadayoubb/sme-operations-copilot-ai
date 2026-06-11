"""Pydantic schemas for the pricing / profit advisor.

All arithmetic happens in `pricing_service.calculate_margin` (pure Python).
The LLM only writes the human explanation — it never computes numbers.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class PricingRequest(BaseModel):
    cost: float = Field(ge=0, description="Cost price per unit")
    sell: float = Field(ge=0, description="Selling price per unit")
    delivery: float = Field(default=0.0, ge=0, description="Delivery cost per unit")
    packaging: float = Field(default=0.0, ge=0, description="Packaging cost per unit")
    # optional — when set, the service pulls velocity + cost trend from the DB
    product_id: Optional[int] = Field(default=None, description="Link to a known product for context")
    product_name: Optional[str] = Field(default=None, description="Display name used in the LLM prompt")


class PricingScenario(BaseModel):
    label: str            # "Break-even", "15% margin", …
    target_margin_pct: float
    required_price: float
    profit: float


class CostTrend(BaseModel):
    prev_cost: float
    current_cost: float
    change_pct: float     # positive = cost went up
    direction: str        # "up" | "down" | "flat"


class PricingResponse(BaseModel):
    # ── core numbers (unchanged) ─────────────────────────────────────────
    total_cost: float
    profit: float
    margin_pct: float
    sell_for_25pct: float

    # ── scenario table (5 target margins, pure Python) ───────────────────
    scenarios: list[PricingScenario]

    # ── business context (from DB when product_id given) ─────────────────
    velocity: str                          # "fast" | "medium" | "slow" | "unknown"
    velocity_avg_daily: Optional[float]    # avg units/day last 30 days
    cost_trend: Optional[CostTrend]        # supplier price movement

    # ── LLM strategy (3 structured parts) ────────────────────────────────
    assessment: str       # current position in 1-2 sentences
    recommendation: str   # specific price advice in 1-2 sentences
    risk: str             # one risk to watch

    # kept for backward compat (concatenation of the three above)
    explanation: str


class ProductPricingInfo(BaseModel):
    id: int
    name: str
    current_stock: float
    latest_cost: Optional[float]      # from most recent invoice
    cost_change_pct: Optional[float]  # vs previous invoice
    avg_daily_sales: Optional[float]
    velocity: str                     # "fast" | "medium" | "slow" | "unknown"


class PriceHistoryPoint(BaseModel):
    invoice_date: Optional[date]
    unit_price: float
