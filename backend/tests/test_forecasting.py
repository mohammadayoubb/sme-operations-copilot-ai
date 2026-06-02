"""Tests for the forecasting core (feature engineering + model train/predict).

These exercise the deterministic pandas/numpy maths and a small end-to-end
train→predict cycle. No database is needed.
"""
import numpy as np
import pandas as pd
import pytest

from app.ai import forecasting


def _synthetic_series(days: int = 60, base: float = 5.0, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2026-01-01")
    idx = pd.date_range(start, periods=days, freq="D")
    weekend = np.where(idx.dayofweek >= 5, 3.0, 0.0)
    qty = np.clip(base + weekend + rng.normal(0, 1.0, days), 0, None).round()
    return pd.Series(qty, index=idx, dtype="float64")


def test_daily_series_fills_missing_days_and_sums_duplicates():
    rows = [
        ("2026-01-01", 2),
        ("2026-01-01", 3),   # same day → summed
        ("2026-01-04", 5),   # gap on the 2nd and 3rd → 0-filled
    ]
    s = forecasting.daily_series(rows)
    assert list(s.index.strftime("%Y-%m-%d")) == ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]
    assert s.iloc[0] == 5.0          # 2 + 3
    assert s.iloc[1] == 0.0 and s.iloc[2] == 0.0
    assert s.iloc[3] == 5.0


def test_compute_basic_features_shape_and_values():
    s = _synthetic_series(days=30, base=4.0)
    feats = forecasting.compute_basic_features(s, current_stock=20)

    assert set(feats) == {"avg_daily_sales", "sales_last_7d", "sales_last_30d", "days_of_stock_remaining"}
    assert feats["avg_daily_sales"] > 0
    assert feats["sales_last_7d"] == pytest.approx(float(s.tail(7).sum()))
    # days_of_stock_remaining = stock / avg_daily
    assert feats["days_of_stock_remaining"] == pytest.approx(20 / feats["avg_daily_sales"], abs=0.05)


def test_compute_basic_features_handles_empty_series():
    feats = forecasting.compute_basic_features(pd.Series(dtype="float64"), current_stock=10)
    assert feats["avg_daily_sales"] == 0.0
    assert feats["days_of_stock_remaining"] is None


def test_make_supervised_has_expected_columns():
    s = _synthetic_series(days=40)
    df = forecasting.make_supervised(s)
    assert list(df.columns) == ["date", "lag_1", "lag_7", "roll_7", "dow", "y"]
    assert len(df) > 0
    assert not df[forecasting.FEATURE_COLS].isnull().any().any()


def test_train_and_select_returns_valid_artifact_and_metrics():
    series = {1: _synthetic_series(seed=1), 2: _synthetic_series(seed=2, base=8.0)}
    art = forecasting.train_and_select(series)

    assert art["model_name"] in {"moving_average", "linear_regression", "random_forest"}
    assert set(art["metrics"]) == {"moving_average", "linear_regression", "random_forest"}
    for m in art["metrics"].values():
        assert m["rmse"] >= 0 and m["mae"] >= 0
    assert art["feature_cols"] == forecasting.FEATURE_COLS


def test_predict_daily_demand_is_nonnegative_float():
    s = _synthetic_series(seed=3)
    art = forecasting.train_and_select({1: s})
    pred = forecasting.predict_daily_demand(s, art)
    assert isinstance(pred, float)
    assert pred >= 0


def test_forecast_product_recommends_reorder_when_stock_low():
    s = _synthetic_series(seed=4, base=5.0)
    art = forecasting.train_and_select({1: s})

    low = forecasting.forecast_product(s, current_stock=4, reorder_level=10, artifact=art)
    assert low["reorder_recommended"] is True
    assert low["days_until_stockout"] is not None and low["days_until_stockout"] > 0
    assert low["reorder_by_date"] is not None

    high = forecasting.forecast_product(s, current_stock=500, reorder_level=10, artifact=art)
    assert high["reorder_recommended"] is False


def test_save_and_load_roundtrip(tmp_path):
    art = forecasting.train_and_select({1: _synthetic_series(seed=5)})
    path = str(tmp_path / "model.pkl")
    forecasting.save_model(art, path)
    loaded = forecasting.load_model(path)
    assert loaded is not None
    assert loaded["model_name"] == art["model_name"]
    assert loaded["feature_cols"] == forecasting.FEATURE_COLS
