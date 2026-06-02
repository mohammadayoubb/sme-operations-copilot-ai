# SoukPilot AI — Phase 3 Summary

**Features:** Pricing / Profit Advisor + Inventory Forecasting (ML)
**Status:** ✅ Complete, tested (Swagger + frontend), committed to `main`
**Date:** 2026-06-02

---

## 1. What Phase 3 Does (in plain words)

Two features were added in this phase.

### Feature A — Pricing / Profit Advisor
The owner types in their **cost price, selling price, delivery cost, and packaging
cost**. The system **calculates the profit and margin in plain Python**, then asks
the AI to **explain the numbers** in simple business language and suggest how to
improve. The AI never does the math — it only explains the numbers Python computed.

> Example: cost $7, sell $10, delivery $1, packaging $0.50
> → total cost **$8.50**, profit **$1.50**, margin **15%**, price for 25% margin **$11.33**
> → AI: *"…to improve the margin, reduce delivery/packaging or raise the price."*

### Feature B — Inventory Forecasting (Machine Learning)
The system learns from **sales history** to predict **which products will run out
soon** and **when to reorder**. It trains real scikit-learn models, compares them,
and uses the best one.

> Example: Nutella 400g — stock 8, **avg 3.14 sold/day**, **runs out in ~2.5 days**,
> **reorder recommended**. Meanwhile Pepsi (120 in stock, ~8 days left) is **not**
> flagged — so it's a real forecast, not a blanket "everything is low" warning.

---

## 2. Feature A — Pricing Advisor

### 2.1 Flow
```
Owner enters costs (Frontend: Pricing Advisor page)
        │  POST /api/pricing/analyze  { cost, sell, delivery, packaging }
        ▼
  pricing_service.analyze()
    1. calculate_margin()   ← PURE PYTHON arithmetic
    2. explain_pricing()    ← LLM (complete_text) explains the numbers
        ▼
  { total_cost, profit, margin_pct, sell_for_25pct, explanation }
        ▼
  Frontend shows 4 metric cards + AI explanation box
```

### 2.2 The math (all in Python, never the LLM)
- `total_cost = cost + delivery + packaging`
- `profit = sell − total_cost`
- `margin_pct = profit / sell × 100`  (returns 0 when `sell = 0`, so no divide-by-zero)
- `sell_for_25pct = total_cost / 0.75`  (the price `P` where `(P − total_cost)/P = 25%`)

### 2.3 Files
| File | Purpose |
|------|---------|
| `backend/app/schemas/pricing.py` | `PricingRequest`, `PricingResponse`, `PriceHistoryPoint` |
| `backend/app/services/pricing_service.py` | `calculate_margin()` (pure) + `explain_pricing()` (LLM) + `analyze()` |
| `backend/app/api/pricing.py` | `POST /analyze`, `GET /history/{product_id}` |
| `backend/app/repositories/product_repo.py` | `price_history()` (+ `list_products`, `get_product`) |
| `frontend/src/pages/PricingAdvisor.tsx` | Input form, metric cards, AI explanation |
| `backend/tests/test_pricing.py` | 6 tests (incl. zero cost, zero sell, negative margin) |

`GET /api/pricing/history/{id}` returns a product's unit-price history from past
invoice items (e.g. Pepsi at $0.42 from the Phase 1 invoice).

---

## 3. Feature B — Inventory Forecasting

### 3.1 The ML pipeline
```
Sales history (sales table)
        │
        ▼  daily_series()           → one row per calendar day, 0-filled
        ▼  make_supervised()        → features: lag_1, lag_7, roll_7, day-of-week → target
        ▼  train_and_select()       → train + compare 3 models, pick best by RMSE
              • moving-average baseline
              • linear regression
              • random forest
        ▼  save_model() (joblib)    → /app/ml_models/forecast_model.pkl
        ▼  forecast_product()       → avg_daily_sales, days_until_stockout,
                                       reorder_recommended, reorder_by_date
```

### 3.2 How a recommendation is made
1. Predict the product's daily demand with the trained model (falls back to the
   recent average if the model can't produce a positive rate).
2. `days_until_stockout = current_stock / avg_daily_sales`.
3. **Reorder if** `current_stock ≤ reorder_level` **or** `days_until_stockout ≤ 7`.
4. `reorder_by_date = stockout_date − lead_time (3 days)`, floored at today — so
   urgent items say "today" and well-stocked items get a real future date.

### 3.3 The three models (live result from `POST /retrain`)
| Model | RMSE | MAE |
|-------|------|-----|
| moving_average (baseline) | 2.31 | 1.85 |
| **linear_regression (winner)** | **1.87** | **1.44** |
| random_forest | 1.98 | 1.54 |

The winner is saved to `ml_models/forecast_model.pkl` with joblib.

### 3.4 Files
| File | Purpose |
|------|---------|
| `backend/app/models/sales.py` | `Sale` ORM model (maps the existing `sales` table) |
| `backend/app/repositories/sales_repo.py` | Read sales history (per product / all) |
| `backend/app/ai/forecasting.py` | Feature engineering, train/compare/select, save/load, inference |
| `backend/app/services/forecasting_service.py` | Load-or-train artifact, per-product inference, recommendations |
| `backend/app/schemas/forecast.py` | `ProductForecast`, `RetrainResult` |
| `backend/app/schemas/product.py` | `ProductOut` (inventory table) |
| `backend/app/api/forecast.py` | `GET /reorder`, `GET /stockout/{id}`, `POST /retrain` |
| `backend/app/api/products.py` | `GET /` + `GET /{id}` (inventory table) |
| `backend/app/workers/forecast_tasks.py` | `retrain_forecasting_model` Celery task (weekly beat) |
| `frontend/src/pages/Inventory.tsx` | Reorder cards + all-products table |
| `sample_data/seed_sales.py` | Generates 60 days of realistic sales history |
| `backend/tests/test_forecasting.py` | 8 tests (features, train/select, predict, recommend, save/load) |

