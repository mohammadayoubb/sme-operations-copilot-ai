"""Pydantic schemas for inventory forecasting responses."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ProductForecast(BaseModel):
    product_id: int
    product_name: str
    current_stock: float
    reorder_level: float
    avg_daily_sales: float
    sales_last_7d: float
    sales_last_30d: float
    days_until_stockout: Optional[float] = None
    reorder_recommended: bool
    reorder_by_date: Optional[str] = None


class RetrainResult(BaseModel):
    status: str
    model_name: Optional[str] = None
    metrics: Optional[dict] = None
    trained_at: Optional[str] = None
    n_train_rows: Optional[int] = None
    model_path: Optional[str] = None
    error: Optional[str] = None
