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


class PricingResponse(BaseModel):
    total_cost: float          # cost + delivery + packaging
    profit: float              # sell - total_cost
    margin_pct: float          # profit / sell * 100
    sell_for_25pct: float      # selling price needed to reach a 25% margin
    explanation: str           # LLM-written, business-friendly


class PriceHistoryPoint(BaseModel):
    invoice_date: Optional[date]
    unit_price: float