### 3.5 API endpoints
| Method & Path | Purpose |
|---|---|
| `GET /api/forecast/reorder` | Products needing reorder, soonest stockout first |
| `GET /api/forecast/stockout/{product_id}` | Full forecast for one product |
| `POST /api/forecast/retrain` | Train+compare now, return RMSE/MAE + saved model path |

> **Sync vs. async:** `/retrain` runs **synchronously** (the dataset is small) so the
> RMSE comparison comes straight back in Swagger. The same work also runs **weekly**
> via the `retrain_forecasting_model` Celery beat task.

---

## 4. The Seed Data

`sample_data/seed_sales.py` creates 60 days of history for the four demo grocery
products with **weekly seasonality** (weekend bumps) and **random noise**, then sets
stock levels so the forecast is interesting:

| Product | Stock | ~Avg/day | Result |
|---------|-------|----------|--------|
| Pepsi 330ml | 120 | ~14.8 | OK (~8 days) — **not** flagged |
| Lays Chips 45g | 30 | ~8.1 | Reorder (~3.7 days) |
| Water 1.5L | 18 | ~10.7 | Reorder (~1.7 days) |
| Nutella 400g | 8 | ~3.1 | Reorder (~2.5 days) |

Run it inside the backend container:
```bash
docker compose exec -T backend python - < sample_data/seed_sales.py
```

---

## 5. Bugs Found & Fixed During Testing

1. **`/reorder` returned 500.** `ProductForecast` required `reorder_level`, but the
   forecast dict didn't include it. Fixed by passing it explicitly in
   `forecasting_service._forecast_for_product`.

2. **Frontend "Analyze" button did nothing.** Docker Desktop on Windows doesn't emit
   filesystem events into the container for bind-mounted files, so Vite never noticed
   the edited pages and kept serving the **old stub** (whose button had no handler).
   Fixed by enabling `server.watch.usePolling` in `frontend/vite.config.ts` and
   restarting the frontend container. Future frontend edits now hot-reload.

---

## 6. How It Was Tested

### Automated — 14 new tests (39 total, all passing)
```bash
cd backend && python -m pytest -q
# 25 (Phases 1–2) + 6 pricing + 8 forecasting = 39 passed
```
- Pricing: handoff example, zero cost, zero-sell (no div-by-zero), negative margin,
  and that the recommended 25% price actually yields 25%.
- Forecasting: daily-series gap filling, feature shapes/values, train/select returns
  valid metrics for all 3 models, non-negative predictions, reorder logic, save/load.

### Manual — Swagger (`http://localhost:8080/docs`)
- Pricing analyze (normal + negative margin) and price history ✅
- Forecast retrain (3 models compared, artifact saved) ✅
- Reorder list + per-product stockout, with Pepsi correctly **not** flagged ✅

### Manual — Frontend (`http://localhost:5173`)
- Pricing Advisor: metric cards (margin color-coded) + AI explanation ✅
- Inventory: reorder cards + products table with status badges ✅

---

## 7. Design Decisions (the "why")

- **Math in Python, not the LLM.** Margins must be exact and deterministic; the LLM
  only writes the human-readable explanation.
- **One global model across products.** The features (lags, rolling mean, day-of-week)
  are product-agnostic, so a single model trained on all products generalises and
  avoids many fragile per-product models.
- **Best-of-three by RMSE.** Training three models and selecting on a time-based
  holdout is honest ML practice and shows the baseline is actually beaten.
- **`/retrain` is synchronous, but a Celery task also exists.** Immediate feedback for
  testing/demo, plus the scheduled weekly retrain via Celery beat.
- **No schema changes.** Only the missing `Sale` ORM mapping was added (same pattern as
  `Order` in Phase 2).

---

## 8. Notes / Known Quirks

- **The `.pkl` is git-ignored** (`ml_models/*.pkl`) — correct practice for binary
  artifacts. The pipeline regenerates it on `POST /retrain` (or the weekly task), and
  it lives at `ml_models/forecast_model.pkl` on disk for inspection.
- **Leftover apparel products** (`hoodie`, `t-shirt`, `cap`, `jacket`) from Phase 2
  order testing have **negative stock** and no sales, so they appear as CRITICAL /
  reorder-recommended. That's honest data; reset their stock if a cleaner demo is wanted.
- **No rebuild needed** — `scikit-learn`, `pandas`, `numpy`, `joblib` were already in
  `requirements.txt`.

---

## 9. Commits (on `main`)

```
fix(frontend): enable Vite polling so edits hot-reload under Docker/Windows
feat(forecast): inventory page with reorder cards + 60-day sales seed
feat(forecast): wire forecasting service, APIs, and retrain worker
feat(forecast): add sales model and scikit-learn forecasting core (Phase 3B)
feat(pricing): add Pricing / Profit Advisor (Phase 3A)
```

---

## 10. Possible Next Steps (not in Phase 3 scope)

- Record real `sales` rows automatically when an order is fulfilled (Phase 2 → sales).
- Add a price-history **chart** on the Pricing page using `GET /pricing/history/{id}`.
- Show forecast columns (days-to-stockout) inline in the full products table.
- Per-product or seasonal models once there's more than 60 days of history.
- Persist each pricing analysis as an `AIInsight` for the dashboard/reports.
