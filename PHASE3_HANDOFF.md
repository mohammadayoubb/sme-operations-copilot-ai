# SoukPilot AI — Phase 3 Session Handoff

## What This Project Is
SoukPilot AI is an AI-first operations copilot for Lebanese SMEs.
GitHub: https://github.com/mohammadayoubb/sme-operations-copilot-ai.git

---

## Stack
- **Backend:** FastAPI + SQLAlchemy + Alembic (Python 3.11)
- **DB:** PostgreSQL (db=`soukpilot_db`, user=`soukpilot`, password=`soukpilot_secret`)
- **Queue:** Redis + Celery workers
- **AI:** OpenAI GPT-4o-mini (JSON mode + Vision API) via `app/ai/llm.py`
- **Frontend:** React + TypeScript + Vite (react-router-dom, axios)
- **Deployment:** Docker Compose — `docker compose up` (backend :8080, frontend :5173)

---

## Current State — Phases 1 & 2 Complete ✅

### Phase 1 — Invoice OCR + LLM Extraction ✅
- Upload invoice image → GPT-4o-mini Vision reads it → LLM extracts JSON → Pydantic validates → DB transaction (invoice + items + inventory update + price comparison alerts)
- Key files: `app/ai/ocr.py`, `app/ai/extraction.py`, `app/services/invoice_service.py`, `app/api/invoices.py`

### Phase 2 — WhatsApp Order Extraction ✅
- Paste customer message → LLM NER extraction → Pydantic validates → DB transaction (order + order_items + inventory deduction)
- Key files: `app/schemas/order.py`, `app/services/order_service.py`, `app/repositories/order_repo.py`, `app/api/orders.py`
- ORM models: `app/models/order.py` (Order, OrderItem) — already in `models/__init__.py`

---

## Established Patterns — Follow These in Phase 3

1. **All LLM calls** → `app/ai/llm.py` → `complete_json()` for structured output, `complete_text()` for explanations
2. **All prompts** → `app/ai/prompts.py` — `PRICING_EXPLANATION_PROMPT` is already written there
3. **Pydantic validation BEFORE any DB write** — if it fails, nothing is saved
4. **Calculations in Python code, LLM only explains results** — never ask the LLM to do arithmetic
5. **Services** orchestrate everything; **repositories** do raw DB queries; **APIs** call services
6. **Guardrails** (`app/security/guardrails.py`) on all user inputs — `redact_pii()` + `detect_injection()`
7. **API stubs** already exist in `app/api/pricing.py` and `app/api/forecast.py` — fill them in

---

## Phase 3 Goal — Pricing Advisor + Inventory Forecasting

Two features in one phase:

---

### Feature A: Pricing / Profit Advisor

Owner inputs cost price, selling price, delivery cost, packaging cost.
System calculates margin in Python, then LLM explains it in business language.

**Example:**
- Input: cost=$7, sell=$10, delivery=$1, packaging=$0.50
- Python calculates: profit=$1.50, margin=15%, sell_for_25pct=$11.33
- LLM explains: "Your margin is low because delivery and packaging reduce profit. To reach 25%, sell at $11.33."

**Checklist:**
- [ ] `app/schemas/pricing.py` — PricingRequest (cost, sell, delivery, packaging), PricingResponse (profit, margin_pct, total_cost, sell_for_25pct, explanation)
- [ ] `app/services/pricing_service.py` — `calculate_margin()` in pure Python + `explain_pricing()` calls LLM with PRICING_EXPLANATION_PROMPT
- [ ] `app/api/pricing.py` — fill in `POST /api/pricing/analyze` (stub exists), `GET /api/pricing/history/{product_id}`
- [ ] `frontend/src/pages/PricingAdvisor.tsx` — input form, calculated results display, AI explanation box
- [ ] Tests: `backend/tests/test_pricing.py` — test margin calculations for edge cases (zero cost, zero sell, negative margin)

**Key rule:** `pricing_service.py` already exists as a stub. The math must be in Python, not LLM.
`PRICING_EXPLANATION_PROMPT` is already in `app/ai/prompts.py` — use it directly.

---

### Feature B: Inventory Forecasting (ML)

Train scikit-learn models on sales history to predict which products will run out soon.

**Example output:**
```json
{
  "product_name": "Nutella 400g",
  "current_stock": 8,
  "avg_daily_sales": 3.2,
  "days_until_stockout": 2.5,
  "reorder_recommended": true,
  "reorder_by_date": "2026-06-05"
}
```

**ML Pipeline:**
1. Seed 60 days of realistic sales history (`sample_data/seed_sales.py`)
2. Feature engineering: avg_daily_sales, sales_last_7d, sales_last_30d, days_of_stock_remaining
3. Train 3 models: moving average, linear regression, random forest
4. Compare with RMSE/MAE, save best model with `joblib` to `/app/ml_models/`
5. Inference endpoint returns reorder recommendations

**Checklist:**
- [ ] `sample_data/seed_sales.py` — generate 60 days of sales data for existing products (Pepsi, Lays, Water, Nutella from Phase 1)
- [ ] `app/ai/forecasting.py` — feature engineering, train/compare models, save artifact, inference
- [ ] `app/services/forecasting_service.py` — fill in stub: load model, run inference, return reorder list
- [ ] `app/repositories/sales_repo.py` — fill in stub: get sales history by product, date range
- [ ] `app/api/forecast.py` — fill in `GET /api/forecast/reorder`, `GET /api/forecast/stockout/{product_id}`, `POST /api/forecast/retrain`
- [ ] `app/workers/forecast_tasks.py` — fill in `retrain_forecasting_model` Celery task (stub exists)
- [ ] `frontend/src/pages/Inventory.tsx` — products table + reorder alert cards
- [ ] Tests: `backend/tests/test_forecasting.py` — test feature engineering output, model returns valid prediction

---

## Important Files to Read Before Starting

- `backend/app/ai/prompts.py` — PRICING_EXPLANATION_PROMPT already written, use it
- `backend/app/services/pricing_service.py` — stub exists, fill it in
- `backend/app/services/forecasting_service.py` — stub exists, fill it in
- `backend/app/api/pricing.py` — stub exists, fill it in
- `backend/app/api/forecast.py` — stub exists, fill it in
- `backend/app/workers/forecast_tasks.py` — stub exists, fill it in
- `backend/app/repositories/sales_repo.py` — stub exists, fill it in
- `backend/app/ai/llm.py` — use `complete_text()` for the pricing explanation
- `backend/app/services/invoice_service.py` — reference for transaction pattern

---

## DB Tables Available (already migrated, do not change schema)

For pricing: `products` (has cost_price, selling_price), `invoice_items` (has unit_price history)
For forecasting: `sales` (product_id, quantity, sale_date), `products` (current_stock, reorder_level)

The `sales` table schema:
```sql
sales(id, business_id, product_id, quantity, unit_price, total, sale_date, source, created_at)
```

---

## Docker / Running
```bash
docker compose up          # all services up, no rebuild needed
# Swagger UI: http://localhost:8080/docs
# Frontend:   http://localhost:5173
```

Only rebuild if `requirements.txt` changes:
```bash
docker compose build backend worker beat && docker compose up -d backend worker beat
```

New packages needed for Phase 3: `scikit-learn`, `pandas`, `numpy`, `joblib` — **already in requirements.txt**, no rebuild needed.

---

## Do NOT
- Ask the LLM to calculate profit margins or percentages — Python only
- Change the DB schema (all tables already exist and are migrated)
- Skip Pydantic validation before DB writes
- Forget to save the trained model artifact with joblib (recruiters need to see the .pkl file)
