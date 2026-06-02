# SoukPilot AI — Phase 2 Summary

**Feature:** WhatsApp / Instagram Order Extraction
**Status:** ✅ Complete, tested (Swagger + frontend), committed to `main`
**Date:** 2026-06-02

---

## 1. What Phase 2 Does (in plain words)

The shop owner copies a customer's WhatsApp or Instagram message and pastes it
into the app. The system:

1. Reads the messy, mixed-language message (Arabic/English/"Arabizi").
2. Uses AI to pull out a **structured order**: what products, how many, what
   color/size, where to deliver, how they'll pay.
3. **Validates** that structure strictly before saving anything.
4. Saves the order, creates the order line items, and **deducts the stock** from
   inventory — all in one safe database transaction.
5. Shows the owner the clean, structured result and a list of recent orders.

**Example**

Input message:
> "Salam, bddi 3 black hoodies size L w 2 white ones size M, delivery to Hamra, cash on delivery"

Structured output:
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

---

## 2. The End-to-End Flow

```
Owner pastes message  (Frontend: Orders page)
        │
        ▼  POST /api/orders/extract   { message, source }
┌─────────────────────────────────────────────────────────┐
│  API endpoint  (app/api/orders.py)                       │
│        │                                                 │
│        ▼  calls service                                  │
│  Order Service  (app/services/order_service.py)          │
│    1. Guardrails  → block prompt-injection (→ 400)       │
│    2. LLM extract → GPT-4o-mini, JSON mode               │
│    3. Validate    → Pydantic ExtractedOrder (→ 422 bad)  │
│    4. Transaction:                                        │
│         • create order header                            │
│         • if intent == new_order:                        │
│             - create order_items                         │
│             - fuzzy match / create products              │
│             - deduct stock + inventory movements         │
│             - raise low-stock alerts                     │
│        │                                                 │
│        ▼  commit, then build response                    │
└─────────────────────────────────────────────────────────┘
        │
        ▼  201 + structured order (with items)
Frontend shows the extracted order + refreshes Recent Orders
```

This mirrors the Phase 1 invoice pipeline, with one deliberate difference:
**order extraction runs synchronously** inside the API request (no Celery), because
it's a single fast text-LLM call — there's no heavy OCR step like invoices have.

---

## 3. Files Created / Changed

### Backend

| File | What it is | New/Changed |
|------|------------|-------------|
| `backend/app/models/order.py` | SQLAlchemy ORM models `Order` + `OrderItem` mapping the existing tables | **New** |
| `backend/app/models/__init__.py` | Registers the new models on `Base.metadata` | Changed |
| `backend/app/schemas/order.py` | Pydantic validation contracts + API request/response schemas | **New** |
| `backend/app/ai/extraction.py` | Added `parse_order_json()` + `extract_order()` | Changed |
| `backend/app/repositories/order_repo.py` | DB persistence helpers for orders | Changed (was a stub) |
| `backend/app/services/order_service.py` | Orchestration: guardrails → LLM → validate → transaction | Changed (was a stub) |
| `backend/app/api/orders.py` | The 4 real endpoints (were 501 stubs) | Changed |
| `backend/tests/test_order_extraction.py` | 6 unit tests for the parse/validate core | **New** |
| `sample_data/orders/*.txt` | 4 sample messages (2 orders, 1 inquiry, 1 complaint) | **New** |

### Frontend

| File | What it is | New/Changed |
|------|------------|-------------|
| `frontend/src/pages/Orders.tsx` | Full Orders page UI | Changed (was a static stub) |

> **Note:** `frontend/src/services/api.ts` already had `ordersApi` wired in Phase 1,
> so no changes were needed there.

---

## 4. The Pieces Explained

### 4.1 Database models — `app/models/order.py`
The `orders` and `order_items` **tables already existed** (created by the Phase 1
Alembic migration `0001_initial_schema.py`), but there were **no Python ORM
classes** mapping them. Phase 2 adds those classes so the code can read/write the
tables. **This is not a schema change** — the columns map exactly to the migration.

- `Order`: `id, business_id, source, raw_message, extracted_json, delivery_area,
  payment_method, status, created_at`
- `OrderItem`: `id, order_id, product_id, product_name, quantity, color, size, notes`

### 4.2 Validation schemas — `app/schemas/order.py`
These are the **safety contract**. The LLM's output is just text until it passes
these checks; if validation fails, **nothing is written to the database**.

- `ExtractedOrderItem` — `product` (required, non-blank), `quantity` (int > 0),
  `color`/`size` (optional).
- `ExtractedOrder` — `intent` must be one of `new_order | inquiry | complaint |
  other`; `items`; `delivery_area`; `payment_method` (one of `cash_on_delivery |
  bank_transfer | other`, or null); `notes`.
- API schemas — `OrderExtractRequest`, `OrderStatusUpdate`, `OrderItemOut`,
  `OrderListItem`, `OrderDetailOut`.

### 4.3 Extraction core — `app/ai/extraction.py`
Two new functions, following the invoice pattern:
- `parse_order_json(raw)` — pure, deterministic: JSON → validated `ExtractedOrder`.
  No OpenAI/DB imports, so it's trivially unit-testable. **This is the part the
  tests verify.**
