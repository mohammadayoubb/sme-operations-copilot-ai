"""Pydantic schemas for product listing."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ProductOut(BaseModel):
    id: int
    name: str
    sku: Optional[str] = None
    current_stock: Optional[float] = None
    reorder_level: Optional[float] = None
    unit: Optional[str] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None

    model_config = {"from_attributes": True}
