"""Pricing / profit advisor.

`calculate_margin` is pure Python — the LLM is NEVER asked to do arithmetic.
`analyze_smart` pulls live context from the DB (velocity, cost trend) and asks
the LLM to write a 3-part strategic recommendation based on the full picture.
"""
from __future__ import annotations

import json
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.prompts import PRICING_EXPLANATION_PROMPT, PRICING_STRATEGY_PROMPT
from app.core.logging import get_logger
from app.schemas.pricing import (
    CostTrend,
    PricingRequest,
    PricingResponse,
    PricingScenario,
    ProductPricingInfo,
)

logger = get_logger(__name__)

TARGET_MARGIN = 0.25  # 25%
SCENARIO_TARGETS = [0, 15, 20, 25, 30]  # margin % targets for the scenario table
VELOCITY_WINDOW_DAYS = 30


# ── Pure-Python math (tests depend on this staying unchanged) ───────────────

def calculate_margin(cost: float, sell: float, delivery: float = 0.0, packaging: float = 0.0) -> dict:
    """Compute profit, margin %, and the price needed for a 25% margin.

    Pure arithmetic, no LLM. Handles the edge cases the tests care about:
    zero selling price, zero cost, and negative margins.
    """
    total_cost = round(cost + delivery + packaging, 2)
    profit = round(sell - total_cost, 2)

    # Margin is profit as a share of the selling price; undefined when sell == 0.
    margin_pct = round(profit / sell * 100, 2) if sell > 0 else 0.0

    # Price P such that (P - total_cost) / P = 0.25  =>  P = total_cost / 0.75.
    sell_for_25pct = round(total_cost / (1 - TARGET_MARGIN), 2) if total_cost > 0 else 0.0

    return {
        "total_cost": total_cost,
        "profit": profit,
        "margin_pct": margin_pct,
        "sell_for_25pct": sell_for_25pct,
    }


def calculate_scenarios(total_cost: float) -> list[PricingScenario]:
    """Return a table of required selling prices for each target margin."""
    scenarios = []
    for target_pct in SCENARIO_TARGETS:
        if target_pct == 0:
            required_price = round(total_cost, 2)
            label = "Break-even"
        else:
            required_price = round(total_cost / (1 - target_pct / 100), 2)
            label = f"{target_pct}% margin"
        profit = round(required_price - total_cost, 2)
        scenarios.append(PricingScenario(
            label=label,
            target_margin_pct=float(target_pct),
            required_price=required_price,
            profit=profit,
        ))
    return scenarios


# ── DB context helpers (pure Python, no LLM) ────────────────────────────────

def _get_velocity(db: Session, product_id: int) -> tuple[str, Optional[float]]:
    """Return (label, avg_daily_sales) from the last 30 days of sales history."""
    from app.repositories.sales_repo import get_sales_history

    sales = get_sales_history(db, product_id, days=VELOCITY_WINDOW_DAYS)
    if not sales:
        return "unknown", None
    total_qty = sum(float(s.quantity or 0) for s in sales)
    avg_daily = round(total_qty / VELOCITY_WINDOW_DAYS, 2)
    if avg_daily >= 5:
        label = "fast"
    elif avg_daily >= 1:
        label = "medium"
    else:
        label = "slow"
    return label, avg_daily


def _get_cost_trend(db: Session, product_id: int) -> Optional[CostTrend]:
    """Return the direction and magnitude of supplier cost change from invoice history."""
    from app.repositories.product_repo import price_history

    history = price_history(db, product_id)  # oldest → newest
    if len(history) < 2:
        return None
    _, prev_cost = history[-2]
    _, curr_cost = history[-1]
    if prev_cost == 0:
        return None
    change_pct = round((curr_cost - prev_cost) / prev_cost * 100, 2)
    direction = "up" if change_pct > 0.5 else "down" if change_pct < -0.5 else "flat"
    return CostTrend(
        prev_cost=prev_cost,
        current_cost=curr_cost,
        change_pct=change_pct,
        direction=direction,
    )


# ── LLM layer ───────────────────────────────────────────────────────────────

def explain_pricing(req: PricingRequest, calc: dict) -> str:
    """Legacy plain-text explanation (kept for backward compat)."""
    from app.ai.llm import complete_text

    prompt = PRICING_EXPLANATION_PROMPT.format(
        cost=req.cost,
        sell=req.sell,
        delivery=req.delivery,
        packaging=req.packaging,
        profit=calc["profit"],
        margin_pct=calc["margin_pct"],
    )
    return complete_text(prompt)