- `extract_order(message)` — builds the prompt (`ORDER_EXTRACTION_PROMPT`, already
  in `app/ai/prompts.py`), calls the LLM (`complete_json`), then parses + validates.

### 4.4 Repository — `app/repositories/order_repo.py`
Thin database helpers, no business logic:
`create_order`, `add_item`, `get`, `list_orders`, `get_items`.

### 4.5 Service — `app/services/order_service.py`
The orchestrator (`extract_and_create_order`). The important rules:
- **Guardrails first.** Obvious prompt-injection attempts are blocked before the
  message ever reaches the LLM (raises `GuardrailError` → API returns `400`).
- **Only `new_order` touches inventory.** Inquiries/complaints are still saved
  (for follow-up) but create no items and deduct no stock.
- **Stock out + audit trail.** Each ordered item deducts stock via
  `product_repo.adjust_stock(..., reason="order")`, which also records an
  `inventory_movements` row.
- **Low-stock alerts.** If a product drops to/below its reorder level after the
  order, a `low_stock` alert is created.
- **Product matching reused from Phase 1.** `match_or_create_product` fuzzy-matches
  the extracted product name to an existing product (so "hoodie" twice maps to the
  same product) or creates a new one.

### 4.6 API — `app/api/orders.py`
| Method & Path | Purpose | Success | Errors |
|---|---|---|---|
| `POST /api/orders/extract` | Extract + save an order | `201` + full order | `400` guardrail, `422` invalid LLM output |
| `GET /api/orders/` | List all orders (newest first) | `200` | — |
| `GET /api/orders/{id}` | One order with items + JSON | `200` | `404` |
| `PATCH /api/orders/{id}/status` | Update status | `200` | `404` |

### 4.7 Frontend — `frontend/src/pages/Orders.tsx`
- Paste box + **source** selector (WhatsApp / Instagram / Manual).
- "Extract Order with AI" button (shows "Extracting…" during the call).
- **Extracted Order** card: intent, delivery area, payment, status, an items table,
  and a collapsible "View extracted JSON".
- **Recent Orders** table with an inline **status dropdown** (PATCHes on change).
- Error banner for guardrail/validation failures.
- Styling matches the existing Invoice page for a consistent look.

---

## 5. Bug Found & Fixed During Testing

**Symptom:** `POST /api/orders/extract` returned the correct `extracted_json` but
an **empty top-level `items: []`**, even though the items were saved correctly
(visible via `GET /api/orders/{id}`).

**Cause:** The database session is configured with `autoflush=False`
(`app/core/database.py`). The endpoint built the response (which re-queries the
items) **before** `db.commit()`, so the just-added items hadn't been flushed to the
DB yet and the query returned nothing.

**Fix:** Commit **before** building the response detail in `POST /extract`. The data
was never actually lost — only the immediate response was affected. (One-line
reorder in `app/api/orders.py`.)

---

## 6. How It Was Tested

### Automated (6 tests, all passing — 11 total with Phase 1)
`backend/tests/test_order_extraction.py`:
1. Parses a valid order JSON correctly.
2. Allows null/optional fields (inquiry with no items).
3. Allows null item color/size.
4. **Rejects** a bad `intent`.
5. **Rejects** zero quantity.
6. **Rejects** a blank product name.

Run with:
```bash
cd backend && python -m pytest -q
```

### Manual — Swagger (`http://localhost:8080/docs`)
- `POST /extract` → `201` with structured order ✅
- `GET /` and `GET /{id}` → order persisted with items ✅
- `PATCH /{id}/status` → status updates ✅

### Manual — Frontend (`http://localhost:5173/orders`)
- Paste → extract → structured table + JSON ✅
- Recent Orders list with live status dropdowns ✅

---

## 7. Design Decisions (the "why")

- **Synchronous, not Celery.** Invoices need a background worker because OCR is
  slow. Order extraction is one quick text-LLM call and the frontend expects an
  immediate response, so it runs inline in the request.
- **No schema changes.** The Phase 1 migration already created `orders`/`order_items`;
  Phase 2 only added the missing ORM mappings.
- **Validation before persistence.** The strict Pydantic layer is the guarantee that
  bad/hallucinated AI output never reaches the database.
- **Inventory only on `new_order`.** Logging inquiries/complaints is useful, but they
  must not silently change stock levels.
- **Reused Phase 1 building blocks.** Guardrails, product fuzzy-matching, stock
  adjustment, and alerts are all shared — Phase 2 didn't reinvent them.

---

## 8. Commits (on `main`)

```
test(orders): add extraction tests and sample messages
feat(orders): build Orders page UI
feat(orders): implement order extraction API endpoints
feat(orders): add order extraction pipeline (LLM + repo + service)
feat(orders): add Order ORM models and extraction schemas
```

---

## 9. Possible Next Steps (not in Phase 2 scope)

- Let the owner **edit** the extracted order before confirming (e.g. fix a wrong size).
- Capture **customer name/phone** (currently redacted by guardrails / not stored).
- Show **inventory impact** inline (e.g. "stock now 4 left") on the result card.
- Surface **low-stock alerts** generated by orders on the Dashboard.
- Add a **service-level integration test** (with a fake LLM) to cover the full
  transaction, not just the parse/validate core.
