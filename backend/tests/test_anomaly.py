"""Unit tests for the anomaly detection core.

All tests are purely deterministic — no DB, no LLM, no network.
"""
from datetime import date, timedelta

from app.ai.anomaly import daily_series, detect_anomalies


def _make_series(values: list[float], start: date | None = None) -> list[tuple[date, float]]:
    """Build a (date, qty) series from a list of daily values."""
    if start is None:
        # Place the series so the last few days fall within the lookback window
        start = date.today() - timedelta(days=len(values) - 1)
    return [(start + timedelta(days=i), v) for i, v in enumerate(values)]


# ── daily_series ──────────────────────────────────────────────────

def test_daily_series_aggregates_same_day():
    """Two sales rows on the same date should be summed."""
    class FakeRow:
        def __init__(self, d, qty):
            self.sale_date = d
            self.quantity = qty

    today = date.today()
    rows = [FakeRow(today, 3.0), FakeRow(today, 5.0)]
    result = daily_series(rows)
    assert len(result) == 1
    assert result[0] == (today, 8.0)


def test_daily_series_sorted():
    class FakeRow:
        def __init__(self, d, qty):
            self.sale_date = d
            self.quantity = qty

    today = date.today()
    rows = [FakeRow(today, 5.0), FakeRow(today - timedelta(days=1), 3.0)]
    result = daily_series(rows)
    assert result[0][0] < result[1][0]


# ── detect_anomalies — edge cases ─────────────────────────────────

def test_detect_anomalies_too_short_returns_empty():
    """Series shorter than window + 1 should return no anomalies."""
    series = _make_series([5.0] * 10)  # window default = 14
    assert detect_anomalies(series) == []


def test_detect_anomalies_flat_series_no_flags():
    """Perfectly flat sales → zero variance → no anomalies flagged."""
    series = _make_series([10.0] * 30)
    # std=0 → skipped, so no anomalies
    assert detect_anomalies(series) == []


def test_detect_anomalies_spike_detected():
    """A sudden large spike at the end of the series must be flagged."""
    base = [10.0] * 25        # stable baseline
    spike = [10.0] * 4 + [80.0]  # big spike 3 days ago
    today = date.today()
    start = today - timedelta(days=len(base + spike) - 1)
    series = _make_series(base + spike, start=start)

    anomalies = detect_anomalies(series, window=14, z_thresh=2.0, lookback_days=7)
    assert len(anomalies) >= 1
    assert anomalies[0]["direction"] == "spike"
    assert anomalies[0]["z_score"] > 2.0


def test_detect_anomalies_drop_detected():
    """A sudden large drop at the end of the series must be flagged."""
    base = [20.0] * 25
    drop = [20.0] * 4 + [1.0]
    today = date.today()
    start = today - timedelta(days=len(base + drop) - 1)
    series = _make_series(base + drop, start=start)

    anomalies = detect_anomalies(series, window=14, z_thresh=2.0, lookback_days=7)
    assert len(anomalies) >= 1
    assert anomalies[0]["direction"] == "drop"
    assert anomalies[0]["z_score"] < -2.0


def test_detect_anomalies_old_anomaly_excluded():
    """An anomaly outside the lookback window must not be reported."""
    base = [10.0] * 20
    old_spike = [80.0]        # spike 10 days ago
    recent_normal = [10.0] * 10
    today = date.today()
    start = today - timedelta(days=len(base + old_spike + recent_normal) - 1)
    series = _make_series(base + old_spike + recent_normal, start=start)

    anomalies = detect_anomalies(series, window=14, z_thresh=2.0, lookback_days=7)
    # The spike is 10 days ago; lookback is 7 — should not appear
    assert all(a["direction"] == "spike" and
               (date.today() - date.fromisoformat(a["date"])).days <= 7
               for a in anomalies)


def test_detect_anomalies_fields_present():
    """Each returned anomaly must have all expected keys."""
    base = [10.0] * 25
    spike = [10.0] * 4 + [90.0]
    today = date.today()
    start = today - timedelta(days=len(base + spike) - 1)
    series = _make_series(base + spike, start=start)

    anomalies = detect_anomalies(series, window=14, z_thresh=2.0, lookback_days=7)
    assert anomalies, "expected at least one anomaly"
    for a in anomalies:
        assert "date" in a
        assert "actual" in a
        assert "expected" in a
        assert "z_score" in a
        assert "direction" in a
        assert "pct_deviation" in a


def test_detect_anomalies_sorted_most_recent_first():
    """Returned anomalies must be sorted most-recent date first."""
    base = [10.0] * 20
    spikes = [10.0, 90.0, 10.0, 90.0, 10.0]
    today = date.today()
    start = today - timedelta(days=len(base + spikes) - 1)
    series = _make_series(base + spikes, start=start)

    anomalies = detect_anomalies(series, window=14, z_thresh=2.0, lookback_days=7)
    dates = [a["date"] for a in anomalies]
    assert dates == sorted(dates, reverse=True)
