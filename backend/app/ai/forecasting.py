"""Inventory demand forecasting (scikit-learn).

Pipeline:
  1. Turn raw sales rows into a continuous, 0-filled daily series (pandas).
  2. Feature-engineer a supervised dataset (lag_1, lag_7, roll_7, day-of-week).
  3. Train + compare three models — moving-average baseline, linear regression,
     random forest — and select the best by RMSE on a time-based holdout.
  4. Persist the winning artifact with joblib so it can be loaded for inference.
  5. Inference turns a product's recent series + stock into a reorder recommendation.

The feature-engineering and recommendation maths are plain pandas/numpy so they
can be unit-tested without a database or a trained model.
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd

FEATURE_COLS = ["lag_1", "lag_7", "roll_7", "dow"]
LEAD_TIME_DAYS = 3          # how long a restock takes to arrive
REORDER_HORIZON_DAYS = 7    # flag a product if it has < this many days of stock
HOLDOUT_DAYS = 14           # last N days used to score the models

MODEL_DIR = os.environ.get("ML_MODELS_DIR", "/app/ml_models")
MODEL_PATH = os.path.join(MODEL_DIR, "forecast_model.pkl")


# ── 1. Daily series ────────────────────────────────────────────────

def daily_series(rows: list) -> pd.Series:
    """Build a continuous daily quantity series from sales rows.

    `rows` may be ORM `Sale` objects (with `.sale_date` / `.quantity`) or
    (date, quantity) tuples. Missing calendar days are filled with 0.
    """
    dates: list = []
    qtys: list[float] = []
    for r in rows:
        if isinstance(r, (tuple, list)):
            d, q = r[0], r[1]
        else:
            d, q = r.sale_date, r.quantity
        if d is None:
            continue
        dates.append(pd.Timestamp(d))
        qtys.append(float(q or 0))

    if not dates:
        return pd.Series(dtype="float64")

    s = pd.Series(qtys, index=pd.DatetimeIndex(dates))
    s = s.groupby(s.index).sum()                      # collapse multiple sales/day
    full = pd.date_range(s.index.min(), s.index.max(), freq="D")
    return s.reindex(full, fill_value=0.0).astype("float64")


# ── 2. Features ────────────────────────────────────────────────────

def compute_basic_features(series: pd.Series, current_stock: Optional[float] = None) -> dict:
    """Plain descriptive features used both for display and recommendations."""
    n = len(series)
    if n == 0:
        return {
            "avg_daily_sales": 0.0,
            "sales_last_7d": 0.0,
            "sales_last_30d": 0.0,
            "days_of_stock_remaining": None,
        }

    recent = series.tail(min(30, n))
    avg_daily = float(recent.mean()) if len(recent) else 0.0
    last_7d = float(series.tail(7).sum())
    last_30d = float(series.tail(30).sum())

    days_left: Optional[float] = None
    if current_stock is not None and avg_daily > 0:
        days_left = round(current_stock / avg_daily, 2)

    return {
        "avg_daily_sales": round(avg_daily, 3),
        "sales_last_7d": round(last_7d, 2),
        "sales_last_30d": round(last_30d, 2),
        "days_of_stock_remaining": days_left,
    }


def make_supervised(series: pd.Series) -> pd.DataFrame:
    """Build a supervised frame: lag_1, lag_7, roll_7, dow → target `y`."""
    if len(series) < 9:
        return pd.DataFrame(columns=["date", *FEATURE_COLS, "y"])

    df = pd.DataFrame({"y": series})
    df["lag_1"] = df["y"].shift(1)
    df["lag_7"] = df["y"].shift(7)
    df["roll_7"] = df["y"].shift(1).rolling(7).mean()
    df["dow"] = df.index.dayofweek
    df["date"] = df.index
    df = df.dropna().reset_index(drop=True)
    return df[["date", *FEATURE_COLS, "y"]]


def latest_feature_row(series: pd.Series) -> Optional[dict]:
    """Feature row for predicting the *next* (unobserved) day."""
    if len(series) < 8:
        return None
    vals = series.values
    next_day = series.index[-1] + pd.Timedelta(days=1)
    return {
        "lag_1": float(vals[-1]),
        "lag_7": float(vals[-7]),
        "roll_7": float(np.mean(vals[-7:])),
        "dow": int(next_day.dayofweek),
    }


# ── 3. Train + compare + select ────────────────────────────────────

def _rmse(y_true, y_pred) -> float:
    return float(np.sqrt(np.mean((np.asarray(y_true) - np.asarray(y_pred)) ** 2)))


def _mae(y_true, y_pred) -> float:
    return float(np.mean(np.abs(np.asarray(y_true) - np.asarray(y_pred))))


def train_and_select(series_by_product: dict) -> dict:
    """Train the three models on all products' history and pick the best.

    Returns an artifact dict: {model, model_name, feature_cols, metrics, trained_at}.
    `model` is a fitted sklearn estimator, or None when the moving-average
    baseline wins (inference then just uses the roll_7 feature).
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression

    frames = [make_supervised(s) for s in series_by_product.values()]
    frames = [f for f in frames if not f.empty]
    if not frames:
        raise ValueError("not enough sales history to train a forecasting model")

    data = pd.concat(frames, ignore_index=True).sort_values("date")

    # Time-based holdout: last HOLDOUT_DAYS by calendar date.
    cutoff = data["date"].max() - pd.Timedelta(days=HOLDOUT_DAYS)
    train = data[data["date"] <= cutoff]
    test = data[data["date"] > cutoff]
    if len(train) < 10 or test.empty:          # tiny dataset → skip holdout
        train, test = data, data

    X_train, y_train = train[FEATURE_COLS], train["y"]
    X_test, y_test = test[FEATURE_COLS], test["y"]

    candidates: dict = {
        "moving_average": None,  # baseline: prediction = roll_7
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(n_estimators=120, random_state=42, n_jobs=-1),
    }

    metrics: dict = {}
    fitted: dict = {}
    for name, est in candidates.items():
        if est is None:
            preds = X_test["roll_7"].values
        else:
            est.fit(X_train, y_train)
            preds = est.predict(X_test)
        fitted[name] = est
        metrics[name] = {"rmse": round(_rmse(y_test, preds), 4), "mae": round(_mae(y_test, preds), 4)}

    best_name = min(metrics, key=lambda k: metrics[k]["rmse"])

    return {
        "model": fitted[best_name],
        "model_name": best_name,
        "feature_cols": FEATURE_COLS,
        "metrics": metrics,
        "trained_at": pd.Timestamp.utcnow().isoformat(),
        "n_train_rows": int(len(train)),
    }


