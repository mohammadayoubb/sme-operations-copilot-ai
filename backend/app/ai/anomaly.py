"""Sales anomaly detection using rolling z-score.

Pure Python + numpy (already installed). No model training required.

Algorithm:
  For each day D with enough history:
    rolling_mean = mean of the previous `window` days of sales
    rolling_std  = std  of the previous `window` days of sales
    z_score      = (actual_D - rolling_mean) / rolling_std
  A day is anomalous when |z_score| > z_thresh.

Design note: the LLM only explains the flagged anomalies — all statistics
are computed here in plain Python before the LLM ever sees them.
"""
from __future__ import annotations

from datetime import date


def detect_anomalies(
    series: list[tuple[date, float]],
    window: int = 14,
    z_thresh: float = 2.0,
    lookback_days: int = 7,
) -> list[dict]:
    """Scan a daily sales series for unusual spikes or drops.

    Args:
        series:       [(date, qty)] sorted oldest → newest.
        window:       Rolling baseline window in days.
        z_thresh:     Standard deviations to count as anomalous.
        lookback_days: Only return anomalies this many days before today.

    Returns:
        List of anomaly dicts, one per flagged day, sorted most-recent first.
        Each dict: {date, actual, expected, z_score, direction, pct_deviation}.
    """
    import numpy as np

    if len(series) < window + 1:
        return []

    cutoff = date.today()
    earliest_alert = cutoff.replace(year=cutoff.year) if lookback_days is None else cutoff

    anomalies: list[dict] = []

    for i in range(window, len(series)):
        day, actual = series[i]

        # Only report recent anomalies
        delta = (cutoff - day).days
        if delta > lookback_days or delta < 0:
            continue

        window_vals = [qty for _, qty in series[i - window: i]]
        mean = float(np.mean(window_vals))
        # Floor at 10% of mean (min 0.5) so a flat baseline still detects
        # obvious spikes/drops without dividing by near-zero.
        std = max(float(np.std(window_vals, ddof=1)), mean * 0.10, 0.5)

        z = (actual - mean) / std
        if abs(z) < z_thresh:
            continue

        pct_dev = ((actual - mean) / mean * 100) if mean > 0 else 0.0

        anomalies.append({
            "date": day.isoformat(),
            "actual": round(actual, 1),
            "expected": round(mean, 1),
            "z_score": round(z, 2),
            "direction": "spike" if z > 0 else "drop",
            "pct_deviation": round(abs(pct_dev), 1),
        })

    # Most recent first
    anomalies.sort(key=lambda a: a["date"], reverse=True)
    return anomalies


def daily_series(sales_rows: list) -> list[tuple[date, float]]:
    """Aggregate sale rows into one (date, total_qty) entry per day."""
    totals: dict[date, float] = {}
    for row in sales_rows:
        d = row.sale_date
        if d is not None:
            totals[d] = totals.get(d, 0.0) + float(row.quantity or 0)
    return sorted(totals.items())
