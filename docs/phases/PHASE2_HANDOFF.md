# SoukPilot AI — Phase 2 Session Handoff

## What This Project Is
SoukPilot AI is an AI-first operations copilot for Lebanese SMEs.
Full spec is in `IMPLEMENTATION_PLAN.md`. This file is a briefing for starting Phase 2.

GitHub repo: https://github.com/mohammadayoubb/sme-operations-copilot-ai.git

---

## Stack
- **Backend:** FastAPI + SQLAlchemy + Alembic (Python 3.11)
- **DB:** PostgreSQL (via Docker, db=`soukpilot_db`, user=`soukpilot`)
- **Queue:** Redis + Celery workers
- **AI:** OpenAI GPT-4o-mini (JSON mode + Vision API)
- **Frontend:** React + TypeScript + Vite (react-router-dom, axios)
- **Deployment:** Docker Compose (`docker compose up`)

---

## Current State — Phase 1 Complete ✅

Phase 1 (Invoice OCR + LLM extraction) is fully working and committed.

**What was built:**
- `backend/app/ai/ocr.py` — GPT-4o-mini Vision API reads invoice images
- `backend/app/ai/llm.py` — OpenAI JSON-mode wrapper (`complete_json`, `complete_text`)
- `backend/app/ai/extraction.py` — `parse_invoice_json()` + `extract_invoice()`
- `backend/app/ai/prompts.py` — all prompt templates (ORDER_EXTRACTION_PROMPT already written here)
- `backend/app/schemas/invoice.py` — Pydantic validation schemas
- `backend/app/repositories/product_repo.py` — fuzzy match-or-create, stock adjustment
- `backend/app/repositories/invoice_repo.py` — invoice persistence
- `backend/app/services/invoice_service.py` — full orchestration in one DB transaction
- `backend/app/workers/invoice_tasks.py` — Celery task with commit/rollback
- `backend/app/api/invoices.py` — upload (202), status, list, detail endpoints
- `backend/app/security/guardrails.py` — PII redaction + injection detection
- `frontend/src/pages/InvoiceUpload.tsx` — upload UI with polling
- `frontend/src/services/api.ts` — all API methods pre-wired (ordersApi already there)
- `frontend/src/components/PageShell.tsx` — shared page wrapper component
- `backend/tests/test_invoice_extraction.py` — 5 passing tests

**14 DB tables created** via Alembic migration (`0001_initial_schema.py`).
Relevant tables for Phase 2: `orders`, `order_items`, `products`, `inventory_movements`, `alerts`.

---

## Key Patterns Established in Phase 1 (follow these in Phase 2)

1. **LLM calls** go through `app/ai/llm.py` → `complete_json()` for structured output
2. **All prompts** live in `app/ai/prompts.py` — `ORDER_EXTRACTION_PROMPT` is already written there
3. **Pydantic validation** happens BEFORE any DB write — if it fails, nothing is saved
4. **Services** orchestrate everything in one DB transaction
5. **Repositories** handle raw DB queries — services call repositories, APIs call services
6. **Guardrails** (`app/security/guardrails.py`) are called on all user inputs before LLM
7. **API routers** are stub files already in `backend/app/api/` — `orders.py` exists but returns 501

---

## Phase 2 Goal — WhatsApp / Instagram Order Extraction

**What to build:**
The owner pastes a WhatsApp/Instagram customer message. The system extracts structured order data using LLM + NER, validates it with Pydantic, creates an order, and deducts inventory — all in one transaction.

**Example input:**
> "Salam, bddi 3 black hoodies size L w 2 white ones size M, delivery to Hamra, cash on delivery"

**Example output:**
```json
{
  "intent": "new_order",
  "items": [
    {"product": "hoodie", "quantity": 3, "color": "black", "size": "L"},
    {"product": "hoodie", "quantity": 2, "color": "white", "size": "M"}
  ],
  "delivery_area": "Hamra",
  "payment_method": "cash_on_delivery",
  "notes": null
}
```

**Checklist:**
- [ ] `app/schemas/order.py` — ExtractedOrder + ExtractedOrderItem Pydantic schemas
- [ ] `app/repositories/order_repo.py` — create order, list, get, get_items
- [ ] `app/services/order_service.py` — guardrails → LLM extract → validate → transaction (create order + order_items + deduct inventory + movements)
- [ ] `app/api/orders.py` — POST /api/orders/extract, GET /api/orders/, PATCH /api/orders/{id}/status
- [ ] `frontend/src/pages/Orders.tsx` — paste box, extracted JSON display, orders list
- [ ] `backend/tests/test_order_extraction.py` — 3+ pytest tests (valid, null fields, bad intent)
- [ ] Sample WhatsApp messages in `sample_data/orders/`

---

## Important Files to Read Before Starting
- `backend/app/ai/prompts.py` — ORDER_EXTRACTION_PROMPT is already there, use it
- `backend/app/schemas/invoice.py` — follow same pattern for order schemas
- `backend/app/services/invoice_service.py` — follow same transaction pattern
- `backend/app/api/orders.py` — already exists as a stub, just fill it in
- `frontend/src/services/api.ts` — ordersApi methods already wired up

---

## Docker / Running
```bash
docker compose up          # starts all services
# backend on :8080, frontend on :5173
# Swagger UI: http://localhost:8080/docs
```
No rebuild needed unless requirements.txt changes.

---

## Do NOT
- Change the DB schema (tables are already created and migrated)
- Add new packages without updating requirements.txt AND rebuilding
- Run LLM arithmetic — calculations in Python code, LLM only explains
- Write to DB without Pydantic validation first
