"""Pydantic schemas for invoice extraction and API responses.

`ExtractedInvoice` is the contract the LLM output MUST satisfy before anything
is written to the database. If validation fails, we never touch the DB.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── LLM extraction output (validated before DB write) ─────────────

class ExtractedInvoiceItem(BaseModel):
    name: str
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    total: Optional[float] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("item name cannot be blank")
        return v


class ExtractedInvoice(BaseModel):
    supplier: Optional[str] = None
    date: Optional[str] = None          # raw string from LLM; parsed later
    items: list[ExtractedInvoiceItem] = Field(min_length=1)
    invoice_total: Optional[float] = None
    currency: Optional[str] = "USD"

    @field_validator("supplier", "currency")
    @classmethod
    def strip_str(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v


# ── API request/response schemas ──────────────────────────────────

class InvoiceUploadResponse(BaseModel):
    invoice_id: int
    status: str


class InvoiceStatusResponse(BaseModel):
    invoice_id: int
    status: str
    error: Optional[str] = None


class InvoiceItemOut(BaseModel):
    id: int
    product_id: Optional[int]
    product_name: Optional[str]
    quantity: Optional[float]
    unit_price: Optional[float]
    total: Optional[float]
    price_change_pct: Optional[float]

    model_config = {"from_attributes": True}


class InvoiceListItem(BaseModel):
    id: int
    supplier_id: Optional[int]
    invoice_date: Optional[date]
    invoice_total: Optional[float]
    currency: Optional[str]
    status: str

    model_config = {"from_attributes": True}


class InvoiceDetailOut(InvoiceListItem):
    raw_ocr_text: Optional[str]
    items: list[InvoiceItemOut] = []
