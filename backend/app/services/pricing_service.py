"""Pricing / profit advisor.

`calculate_margin` is pure Python — the LLM is NEVER asked to do arithmetic.
`explain_pricing` takes the already-computed numbers and asks the LLM to write a
short, business-friendly explanation (PRICING_EXPLANATION_PROMPT).
"""
from __future__ import annotations

from app.ai.prompts import PRICING_EXPLANATION_PROMPT
from app.core.logging import get_logger
from app.schemas.pricing import PricingRequest, PricingResponse

logger = get_logger(__name__)

TARGET_MARGIN = 0.25  # 25%


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


def explain_pricing(req: PricingRequest, calc: dict) -> str:
    """Ask the LLM to explain the (already computed) numbers in plain language."""
    from app.ai.llm import complete_text  # lazy: avoids openai import in tests

    prompt = PRICING_EXPLANATION_PROMPT.format(
        cost=req.cost,
        sell=req.sell,
        delivery=req.delivery,
        packaging=req.packaging,
        profit=calc["profit"],
        margin_pct=calc["margin_pct"],
    )
    return complete_text(prompt)


def analyze(req: PricingRequest) -> PricingResponse:
    """Full flow: compute the numbers in Python, then have the LLM explain them."""
    calc = calculate_margin(req.cost, req.sell, req.delivery, req.packaging)
    explanation = explain_pricing(req, calc)
    logger.info("pricing_analyzed", margin_pct=calc["margin_pct"], profit=calc["profit"])
    return PricingResponse(**calc, explanation=explanation)
