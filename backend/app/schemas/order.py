"""Pydantic schemas for order extraction and API responses.

`ExtractedOrder` is the contract the LLM output MUST satisfy before anything
is written to the database. If validation fails, we never touch the DB.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ── LLM extraction output (validated before DB write) ─────────────

class ExtractedOrderItem(BaseModel):
    product: str
    quantity: int = Field(gt=0)
    color: Optional[str] = None
    size: Optional[str] = None

    @field_validator("product")
    @classmethod
    def product_not_blank(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("item product cannot be blank")
        return v

    @field_validator("color", "size")
    @classmethod
    def strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


class ExtractedOrder(BaseModel):
    intent: Literal["new_order", "inquiry", "complaint", "other"]
    items: list[ExtractedOrderItem] = Field(default_factory=list)
    delivery_area: Optional[str] = None
    payment_method: Optional[Literal["cash_on_delivery", "bank_transfer", "other"]] = None
    notes: Optional[str] = None

    @field_validator("delivery_area", "notes")
    @classmethod
    def strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


# ── API request schemas ───────────────────────────────────────────

class OrderExtractRequest(BaseModel):
    message: str = Field(min_length=1)
    source: str = "whatsapp"


class OrderStatusUpdate(BaseModel):
    status: Literal["pending", "confirmed", "fulfilled", "cancelled"]


# ── API response schemas ──────────────────────────────────────────

class OrderItemOut(BaseModel):
    id: int
    product_id: Optional[int]
    product_name: Optional[str]
    quantity: Optional[float]
    color: Optional[str]
    size: Optional[str]
    notes: Optional[str]

    model_config = {"from_attributes": True}


class OrderListItem(BaseModel):
    id: int
    source: Optional[str]
    delivery_area: Optional[str]
    payment_method: Optional[str]
    status: str
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class OrderDetailOut(OrderListItem):
    raw_message: Optional[str]
    extracted_json: Optional[dict] = None
    items: list[OrderItemOut] = []
