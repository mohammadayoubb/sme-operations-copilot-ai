"""Inventory forecasting orchestration.

Loads (or trains, on first use) the scikit-learn artifact, runs inference per
product, and returns reorder recommendations. Heavy retraining is also exposed
as a Celery task (`app/workers/forecast_tasks.py`).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.ai import forecasting
from app.core.logging import get_logger
from app.repositories import product_repo, sales_repo
from app.schemas.forecast import ProductForecast

logger = get_logger(__name__)


def _series_by_product(db: Session, business_id: Optional[int] = None) -> dict:
    """Build a daily sales series for every product that has sales history."""
    sales = sales_repo.get_all_sales(db, business_id)
    grouped: dict[int, list] = {}
    for s in sales:
        grouped.setdefault(s.product_id, []).append(s)
    return {pid: forecasting.daily_series(rows) for pid, rows in grouped.items()}


def train_and_save(db: Session, business_id: Optional[int] = None) -> dict:
    """Train + compare models on all sales history and persist the best artifact."""
    series = _series_by_product(db, business_id)
    artifact = forecasting.train_and_select(series)
    path = forecasting.save_model(artifact)
    logger.info(
        "forecast_model_trained",
        model=artifact["model_name"],
        rmse=artifact["metrics"][artifact["model_name"]]["rmse"],
        path=path,
    )
    return {**artifact, "model_path": path}


def _ensure_artifact(db: Session) -> Optional[dict]:
    """Load the saved artifact, training one on first use if none exists."""
    artifact = forecasting.load_model()
    if artifact is None:
        try:
            artifact = train_and_save(db)
        except ValueError as exc:
            logger.warning("forecast_artifact_unavailable", err=str(exc))
            return None
    return artifact


def _forecast_for_product(db: Session, product, artifact: Optional[dict]) -> ProductForecast:
    rows = sales_repo.get_sales_history(db, product.id)
    series = forecasting.daily_series(rows)
    f = forecasting.forecast_product(
        series,
        current_stock=float(product.current_stock or 0),
        reorder_level=float(product.reorder_level or 0),
        artifact=artifact,
    )
    return ProductForecast(
        product_id=product.id,
        product_name=product.name,
        reorder_level=float(product.reorder_level or 0),
        **f,
    )


def get_reorder_recommendations(db: Session, business_id: Optional[int] = None) -> list[ProductForecast]:
    """Forecast every product; return only those that should be reordered."""
    artifact = _ensure_artifact(db)
    products = product_repo.list_products(db, business_id)
    forecasts = [_forecast_for_product(db, p, artifact) for p in products]
    recommended = [f for f in forecasts if f.reorder_recommended]
    # Soonest stockout first (products with no estimate sink to the bottom).
    recommended.sort(key=lambda f: (f.days_until_stockout is None, f.days_until_stockout or 0))
    return recommended


def forecast_one(db: Session, product_id: int) -> Optional[ProductForecast]:
    product = product_repo.get_product(db, product_id)
    if product is None:
        return None
    artifact = _ensure_artifact(db)
    return _forecast_for_product(db, product, artifact)
