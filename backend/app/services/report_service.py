"""Weekly business report generation.

All numbers are aggregated in plain Python (sales/profit week-over-week, top
products, low-stock risks, margins). The LLM only writes the narrative summary
from those numbers — it never computes anything.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.prompts import WEEKLY_REPORT_PROMPT
from app.core.logging import get_logger
from app.models.business import Supplier
from app.models.invoice import Invoice, InvoiceItem
from app.repositories import product_repo, report_repo, sales_repo
from app.services import forecasting_service

logger = get_logger(__name__)

WEEK_DAYS = 7


# ── Pure helpers (unit-tested) ─────────────────────────────────────

def pct_change(current: float, previous: float) -> Optional[float]:
    """Percentage change vs the previous period. None when there's no baseline."""
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


def rev_profit(rows: list[tuple], cost_map: dict[int, float]) -> tuple[float, float]:
    """rows = list of (product_id, quantity, total). Returns (revenue, profit)."""
    revenue = sum(float(total or 0) for _, _, total in rows)
    profit = sum(
        float(total or 0) - cost_map.get(pid, 0.0) * float(qty or 0)
        for pid, qty, total in rows
    )
    return round(revenue, 2), round(profit, 2)


def margin_pct(cost: Optional[float], sell: Optional[float]) -> Optional[float]:
    if not sell or float(sell) <= 0 or cost is None:
        return None
    return round((float(sell) - float(cost)) / float(sell) * 100, 1)


# ── Aggregation ────────────────────────────────────────────────────

def _supplier_price_changes(db: Session, business_id: int, start: date, end: date) -> list[dict]:
    rows = db.execute(
        select(Supplier.name, InvoiceItem.product_name, InvoiceItem.price_change_pct)
        .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
        .join(Supplier, Invoice.supplier_id == Supplier.id, isouter=True)
        .where(
            Invoice.business_id == business_id,
            Invoice.invoice_date >= start,
            Invoice.invoice_date <= end,
            InvoiceItem.price_change_pct.is_not(None),
        )
        .order_by(InvoiceItem.price_change_pct.desc())
    ).all()
    return [
        {"supplier": s or "unknown", "product": p, "change_pct": round(float(c), 1)}
        for s, p, c in rows
    ]


def build_report_data(db: Session, business_id: int) -> dict:
    """Compute all the weekly numbers in Python. Returns a JSON-serialisable dict."""
    today = date.today()
    end, start = today, today - timedelta(days=WEEK_DAYS - 1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=WEEK_DAYS - 1)

    products = product_repo.list_products(db, business_id)
    cost_map = {p.id: float(p.cost_price or 0) for p in products}
    name_map = {p.id: p.name for p in products}

    sales = sales_repo.get_all_sales(db, business_id)
    this_rows = [s for s in sales if s.sale_date and start <= s.sale_date <= end]
    last_rows = [s for s in sales if s.sale_date and prev_start <= s.sale_date <= prev_end]

    rev_this, profit_this = rev_profit([(s.product_id, s.quantity, s.total) for s in this_rows], cost_map)
    rev_last, profit_last = rev_profit([(s.product_id, s.quantity, s.total) for s in last_rows], cost_map)

    # Top products by revenue this week
    revenue_by_product: dict[int, float] = {}
    units_by_product: dict[int, float] = {}
    for s in this_rows:
        revenue_by_product[s.product_id] = revenue_by_product.get(s.product_id, 0.0) + float(s.total or 0)
        units_by_product[s.product_id] = units_by_product.get(s.product_id, 0.0) + float(s.quantity or 0)
    top_products = [
        {"name": name_map.get(pid, f"#{pid}"), "revenue": round(rev, 2), "units": round(units_by_product.get(pid, 0), 2)}
        for pid, rev in sorted(revenue_by_product.items(), key=lambda kv: kv[1], reverse=True)[:5]
    ]

    # Low-stock risks (reuse the forecasting model)
    risks = forecasting_service.get_reorder_recommendations(db, business_id)
    low_stock_risks = [
        {"name": f.product_name, "current_stock": f.current_stock, "days_until_stockout": f.days_until_stockout}
        for f in risks[:5]
    ]

    # Margins (most / least profitable products)
    margins = [
        {"name": p.name, "margin_pct": margin_pct(p.cost_price, p.selling_price)}
        for p in products
        if margin_pct(p.cost_price, p.selling_price) is not None
    ]
    margins.sort(key=lambda m: m["margin_pct"], reverse=True)

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "sales": {"this_week": rev_this, "last_week": rev_last, "change_pct": pct_change(rev_this, rev_last)},
        "profit": {"this_week": profit_this, "last_week": profit_last, "change_pct": pct_change(profit_this, profit_last)},
        "top_products": top_products,
        "low_stock_risks": low_stock_risks,
        "supplier_price_changes": _supplier_price_changes(db, business_id, start, end),
        "most_profitable": margins[0] if margins else None,
        "least_profitable": margins[-1] if margins else None,
    }


def _narrate(data: dict) -> str:
    from app.ai.llm import complete_text  # lazy: avoids openai import in tests

    return complete_text(WEEKLY_REPORT_PROMPT.format(data_json=json.dumps(data, indent=2)))


def generate(db: Session, business_id: Optional[int] = None):
    """Build the weekly numbers, have the LLM narrate them, and persist the report.

    Caller manages commit/rollback. Returns the created Report (flushed, with id).
    """
    business = product_repo.get_or_create_default_business(db)
    bid = business_id or business.id

    data = build_report_data(db, bid)
    summary = _narrate(data)

    report = report_repo.create_report(
        db, bid,
        period_start=date.fromisoformat(data["period"]["start"]),
        period_end=date.fromisoformat(data["period"]["end"]),
        summary_text=summary,
        data_json=data,
    )
    logger.info(
        "weekly_report_generated",
        report_id=report.id,
        sales_this_week=data["sales"]["this_week"],
        profit_this_week=data["profit"]["this_week"],
    )
    return report
