# SoukPilot AI — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    React Frontend (Vite)                              │
│  Dashboard · Invoices · Orders · Inventory · Pricing                 │
│  Business Q&A · Reports · Voice Copilot · AI Agent Chat              │
│  /superadmin ← standalone portal (own auth, no sidebar)              │
└───────────────────────────┬─────────────────────────────────────────┘
                            │  HTTP / REST · SSE streaming
                            │  Bearer JWT (business_id + role embedded)
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (:8080)                           │
│                                                                       │
│  ── Auth (public) ─────────────────────────────────────────────────  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │
│  │  /auth   │  │ /widget  │  │/webhooks │  │   /api/admin     │    │
│  │ register │  │ own token│  │  Twilio  │  │ superadmin only  │    │
│  │  login   │  │   auth   │  │ sig-val  │  │ get_current_     │    │
│  └──────────┘  └──────────┘  └──────────┘  │  superadmin dep  │    │
│                                              └──────────────────┘    │
│  ── Business routes (JWT required — get_current_user dep) ─────────  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐              │
│  │ invoices │ │  orders  │ │ products │ │  pricing  │              │
│  │    API   │ │    API   │ │    API   │ │    API    │              │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐              │
│  │ forecast │ │  qa/ask  │ │  reports │ │   voice   │              │
│  │    API   │ │ (stream) │ │    API   │ │ transcribe│              │
│  └──────────┘ └──────────┘ └──────────┘ │ /speak    │              │
│  ┌──────────┐ ┌───────────────────────┐  └───────────┘              │
│  │ anomaly  │ │   agent/chat/stream   │  ┌───────────┐              │
│  │   API    │ │  (tool-calling loop)  │  │   drift   │              │
│  └──────────┘ └───────────────────────┘  │    API    │              │
│                                           └───────────┘              │
│                           │                                        │
│  ┌────────────────────────▼─────────────────────────────────────┐ │
│  │                    Services Layer                             │ │
│  │  invoice_service · order_service · pricing_service           │ │
│  │  forecasting_service · rag_service · report_service          │ │
│  │  agent_service · anomaly_service · guardrails_service        │ │
│  └────────────────────────┬─────────────────────────────────────┘ │
│                           │                                        │
│  ┌────────────────────────▼─────────────────────────────────────┐ │
│  │                 AI Module Layer (app/ai/)                     │ │
│  │  llm.py (complete_json · complete_text · stream_text)        │ │
│  │  ocr.py · extraction.py · embeddings.py                      │ │
│  │  rag.py (BM25 + vector + RRF) · forecasting.py               │ │
│  │  vector_store.py · anomaly.py · prompts.py                   │ │
│  └────────────────────────┬─────────────────────────────────────┘ │
│                           │                                        │
│  ┌────────────────────────▼─────────────────────────────────────┐ │
│  │              Repository Layer (app/repositories/)             │ │
│  │  invoice_repo · order_repo · product_repo                    │ │
│  │  sales_repo · report_repo                                    │ │
│  └────────────────────────┬─────────────────────────────────────┘ │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
         ┌─────────────────┼───────────────────────┐
         ▼                 ▼                        ▼
  ┌────────────┐   ┌──────────────┐   ┌──────────────────────┐
  │ PostgreSQL │   │    Redis     │   │      ChromaDB        │
  │ (main DB)  │   │  (task queue)│   │  (vector embeddings) │
  └────────────┘   └──────┬───────┘   └──────────────────────┘
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
| `order_service` | Guardrail check, LLM extraction, confidence scoring, fuzzy product matching, inventory reservation, review queue management |
| `pricing_service` | Python margin calculation, LLM explanation |
| `forecasting_service` | Feature engineering, model load/train, per-product inference, reorder recommendation list |
| `rag_service` | Document summarisation, parent-child chunking, embedding, BM25+vector hybrid retrieval (RRF), grounded answer generation (streaming) |
| `report_service` | Python aggregation (sales, profit, margins), LLM narrative, report persistence, HTML/PDF export |
| `agent_service` | GPT-4o tool-calling loop (up to 8 iterations), 7 read/write tools, streaming SSE output |
| `anomaly_service` | Rolling z-score anomaly detection over daily sales, batch LLM explanation of flagged anomalies |
| `drift_service` | PSI-based distribution shift detection over order features; persists `DriftSignal` rows |
| `admin_service` | Superadmin: list/create/delete tenants, per-tenant usage stats (no business_id scoping) |
| `guardrails_service` | PII redaction, prompt injection detection (called by order, QA, voice, and agent services) |

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
businesses          ← tenant root — one row per registered business
users               ← username, hashed_password, role (owner/staff/superadmin), business_id (nullable for superadmin)
suppliers           ← name, contact, business_id
products            ← name, current_stock, reorder_level, cost_price, selling_price, business_id
invoices            ← file_path, raw_ocr_text, extracted_json, status, business_id
invoice_items       ← per-line: quantity, unit_price, price_change_pct
orders              ← raw_message, extracted_json, delivery_area, payment_method,
                       confidence_score, review_status, business_id
