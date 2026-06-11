"""Data-drift detection using Population Stability Index (PSI).

Compares recent sales distribution (last 7 days) against a 60-day baseline
to flag when the incoming data has shifted enough that the trained forecasting
model may produce unreliable predictions.

PSI interpretation (industry standard):
  PSI < 0.10  → stable   — no action needed
  PSI 0.10–0.20 → warning — monitor, consider retraining
  PSI > 0.20  → alert    — significant shift, retrain model

All logic is deterministic numpy/Python — no LLM, no DB.
"""
from __future__ import annotations

import numpy as np

PSI_WARNING = 0.10
PSI_ALERT = 0.20
DEFAULT_BINS = 10


def _psi_bin(actual_pct: float, expected_pct: float) -> float:
    """PSI contribution for a single bin. Epsilon-guards zero-frequency bins."""
    eps = 1e-6
    a = max(actual_pct, eps)
    e = max(expected_pct, eps)
    return (a - e) * np.log(a / e)


def compute_psi(baseline: list[float], recent: list[float], bins: int = DEFAULT_BINS) -> float:
    """Compute PSI between a baseline and a recent distribution.

    Bins are derived from baseline quantiles so the scale is anchored to the
    training window rather than the potentially-shifted recent window.

    Returns 0.0 when either list is empty (nothing to compare).
    """
    if not baseline or not recent:
        return 0.0

    b = np.asarray(baseline, dtype=float)
    r = np.asarray(recent, dtype=float)

    # Adapt bin count to sample size — standard rule is >= 5 observations per bin.
    bins = min(bins, max(2, len(recent) // 5))

    quantiles = np.linspace(0, 100, bins + 1)
    edges = np.percentile(b, quantiles)
    edges[0] = -np.inf
    edges[-1] = np.inf

    b_counts, _ = np.histogram(b, bins=edges)
    r_counts, _ = np.histogram(r, bins=edges)

    b_pcts = b_counts / max(len(b), 1)
    r_pcts = r_counts / max(len(r), 1)

    psi = float(sum(_psi_bin(rp, bp) for rp, bp in zip(r_pcts, b_pcts)))
    return round(max(psi, 0.0), 4)


def psi_status(psi: float) -> str:
    """Human-readable status label from a PSI score."""
    if psi >= PSI_ALERT:
        return "alert"
    if psi >= PSI_WARNING:
        return "warning"
    return "stable"