# ── 4. Persistence ─────────────────────────────────────────────────

def save_model(artifact: dict, path: str = MODEL_PATH) -> str:
    import joblib

    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(artifact, path)
    return path


def load_model(path: str = MODEL_PATH) -> Optional[dict]:
    import joblib

    if not os.path.exists(path):
        return None
    return joblib.load(path)


# ── 5. Inference ───────────────────────────────────────────────────

def predict_daily_demand(series: pd.Series, artifact: Optional[dict]) -> float:
    """Predict next-day demand for one product. Falls back to the recent mean."""
    row = latest_feature_row(series)
    if row is None:
        recent = series.tail(7)
        return round(float(recent.mean()), 3) if len(recent) else 0.0

    if artifact is None or artifact.get("model") is None:
        pred = row["roll_7"]                          # moving-average baseline
    else:
        cols = artifact["feature_cols"]
        X = pd.DataFrame([[row[c] for c in cols]], columns=cols)
        pred = float(artifact["model"].predict(X)[0])

    return round(max(pred, 0.0), 3)


def forecast_product(
    series: pd.Series,
    current_stock: float,
    reorder_level: float,
    artifact: Optional[dict] = None,
) -> dict:
    """Turn a product's history + stock into a reorder recommendation."""
    feats = compute_basic_features(series, current_stock)

    # The model's forecast drives the stockout estimate; fall back to the
    # descriptive average if the model can't produce a positive rate.
    model_rate = predict_daily_demand(series, artifact)
    avg_daily = model_rate if model_rate > 0 else feats["avg_daily_sales"]

    days_until_stockout: Optional[float] = None
    reorder_by_date: Optional[str] = None
    if avg_daily > 0:
        days_until_stockout = round(current_stock / avg_daily, 2)
        lead = max(0.0, days_until_stockout - LEAD_TIME_DAYS)
        reorder_by_date = (date.today() + timedelta(days=int(lead))).isoformat()

    reorder_recommended = bool(
        current_stock <= reorder_level
        or (days_until_stockout is not None and days_until_stockout <= REORDER_HORIZON_DAYS)
    )

    return {
        "current_stock": round(float(current_stock), 2),
        "avg_daily_sales": round(float(avg_daily), 3),
        "sales_last_7d": feats["sales_last_7d"],
        "sales_last_30d": feats["sales_last_30d"],
        "days_until_stockout": days_until_stockout,
        "reorder_recommended": reorder_recommended,
        "reorder_by_date": reorder_by_date,
    }