order_items         ← product, quantity, color, size
sales               ← product_id, quantity, total, sale_date, source, business_id
inventory_movements ← delta, reason, reference_id (audit trail, no business_id — scoped via product)
alerts              ← type, message, product_id, is_read, business_id
ai_insights         ← type, reference_id, insight_text, business_id
reports             ← period_start/end, summary_text, data_json, business_id
documents           ← source_type, source_id, content (RAG index), business_id
widget_tokens       ← token (UUID), label, business_id
drift_signals       ← run_at, psi_score, status (stable/warning/alert), feature_stats (JSONB)
```

Every table except `drift_signals` carries `business_id`. All queries in
business routes append `WHERE business_id = :bid` — row-level tenant isolation.

Full DDL is in `backend/alembic/versions/` (migrations 0001–0006).

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

## AI Data Flow — Hybrid RAG Q&A

```
1. POST /api/qa/index  (run once to build the index)
      │  for each invoice / order / product:
      │    build plain-text parent document
      │    chunk_text into 400-char child chunks (stored in ChromaDB)
      │    store full parent document in Postgres (documents table)
      │    embed_texts (text-embedding-3-small)
      │    upsert into ChromaDB with parent_id metadata
      └─► { documents_indexed, chunks_indexed }

2. POST /api/qa/ask/stream { question }   (SSE streaming)
      │  guardrails.is_safe_input(question)
      │  embed question
      │  vector_store.search(question_vector, top_k=15)  ← 3× over-retrieve
      │  bm25_score(candidates, question)                ← keyword scoring
      │  reciprocal_rank_fusion(vector_ranks, bm25_ranks) → top 5
      │  fetch full parent documents from Postgres
      │  RAG_QA_PROMPT → stream_text() → SSE token stream
      └─► SSE: text tokens... then { answer, grounded, sources }
          UI badge: HYBRID · "15 candidates · BM25 reranked · 5 sources"
```

## AI Data Flow — Agentic Assistant

```
POST /api/agent/chat/stream { message, history }   (SSE streaming)
      │  loop (max 8 iterations):
      │    GPT-4o with tools → response
      │    if tool_call:
      │      SSE: { type: "tool_start", tool, args }
      │      dispatch tool (check_stock | get_reorder_alerts | get_sales_summary |
      │                     get_latest_report | list_recent_orders |
      │                     get_price_history | create_order)
      │      SSE: { type: "tool_result", tool, result }
      │    else:
      │      break loop
      │  final answer → stream_text() → SSE token stream
      │  SSE: { type: "done" }
      └─► Frontend renders tool badges + streaming text
```

## AI Data Flow — Sales Anomaly Detection

```
GET /api/anomaly/alerts
      │  for each product with sales history:
      │    build daily_sales series
      │    compute 14-day rolling mean + std (std floor = max(10% of mean, 0.5))
      │    z_score = (value - mean) / std
      │    if |z_score| >= 2.0 AND sale_date within last 7 days:
      │      flag anomaly (spike or drop, deviation %, actual vs expected)
      │  batch all flagged anomalies into ONE LLM call → plain-English explanations
      └─► { anomalies: [{ product, date, direction, deviation_pct, explanation }] }
          Dashboard: "AI Anomaly Alerts" panel (hidden when clean)
```

## AI Data Flow — Voice Copilot

```
1. Browser: MediaRecorder → audio/webm blob
2. POST /api/voice/transcribe  (multipart audio file)
      │  OpenAI Whisper-1 (language auto-detected: AR / FR / EN)
      └─► { transcript }

3. POST /api/agent/chat/stream { message: transcript, history }
      │  full agent tool-calling loop (same as Agentic Assistant above)
      └─► SSE token stream → frontend renders tool badges + streaming text

4. POST /api/voice/speak { text: response_text }
      │  OpenAI TTS-1 / voice: nova
      │  returns audio/mpeg (MP3 bytes)
      └─► Browser Audio element plays response aloud
          Fallback: window.speechSynthesis if TTS endpoint fails
```

---

## Authentication & Multi-Tenant Isolation

### JWT flow

```
POST /api/auth/login  →  { access_token, role, business_id }
                              │
                         stored in browser localStorage
                              │
All subsequent requests:  Authorization: Bearer <token>
                              │
                    get_current_user dependency
                              │
                    decodes JWT → CurrentUser(username, business_id, role)
                              │
                    every service call receives business_id
                    every SQL query: WHERE business_id = :bid
```

### Role separation

| Role | business_id | Accesses |
|---|---|---|
| `owner` | tenant N | All business routes |
| `staff` | tenant N | All business routes |
| `superadmin` | NULL | `/api/admin/*` only |

The two dependency functions (`get_current_user` and `get_current_superadmin`)
are mutually exclusive — a superadmin token is rejected by `get_current_user`
and vice versa. Cross-role access is structurally impossible.

## Security Boundaries

- **All user text** (order messages, QA questions, voice transcripts) passes
  through `guardrails.is_safe_input()` before reaching any LLM.
- **All LLM JSON output** is validated by a Pydantic schema before any DB
  write. If validation fails, the transaction is rolled back.
- **PII redaction** (`redact_pii`) is applied to log entries; raw messages are
  stored in the DB but never forwarded to logs verbatim.
- **Row-level tenant isolation**: every business route filters by `business_id`
  from the JWT. A tenant cannot access another tenant's data even with a valid token.
- **Twilio webhook signature validation**: `X-Twilio-Signature` HMAC-SHA1
  checked against `TWILIO_AUTH_TOKEN` on every inbound WhatsApp webhook.
