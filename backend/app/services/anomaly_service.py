"""Sales anomaly detection service.

Flow:
  1. For every product, build a daily sales series from the DB.
  2. Run rolling z-score detection (pure Python/numpy) — flags days that are
     more than 2σ above or below the 14-day rolling mean.
  3. Batch ALL flagged anomalies into a single LLM call for plain-English
     explanations. The LLM explains; it never calculates.
  4. Return a list of AnomalyAlert objects ready for the API.

Only anomalies in the last 7 days are returned — recent means actionable.
"""
from __future__ import annotations

import json
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.anomaly import daily_series, detect_anomalies
from app.core.logging import get_logger
from app.repositories import product_repo, sales_repo

logger = get_logger(__name__)

WINDOW = 14       # rolling baseline window in days
Z_THRESH = 2.0    # standard deviations to flag
LOOKBACK = 7      # only report anomalies this many days old


def _build_anomaly_list_text(raw: list[dict]) -> str:
    """Format anomalies as a numbered list for the LLM prompt."""
    lines = []
    for i, a in enumerate(raw, 1):
        lines.append(
            f"{i}. {a['product_name']} — {a['direction']} on {a['date']}: "
            f"sold {a['actual']} units vs normal {a['expected']}/day "
            f"({a['pct_deviation']:.0f}% deviation, z={a['z_score']:+.1f})"
        )
    return "\n".join(lines)


def _get_explanations(raw: list[dict]) -> list[str]:
    """Single LLM call → one explanation per anomaly in order."""
    from app.ai.llm import complete_json
    from app.ai.prompts import ANOMALY_EXPLANATION_PROMPT

    anomaly_text = _build_anomaly_list_text(raw)
    prompt = ANOMALY_EXPLANATION_PROMPT.format(anomaly_list=anomaly_text)
    try:
        result = json.loads(complete_json(prompt))
        explanations = result.get("explanations", [])
        if isinstance(explanations, list) and len(explanations) == len(raw):
            return [str(e) for e in explanations]
    except Exception as exc:
        logger.warning("anomaly_explanation_failed", err=str(exc))

    # Fallback: generate generic explanations without LLM
    return [
        f"{a['product_name']} sales showed an unusual {a['direction']} "
        f"({a['pct_deviation']:.0f}% from expected) on {a['date']}."
        for a in raw
    ]


def detect_all(db: Session, business_id: int) -> dict:
    """Scan all products and return recent anomalies with AI explanations."""
    products = product_repo.list_products(db, business_id)
    raw_anomalies: list[dict] = []

    for product in products:
        rows = sales_repo.get_sales_history(db, product.id)
        if not rows:
            continue
        series = daily_series(rows)
        flags = detect_anomalies(series, window=WINDOW, z_thresh=Z_THRESH, lookback_days=LOOKBACK)
        for flag in flags:
            flag["product_id"] = product.id
            flag["product_name"] = product.name
            raw_anomalies.append(flag)

    # Sort: most extreme z-scores first, then most recent
    raw_anomalies.sort(key=lambda a: (-abs(a["z_score"]), a["date"]))

    if not raw_anomalies:
        logger.info("anomaly_scan_clean", products_scanned=len(products))
        return {"alerts": [], "scanned_products": len(products), "window_days": WINDOW}

    explanations = _get_explanations(raw_anomalies)

    alerts = []
    for anomaly, explanation in zip(raw_anomalies, explanations):
        alerts.append({
            "product_id": anomaly["product_id"],
            "product_name": anomaly["product_name"],
            "anomaly_date": anomaly["date"],
            "direction": anomaly["direction"],
            "actual_qty": anomaly["actual"],
            "expected_qty": anomaly["expected"],
            "z_score": anomaly["z_score"],
            "pct_deviation": anomaly["pct_deviation"],
            "explanation": explanation,
        })

    logger.info("anomaly_scan_complete",
                products_scanned=len(products),
                anomalies_found=len(alerts))
    return {"alerts": alerts, "scanned_products": len(products), "window_days": WINDOW}