def _llm_strategy(
    req: PricingRequest,
    calc: dict,
    scenarios: list[PricingScenario],
    velocity: str,
    avg_daily: Optional[float],
    cost_trend: Optional[CostTrend],
) -> tuple[str, str, str]:
    """Return (assessment, recommendation, risk) from the LLM."""
    from app.ai.llm import complete_json

    scenario_lines = "\n".join(
        f"  • {s.label}: ${s.required_price:.2f}  (profit ${s.profit:.2f}/unit)"
        for s in scenarios
    )

    if cost_trend:
        direction_word = "up" if cost_trend.direction == "up" else "down" if cost_trend.direction == "down" else "unchanged"
        cost_trend_line = (
            f"Supplier cost trend: {direction_word} {abs(cost_trend.change_pct):.1f}%"
            f" (was ${cost_trend.prev_cost:.2f}, now ${cost_trend.current_cost:.2f})"
        )
    else:
        cost_trend_line = "Supplier cost trend: not available"

    product_name = req.product_name or "this product"
    avg_daily_str = f"{avg_daily:.1f}" if avg_daily is not None else "N/A"

    prompt = PRICING_STRATEGY_PROMPT.format(
        product_name=product_name,
        sell=req.sell,
        margin_pct=calc["margin_pct"],
        cost=req.cost,
        delivery=req.delivery,
        packaging=req.packaging,
        total_cost=calc["total_cost"],
        scenarios_table=scenario_lines,
        velocity=velocity,
        avg_daily=avg_daily_str,
        cost_trend_line=cost_trend_line,
    )

    raw = complete_json(prompt)
    try:
        parsed = json.loads(raw)
        assessment = str(parsed.get("assessment") or "")
        recommendation = str(parsed.get("recommendation") or "")
        risk = str(parsed.get("risk") or "")
    except Exception:
        assessment = recommendation = risk = ""

    return assessment, recommendation, risk


# ── Main entry points ────────────────────────────────────────────────────────

def analyze(req: PricingRequest) -> PricingResponse:
    """Legacy entry point (no DB). Still works for tests and manual-only calls."""
    calc = calculate_margin(req.cost, req.sell, req.delivery, req.packaging)
    explanation = explain_pricing(req, calc)
    scenarios = calculate_scenarios(calc["total_cost"])
    logger.info("pricing_analyzed", margin_pct=calc["margin_pct"], profit=calc["profit"])
    return PricingResponse(
        **calc,
        scenarios=scenarios,
        velocity="unknown",
        velocity_avg_daily=None,
        cost_trend=None,
        assessment="",
        recommendation=explanation,
        risk="",
        explanation=explanation,
    )


def analyze_smart(req: PricingRequest, db: Session, business_id: int | None = None) -> PricingResponse:
    """Full flow: Python math + DB context + structured LLM strategy."""
    # 1. Core margin numbers — pure Python
    calc = calculate_margin(req.cost, req.sell, req.delivery, req.packaging)

    # 2. Scenario table — pure Python
    scenarios = calculate_scenarios(calc["total_cost"])

    # 3. DB context (only when product_id is given)
    velocity: str = "unknown"
    avg_daily: Optional[float] = None
    cost_trend: Optional[CostTrend] = None

    if req.product_id:
        try:
            velocity, avg_daily = _get_velocity(db, req.product_id)
            cost_trend = _get_cost_trend(db, req.product_id)
        except Exception as exc:
            logger.warning("pricing_context_fetch_failed", err=str(exc))

    # 4. LLM strategy — never calculates, only interprets
    assessment, recommendation, risk = _llm_strategy(
        req, calc, scenarios, velocity, avg_daily, cost_trend
    )

    explanation = "\n\n".join(filter(None, [assessment, recommendation, risk]))

    logger.info(
        "pricing_smart_analyzed",
        product_id=req.product_id,
        margin_pct=calc["margin_pct"],
        velocity=velocity,
        has_cost_trend=cost_trend is not None,
    )

    return PricingResponse(
        **calc,
        scenarios=scenarios,
        velocity=velocity,
        velocity_avg_daily=avg_daily,
        cost_trend=cost_trend,
        assessment=assessment,
        recommendation=recommendation,
        risk=risk,
        explanation=explanation,
    )


# ── Product listing for the frontend dropdown ────────────────────────────────

def list_products_with_context(db: Session, business_id: int) -> list[ProductPricingInfo]:
    """Return every product with its latest invoice cost and sales velocity."""
    from app.repositories.product_repo import list_products, price_history

    products = list_products(db, business_id)
    result = []

    for p in products:
        history = price_history(db, p.id)
        latest_cost: Optional[float] = history[-1][1] if history else None
        cost_change_pct: Optional[float] = None
        if len(history) >= 2:
            prev = history[-2][1]
            if prev and prev != 0:
                cost_change_pct = round((history[-1][1] - prev) / prev * 100, 2)

        vel, avg_daily = _get_velocity(db, p.id)

        result.append(ProductPricingInfo(
            id=p.id,
            name=p.name,
            current_stock=float(p.current_stock or 0),
            latest_cost=latest_cost,
            cost_change_pct=cost_change_pct,
            avg_daily_sales=avg_daily,
            velocity=vel,
        ))

    return result
