# SoukPilot AI — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend (Vite)                  │
│  Dashboard · Invoices · Orders · Inventory · Pricing     │
│  Business Q&A · Reports · Voice Assistant                 │
└────────────────────────┬────────────────────────────────┘
                         │  HTTP / REST
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend (:8080)                  │
│                                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ invoices │ │  orders  │ │ products │ │  pricing  │  │
│  │    API   │ │    API   │ │    API   │ │    API    │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘  │
│  ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐        │        │
│  │ forecast │ │    qa    │ │  reports │        │        │
│  │    API   │ │    API   │ │    API   │        │        │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘        │        │
│       └────────────┴────────────┘───────────────┘        │
│                         │                                 │
│  ┌──────────────────────▼──────────────────────────────┐ │
│  │              Services Layer                          │ │
│  │  invoice_service · order_service · pricing_service  │ │
│  │  forecasting_service · rag_service · report_service │ │
│  └──────────────────────┬──────────────────────────────┘ │
│                         │                                 │
│  ┌──────────────────────▼──────────────────────────────┐ │
│  │              AI Module Layer (app/ai/)               │ │
│  │  llm.py · ocr.py · extraction.py · embeddings.py   │ │
│  │  rag.py · forecasting.py · vector_store.py          │ │
│  └──────────────────────┬──────────────────────────────┘ │
│                         │                                 │
│  ┌──────────────────────▼──────────────────────────────┐ │
│  │            Repository Layer (app/repositories/)      │ │
│  │  invoice_repo · order_repo · product_repo           │ │
│  │  sales_repo · report_repo                           │ │
│  └──────────────────────┬──────────────────────────────┘ │
└─────────────────────────┼───────────────────────────────┘
                          │
         ┌────────────────┼───────────────────────┐
         ▼                ▼                        ▼
  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐
  │ PostgreSQL │  │    Redis     │  │      ChromaDB        │
  │ (main DB)  │  │  (task queue)│  │  (vector embeddings) │
  └────────────┘  └──────┬───────┘  └──────────────────────┘
                         │
                  ┌──────▼──────────────────┐
                  │     Celery Worker        │
                  │  process_invoice task    │
                  │  generate_weekly_report  │
                  │  retrain_forecast_model  │
                  │  index_documents task    │
                  └─────────────────────────┘
                  ┌──────────────────────────┐
                  │     Celery Beat          │
                  │  Weekly report: Mon 08:00│
                  │  Forecast retrain: weekly│
                  └──────────────────────────┘
```

---

## Layering Rules

Every request follows a strict top-to-bottom call chain. No layer ever calls
upward.

```
API endpoint
  └─► Service  (orchestration, business rules)
        └─► Repository  (SQL queries via SQLAlchemy)
              └─► Database  (PostgreSQL)
        └─► AI module  (LLM / OCR / embeddings / ML)
              └─► External APIs  (OpenAI, ChromaDB)
```

**Why this matters:** swapping a repository (e.g. switching to a different ORM)
or an AI provider (e.g. switching from OpenAI to Anthropic) requires changing
exactly one layer, leaving all others untouched.

---

## Service Responsibilities

| Service | Owns |
|---|---|
| `invoice_service` | OCR dispatch, LLM extraction, price comparison, stock update, price-increase alerts |
| `order_service` | Guardrail check, LLM extraction, fuzzy product matching, inventory reservation, low-stock alerts |
| `pricing_service` | Python margin calculation, LLM explanation |
| `forecasting_service` | Feature engineering, model load/train, per-product inference, reorder recommendation list |
| `rag_service` | Document summarisation, chunking, embedding, vector upsert, RAG answer generation |
| `report_service` | Python aggregation (sales, profit, margins), LLM narrative, report persistence |
| `guardrails_service` | PII redaction, prompt injection detection (called by order + QA + voice services) |

---

## Background Workers

Slow operations that would block an HTTP request go to Celery:

| Task | Trigger | What it does |
|---|---|---|
| `process_invoice` | Invoice upload API | OCR → LLM extraction → DB transaction |
| `generate_weekly_report` | Celery beat (Mon 08:00) | Aggregation → LLM narrative → persist |
| `retrain_forecast_model` | Celery beat (weekly) | Feature engineering → train 3 models → save best |
| `index_documents` | Manual via `/api/qa/index` | Chunk → embed → upsert into ChromaDB |

The API returns `202 Accepted` immediately on upload; the frontend polls
`GET /api/invoices/{id}/status` every 1.5 s until the worker marks it
`processed` or `failed`.

---

## Database Schema (key tables)

```
businesses          ← single-tenant default business
products            ← name, current_stock, reorder_level, cost_price, selling_price
suppliers           ← name, contact
invoices            ← file_path, raw_ocr_text, extracted_json, status
invoice_items       ← per-line: quantity, unit_price, price_change_pct
orders              ← raw_message, extracted_json, delivery_area, payment_method
order_items         ← product, quantity, color, size
sales               ← product_id, quantity, total, sale_date, source
inventory_movements ← delta, reason, reference_id (audit trail)
alerts              ← type, message, product_id, is_read
reports             ← period_start/end, summary_text, data_json
documents           ← source_type, source_id, content (RAG index)
```

Full DDL is in `alembic/versions/`.

---

## AI Data Flow — Invoice Processing

```
1. POST /api/invoices/upload
      │  validate MIME + size
      │  save file to disk
      │  create invoice row (status=pending)
      │  enqueue process_invoice.delay(invoice_id)
      └─► 202 { invoice_id, status: "pending" }

2. Celery worker: process_invoice(invoice_id)
      │  OCR: OpenAI Vision API → raw_text
      │  guardrails.detect_injection(raw_text)  ← flag but don't block
      │  extraction.extract_invoice(raw_text)
      │    └─► INVOICE_EXTRACTION_PROMPT → complete_json() → parse_invoice_json()
      │         └─► ExtractedInvoice (Pydantic) — raises if invalid
      │  DB transaction:
      │    update invoice header (supplier, date, total)
      │    for each item:
      │      match/create product
      │      create invoice_item (with price_change_pct vs previous)
      │      adjust_stock (+qty, reason="invoice")
      │      if price_change_pct >= 5%: create Alert
      │    invoice.status = "processed"
      └─► commit

3. Frontend polls GET /api/invoices/{id}/status
      └─► { status: "processed" } → fetch full detail + render table
```

---

## AI Data Flow — RAG Q&A

```
1. POST /api/qa/index  (run once to build the index)
      │  for each invoice / order / product:
      │    build plain-text summary
      │    chunk_text (300-500 tokens, 50 token overlap)
      │    embed_texts (text-embedding-3-small)
      │    upsert into ChromaDB
      └─► { documents_indexed, chunks_indexed }

2. POST /api/qa/ask { question }
      │  guardrails.is_safe_input(question)
      │  embed question
      │  vector_store.search(question_vector, top_k=5)
      │  build context string from retrieved chunks
      │  RAG_QA_PROMPT → complete_text()
      └─► { answer, grounded, sources: [{source_type, source_id, content, score}] }
```

---

## Security Boundaries

- **All user text** (order messages, QA questions, voice transcripts) passes
  through `guardrails.is_safe_input()` before reaching any LLM.
- **All LLM JSON output** is validated by a Pydantic schema before any DB
  write. If validation fails, the transaction is rolled back.
- **PII redaction** (`redact_pii`) is applied to log entries; raw messages are
  stored in the DB but never forwarded to logs verbatim.
- No multi-tenant isolation beyond a simple `business_id` filter (single-owner
  MVP scope).
