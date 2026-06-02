# SoukPilot AI — Implementation Plan

> **Mentor-grade 2-week build plan for a job-ready, AI-first capstone project.**
> Based on the SoukPilot AI Final Project Handoff Brief.

---

## Table of Contents

1. [Final Project Scope](#1-final-project-scope)
2. [2-Week Development Roadmap](#2-2-week-development-roadmap)
3. [Recommended Architecture](#3-recommended-architecture)
4. [Feature Breakdown](#4-feature-breakdown)
5. [Database Schema](#5-database-schema)
6. [API Endpoints](#6-api-endpoints)
7. [Folder & Repository Structure](#7-folder--repository-structure)
8. [Demo Script](#8-demo-script)
9. [Tests & Evaluations](#9-tests--evaluations)
10. [Prioritized Task List](#10-prioritized-task-list)

---

## 1. Final Project Scope

### Must Build (MVP — non-negotiable)

| # | Feature | Why It's Non-Negotiable |
|---|---|---|
| 1 | Invoice/receipt OCR + LLM extraction | Flagship AI demo — shows OCR + LLM + structured output |
| 2 | WhatsApp/Instagram order extraction | Shows NLP + NER + business logic |
| 3 | Inventory dashboard | Visible outcome of every AI operation |
| 4 | Pricing/profit advisor | Shows code-calculated logic + AI explanation |
| 5 | RAG business Q&A | Shows embeddings + vector search + grounded generation |
| 6 | AI weekly business report | Shows LLM summarization + scheduled jobs |
| 7 | Inventory forecasting (ML) | Shows ML pipeline end-to-end |
| 8 | Redis + background worker | Shows production backend thinking |
| 9 | Guardrails & PII redaction | Shows safety awareness |
| 10 | Docker Compose deployment | Shows full-stack engineering |
|  11   |Voice assistant (STT/TTS) | High demo wow-factor |
### Optional (Stretch — build only if MVP is solid)

| Feature | Impact |
|---|---|
| Agentic tool-calling assistant | Very impressive but complex |
| DL forecasting (LSTM) | Good if you have time after scikit-learn version |
| Advanced RAG (reranking, parent-child) | Shows depth |
| PDF report export | Good for demo polish |
| Cloud deployment (Railway, Render, AWS) | Optional bonus |

### Avoid (Do Not Build)

- A normal CRUD dashboard with one chatbot bolted on at the end.
- Over-engineering auth (use a simple API key or single-user mode for MVP).
- Building a mobile app.
- Fine-tuning your own LLM.
- Building your own vector DB from scratch.
- Multi-tenant isolation beyond a simple `business_id` filter.

---

## 2. Two-Week Development Roadmap

### Phase 0 — Day 1 (Setup & Foundation)

**Goal: working skeleton before writing any AI code.**

- [ ] Create GitHub repo with the folder structure below.
- [ ] Write `docker-compose.yml` with all services (backend, frontend, postgres, redis, worker).
- [ ] Create FastAPI app with health check endpoint.
- [ ] Create React app with placeholder pages.
- [ ] Run Postgres migrations for core tables.
- [ ] Write `.env.example` and confirm API keys work (OpenAI, etc.).
- [ ] Confirm Docker Compose brings everything up cleanly.

**End of Day 1 deliverable:** `docker-compose up` starts all services, `/health` returns 200, React renders.

---

### Phase 1 — Days 2–3 (Core AI Module 1: Invoice OCR + LLM)

**Goal: first end-to-end AI feature.**

- [ ] Build file upload endpoint (`POST /api/invoices/upload`).
- [ ] Integrate OCR (EasyOCR or Tesseract) to extract raw text from image/PDF.
- [ ] Write LLM extraction prompt — structured JSON output.
- [ ] Validate JSON output with Pydantic schema.
- [ ] Save invoice + items to Postgres in a transaction.
- [ ] Update product/inventory quantities.
- [ ] Compare current prices to previous supplier invoices and flag increases.
- [ ] Push OCR + extraction to Redis background worker (Celery/RQ).
- [ ] Write 3 pytest tests for invoice extraction parsing.

**End of Phase 1 deliverable:** Upload a real invoice image → structured JSON appears in DB, inventory updated.

---

### Phase 2 — Day 4 (Core AI Module 2: Order Extraction)

**Goal: WhatsApp/Instagram order parsing.**

- [ ] Build order extraction endpoint (`POST /api/orders/extract`).
- [ ] Write LLM prompt for NER-style extraction (product, qty, size, color, delivery, payment).
- [ ] Validate extracted JSON with Pydantic.
- [ ] Create order + reserve/deduct inventory in a transaction.
- [ ] Write 3 pytest tests for order extraction.

**End of Phase 2 deliverable:** Paste a WhatsApp message → structured order in DB.

---

### Phase 3 — Days 5–6 (Pricing Advisor + Forecasting)

**Goal: ML pipeline and business calculations.**

- [ ] Build pricing/profit advisor endpoint (`POST /api/pricing/analyze`).
- [ ] Implement margin calculations in Python code (not LLM).
- [ ] Pass calculated results to LLM for business-language explanation.
- [ ] Build sales history seed script (generate 60 days of dummy sales data).
- [ ] Build forecasting pipeline:
  - Data preprocessing + feature engineering (sales velocity, rolling avg).
  - Train moving average + linear regression + random forest.
  - Compare models with RMSE/MAE.
  - Save best model artifact (`joblib`).
- [ ] Build inference endpoint (`GET /api/forecast/reorder`).
- [ ] Add scheduled Celery task to retrain weekly.

**End of Phase 3 deliverable:** Forecasting returns "Nutella may run out in 3 days", pricing advisor gives margin + AI explanation.

---

### Phase 4 — Days 7–8 (RAG Business Q&A)

**Goal: owner can ask natural-language questions about their own data.**

- [ ] Set up Chroma or pgvector for vector storage.
- [ ] Write document indexing pipeline (invoice summaries, orders, sales records → chunks → embeddings).
- [ ] Build retrieval endpoint (`POST /api/qa/ask`).
- [ ] Write RAG prompt (retrieved context + question → grounded answer).
- [ ] Add source documents to response so owner can see where the answer came from.
- [ ] Handle "I don't know" gracefully when no evidence exists.
- [ ] Write 3 RAG faithfulness test cases.

**End of Phase 4 deliverable:** Ask "Which supplier raised prices the most?" → grounded answer with source records.

---

### Phase 5 — Day 9 (Weekly Report + Guardrails)

**Goal: AI report generation and safety layer.**

- [ ] Build weekly report generator service.
- [ ] Aggregate: total sales, profit, top products, supplier price changes, low-stock risks.
- [ ] Pass aggregated data to LLM for narrative summary.
- [ ] Add Celery beat schedule for weekly generation.
- [ ] Build guardrails service:
  - PII redaction (phone numbers, names) using regex + optional LLM check.
  - Prompt injection detection (scan uploads/inputs for instruction injection patterns).
  - LLM output validation before DB write.
- [ ] Write guardrails tests.

**End of Phase 5 deliverable:** One-click weekly report, guardrails block injection attempts.

---

### Phase 6 — Days 10–11 (Frontend Polish + Inventory Dashboard)

**Goal: recruiter-ready UI.**

- [ ] Build inventory dashboard page (table, low-stock badges, reorder alerts).
- [ ] Build invoice upload page with progress indicator and extracted result display.
- [ ] Build orders page (paste box, extracted JSON display, order list).
- [ ] Build RAG Q&A chat page.
- [ ] Build weekly report page.
- [ ] Build pricing advisor page.
- [ ] Connect all pages to backend APIs.
- [ ] Add error states and loading indicators.

---

### Phase 7 — Days 12–13 (Testing, Docs, Stretch)

**Goal: production-credibility polish.**

- [ ] Run full test suite, fix failures.
- [ ] Write `README.md`, `ARCHITECTURE.md`, `AI_FEATURES.md`, `EVALS.md`, `SECURITY.md`, `RUNBOOK.md`.
- [ ] Add API docs via FastAPI's built-in `/docs` (Swagger UI).
- [ ] Add observability logs to all AI operations.
- [ ] If time allows: build voice assistant (STT via Whisper, TTS via OpenAI or browser API).
- [ ] If time allows: build agentic assistant with tool calling.

---

### Phase 8 — Day 14 (Demo Dry Run + Final Prep)

**Goal: demo-ready project.**

- [ ] Seed realistic demo data (sample invoices, orders, sales history).
- [ ] Run full demo script end-to-end.
- [ ] Fix any visual or data bugs found in dry run.
- [ ] Record a short screen recording as backup.
- [ ] Push clean final commit to GitHub.

---

## 3. Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        React Frontend                        │
│  (Dashboard, Invoice Upload, Orders, RAG Chat, Reports)     │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP / REST
┌─────────────────────▼───────────────────────────────────────┐
│                     FastAPI Backend                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ Invoice  │ │  Order   │ │ Pricing  │ │  RAG / Q&A   │   │
│  │   API    │ │   API    │ │   API    │ │     API      │   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘   │
│       │             │            │               │            │
│  ┌────▼─────────────▼────────────▼───────────────▼───────┐  │
│  │              Services + Repositories Layer             │  │
│  └──────────────────────────────┬─────────────────────────┘  │
│                                 │                             │
│  ┌──────────────────────────────▼──────────────┐            │
│  │           AI Module Layer (ai/)              │            │
│  │  OCR → LLM Extraction → Guardrails →        │            │
│  │  Embeddings → RAG → Forecasting → Reports   │            │
│  └──────────────────────────────────────────────┘            │
└────────────────────┬──────────────────────────────────────────┘
                     │
         ┌───────────┼──────────────────┐
         │           │                  │
┌────────▼──┐  ┌─────▼──────┐  ┌───────▼──────┐
│ PostgreSQL │  │   Redis    │  │  Chroma /    │
│  (main DB) │  │  (queue)   │  │  pgvector    │
└────────────┘  └─────┬──────┘  │  (vectors)   │
                      │         └──────────────┘
               ┌──────▼──────┐
               │  Celery     │
               │  Worker     │
               │  (OCR,      │
               │  indexing,  │
               │  reports,   │
               │  forecasting│
               └─────────────┘
```

### Service Responsibilities

| Service | Responsibility |
|---|---|
| `invoice_service` | Upload handling, OCR dispatch, LLM extraction, price comparison |
| `order_service` | Order extraction, product matching, inventory reservation |
| `pricing_service` | Margin calculations, AI explanation |
| `forecasting_service` | Feature engineering, model inference, reorder alerts |
| `rag_service` | Document indexing, embedding, retrieval, grounded generation |
| `report_service` | Weekly aggregation, LLM narrative generation |
| `guardrails_service` | PII redaction, prompt injection detection, output validation |
| `worker_tasks` | Celery tasks for all slow async operations |

---

## 4. Feature Breakdown

### Feature 1: Invoice / Receipt OCR + LLM Extraction

**Flow:**
```
Upload file → Validate MIME type → Push to Redis queue →
Worker: OCR raw text → LLM structured extraction →
Pydantic validation → Transaction: save invoice + items + update inventory →
Price comparison check → Return result to frontend
```

**OCR options (pick one):**
- `EasyOCR` — easiest setup, good for mixed-language invoices (recommended)
- `Tesseract` via `pytesseract` — reliable, needs more preprocessing
- `PaddleOCR` — very accurate, heavier install

**LLM extraction prompt template:**
```
You are a data extraction assistant. Extract the following fields from this invoice text as valid JSON only. Do not add any explanation.

Fields to extract:
- supplier (string)
- date (ISO format string)
- items (array of: name, quantity, unit_price, total)
- invoice_total (float)
- currency (string)

Invoice text:
{ocr_text}

Respond with only valid JSON. If a field cannot be found, use null.
```

**Validation:** Use Pydantic model to validate before any DB write. If validation fails, log and return a structured error — never save invalid data.

**Price comparison:** After saving, query previous invoices from the same supplier, compare unit prices per product, flag increases > 5%.

---

### Feature 2: WhatsApp / Instagram Order Extraction

**Flow:**
```
Paste message → Guardrails check (PII, injection) →
LLM NER extraction → Pydantic validation →
Product matching (fuzzy match against products table) →
Transaction: create order + reserve/deduct inventory →
Return structured order to frontend
```

**LLM extraction prompt template:**
```
You are an order extraction assistant for a Lebanese small business. Extract the following fields from this customer message as valid JSON only.

Fields:
- intent (one of: new_order, inquiry, complaint, other)
- items (array of: product, quantity, color, size — use null if not mentioned)
- delivery_area (string or null)
- payment_method (one of: cash_on_delivery, bank_transfer, other, null)
- notes (string or null)

Customer message:
{message}

Respond with only valid JSON.
```

**Product matching:** Use fuzzy string matching (`rapidfuzz`) to map extracted product names to database products. If no match, flag as unresolved and let the owner manually confirm.

---

### Feature 3: Voice-Based Business Assistant (Stretch)

**Flow:**
```
Owner records audio → Upload audio file →
Whisper STT transcription →
LLM command understanding (intent: record_sale, check_stock, create_order) →
Execute backend action →
TTS response via OpenAI TTS or browser `window.speechSynthesis`
```

**Implementation note:** Treat voice as an alternate input channel. After transcription, the text goes through the same extraction/command flow as typed input. This reuses existing code cleanly.

---

### Feature 4: Inventory Forecasting (ML)

**Flow:**
```
Sales history from DB → Feature engineering →
Train models (moving average, linear regression, random forest) →
Compare with RMSE/MAE → Save best model artifact →
Scheduled inference → Generate reorder alerts → Store in alerts table
```

**Features to engineer per product:**
- `sales_last_7d` — total units sold last 7 days
- `sales_last_30d` — total units sold last 30 days
- `avg_daily_sales` — rolling average
- `days_of_stock_remaining` — current stock / avg daily sales
- `day_of_week` — encoded
- `is_weekend` — binary

**Model comparison:**
```python
models = {
    "moving_average": MovingAverageModel(window=7),
    "linear_regression": LinearRegression(),
    "random_forest": RandomForestRegressor(n_estimators=100),
}
# Evaluate each on test split, save best by RMSE
```

**Inference output:**
```json
{
  "product_id": 12,
  "product_name": "Nutella 400g",
  "current_stock": 8,
  "avg_daily_sales": 3.2,
  "days_until_stockout": 2.5,
  "reorder_recommended": true,
  "reorder_by_date": "2026-06-04"
}
```

---

### Feature 5: Pricing / Profit Advisor

**Implementation rule:** All calculations happen in Python code. The LLM only explains the result in business language.

**Calculation logic:**
```python
def calculate_margin(cost: float, sell: float, delivery: float, packaging: float) -> dict:
    total_cost = cost + delivery + packaging
    profit = sell - total_cost
    margin_pct = (profit / sell) * 100 if sell > 0 else 0
    target_sell_25 = total_cost / (1 - 0.25)
    return {
        "profit": round(profit, 2),
        "margin_pct": round(margin_pct, 1),
        "total_cost": round(total_cost, 2),
        "sell_price_for_25pct_margin": round(target_sell_25, 2),
    }
```

**LLM explanation prompt:**
```
A small business owner calculated the following:
- Cost price: ${cost}
- Selling price: ${sell}
- Delivery cost: ${delivery}
- Packaging cost: ${packaging}
- Profit: ${profit}
- Margin: ${margin_pct}%

Write a 2-3 sentence business explanation of these results and one specific recommendation to improve the margin. Keep the language simple and direct.
```

---

### Feature 6: RAG-Based Business Q&A

**Indexing pipeline (run after each invoice/order/sale is saved):**
```
Document source → Chunk text (300–500 tokens, 50 token overlap) →
Generate embedding (OpenAI text-embedding-3-small or similar) →
Store vector + metadata in Chroma/pgvector
```

**Document types to index:**
- Invoice summaries (supplier, date, items, prices)
- Order records (customer, products, delivery area)
- Weekly reports
- Product sales summaries

**Retrieval + generation flow:**
```
Owner question → Generate question embedding →
Vector similarity search (top 5 chunks) →
Build context from retrieved chunks →
LLM prompt with context → Grounded answer + source references
```

**RAG prompt template:**
```
You are a business assistant for a Lebanese small business. Answer the owner's question using ONLY the business records provided below. If the answer cannot be found in the records, say "I don't have enough data to answer that."

Business records:
{retrieved_context}

Owner's question: {question}

Provide a clear, direct answer. If relevant, mention which records support your answer.
```

---

### Feature 7: AI Weekly Business Report

**Aggregation queries (run in Python, not LLM):**
- Total sales this week vs. last week
- Total profit this week vs. last week
- Top 5 products by revenue
- Supplier price changes this week
- Products with < 7 days of stock remaining
- Most and least profitable products

**LLM narrative prompt:**
```
You are writing a weekly business summary for a Lebanese small business owner. Use the data below to write a clear, 4–6 sentence summary. Highlight wins, risks, and one actionable recommendation.

Data:
{aggregated_json}

Write the summary in simple, direct language.
```

**Scheduled task:** Celery beat trigger every Monday at 8 AM. Store report in `reports` table. Display in frontend reports page.

---

### Feature 8: Guardrails & Redaction

**PII Redaction (apply to all inputs before logging):**
```python
import re

PHONE_PATTERN = re.compile(r"\+?[\d\s\-\(\)]{7,15}")
EMAIL_PATTERN = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")

def redact_pii(text: str) -> str:
    text = PHONE_PATTERN.sub("[PHONE REDACTED]", text)
    text = EMAIL_PATTERN.sub("[EMAIL REDACTED]", text)
    return text
```

**Prompt injection detection:**
```python
INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"forget everything",
    r"you are now",
    r"system prompt",
    r"reveal your instructions",
    r"act as",
]

def detect_injection(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in INJECTION_PATTERNS)
```

**LLM output validation:** Before writing any LLM-extracted JSON to the DB, run it through the Pydantic schema. If validation fails, log the raw output and return an error. Never write unvalidated LLM output to the database.

---

## 5. Database Schema

```sql
-- Core business entities

CREATE TABLE businesses (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE products (
    id              SERIAL PRIMARY KEY,
    business_id     INTEGER REFERENCES businesses(id),
    name            VARCHAR(255) NOT NULL,
    sku             VARCHAR(100),
    current_stock   FLOAT DEFAULT 0,
    reorder_level   FLOAT DEFAULT 10,
    unit            VARCHAR(50),          -- e.g. "piece", "kg", "bottle"
    cost_price      NUMERIC(10,2),
    selling_price   NUMERIC(10,2),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE suppliers (
    id          SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    name        VARCHAR(255) NOT NULL,
    contact     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Invoice processing

CREATE TABLE invoices (
    id              SERIAL PRIMARY KEY,
    business_id     INTEGER REFERENCES businesses(id),
    supplier_id     INTEGER REFERENCES suppliers(id),
    invoice_date    DATE,
    invoice_total   NUMERIC(12,2),
    currency        VARCHAR(10) DEFAULT 'USD',
    raw_ocr_text    TEXT,
    extracted_json  JSONB,
    status          VARCHAR(50) DEFAULT 'pending',  -- pending, processed, failed
    file_path       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE invoice_items (
    id              SERIAL PRIMARY KEY,
    invoice_id      INTEGER REFERENCES invoices(id),
    product_id      INTEGER REFERENCES products(id),
    product_name    VARCHAR(255),         -- raw extracted name before matching
    quantity        FLOAT,
    unit_price      NUMERIC(10,4),
    total           NUMERIC(12,2),
    price_change_pct FLOAT               -- vs. previous invoice from same supplier
);

-- Order management

CREATE TABLE orders (
    id              SERIAL PRIMARY KEY,
    business_id     INTEGER REFERENCES businesses(id),
    source          VARCHAR(50),         -- whatsapp, instagram, manual
    raw_message     TEXT,
    extracted_json  JSONB,
    delivery_area   VARCHAR(255),
    payment_method  VARCHAR(100),
    status          VARCHAR(50) DEFAULT 'pending',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER REFERENCES orders(id),
    product_id  INTEGER REFERENCES products(id),
    product_name VARCHAR(255),
    quantity    FLOAT,
    color       VARCHAR(100),
    size        VARCHAR(50),
    notes       TEXT
);

-- Sales tracking

CREATE TABLE sales (
    id          SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    product_id  INTEGER REFERENCES products(id),
    quantity    FLOAT,
    unit_price  NUMERIC(10,4),
    total       NUMERIC(12,2),
    sale_date   DATE DEFAULT CURRENT_DATE,
    source      VARCHAR(50),             -- order, manual, voice
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Inventory movements audit trail

CREATE TABLE inventory_movements (
    id          SERIAL PRIMARY KEY,
    product_id  INTEGER REFERENCES products(id),
    delta       FLOAT,                   -- positive = stock in, negative = stock out
    reason      VARCHAR(100),            -- invoice, order, sale, manual_adjustment
    reference_id INTEGER,               -- invoice_id or order_id
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- AI outputs and reports

CREATE TABLE alerts (
    id          SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    type        VARCHAR(100),            -- low_stock, price_increase, reorder
    message     TEXT,
    product_id  INTEGER REFERENCES products(id),
    is_read     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ai_insights (
    id          SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    type        VARCHAR(100),            -- pricing, forecast, order, invoice
    reference_id INTEGER,
    insight_text TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE reports (
    id          SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    period_start DATE,
    period_end   DATE,
    report_type  VARCHAR(50) DEFAULT 'weekly',
    summary_text TEXT,
    data_json    JSONB,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- RAG / document indexing

CREATE TABLE documents (
    id          SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    source_type VARCHAR(100),            -- invoice, order, report, manual
    source_id   INTEGER,
    content     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- pgvector extension for embeddings (or use separate Chroma)
-- CREATE EXTENSION IF NOT EXISTS vector;
-- ALTER TABLE documents ADD COLUMN embedding vector(1536);
```

---

## 6. API Endpoints

### Invoices
```
POST   /api/invoices/upload              Upload invoice image/PDF
GET    /api/invoices/                    List invoices
GET    /api/invoices/{id}                Get invoice detail + items
GET    /api/invoices/{id}/status         Poll processing status (background job)
```

### Orders
```
POST   /api/orders/extract               Extract order from pasted message
GET    /api/orders/                      List orders
PATCH  /api/orders/{id}/status           Update order status
```

### Products & Inventory
```
GET    /api/products/                    List products with current stock
GET    /api/products/{id}                Product detail
PATCH  /api/products/{id}/stock          Manual stock adjustment
GET    /api/inventory/alerts             Low-stock and reorder alerts
```

### Pricing
```
POST   /api/pricing/analyze              Calculate margin + AI explanation
GET    /api/pricing/history/{product_id} Price history for a product
```

### Forecasting
```
GET    /api/forecast/reorder             Products recommended for reorder
GET    /api/forecast/stockout/{id}       Predicted stockout date for one product
POST   /api/forecast/retrain             Trigger model retraining (admin)
```

### RAG / Q&A
```
POST   /api/qa/ask                       Ask a business question
POST   /api/qa/index                     Re-index documents (background task)
```

### Reports
```
GET    /api/reports/                     List generated reports
GET    /api/reports/latest               Latest weekly report
POST   /api/reports/generate             Trigger report generation now
```

### Voice (Stretch)
```
POST   /api/voice/transcribe             Upload audio → transcription
POST   /api/voice/command                Process transcribed command
```

### Health
```
GET    /health                           Service health check
GET    /api/docs                         FastAPI Swagger UI (auto-generated)
```

---

## 7. Folder & Repository Structure

```
soukpilot-ai/
│
├── README.md
├── IMPLEMENTATION_PLAN.md
├── ARCHITECTURE.md
├── AI_FEATURES.md
├── EVALS.md
├── SECURITY.md
├── RUNBOOK.md
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                        # DB migrations
│   │   └── versions/
│   └── app/
│       ├── main.py                     # FastAPI app init, router registration
│       ├── core/
│       │   ├── config.py               # Settings (pydantic BaseSettings)
│       │   ├── database.py             # SQLAlchemy engine + session
│       │   └── logging.py              # Structured logging setup
│       ├── api/
│       │   ├── invoices.py
│       │   ├── orders.py
│       │   ├── products.py
│       │   ├── pricing.py
│       │   ├── forecast.py
│       │   ├── qa.py
│       │   ├── reports.py
│       │   └── voice.py
│       ├── services/
│       │   ├── invoice_service.py
│       │   ├── order_service.py
│       │   ├── pricing_service.py
│       │   ├── forecasting_service.py
│       │   ├── rag_service.py
│       │   ├── report_service.py
│       │   └── guardrails_service.py
│       ├── repositories/
│       │   ├── invoice_repo.py
│       │   ├── order_repo.py
│       │   ├── product_repo.py
│       │   └── sales_repo.py
│       ├── models/                     # SQLAlchemy ORM models
│       │   ├── invoice.py
│       │   ├── order.py
│       │   ├── product.py
│       │   ├── sales.py
│       │   └── report.py
│       ├── schemas/                    # Pydantic schemas (request/response + LLM output validation)
│       │   ├── invoice.py
│       │   ├── order.py
│       │   ├── pricing.py
│       │   └── forecast.py
│       ├── ai/
│       │   ├── ocr.py                  # OCR integration (EasyOCR/Tesseract)
│       │   ├── llm.py                  # OpenAI client wrapper
│       │   ├── extraction.py           # Invoice + order LLM extraction
│       │   ├── embeddings.py           # Embedding generation
│       │   ├── rag.py                  # Retrieval + generation
│       │   ├── forecasting.py          # ML model training + inference
│       │   └── prompts.py              # All prompt templates in one place
│       ├── workers/
│       │   ├── celery_app.py           # Celery app init
│       │   ├── invoice_tasks.py        # OCR + extraction tasks
│       │   ├── indexing_tasks.py       # Document embedding + indexing
│       │   ├── report_tasks.py         # Weekly report generation
│       │   └── forecast_tasks.py       # Periodic model retraining
│       └── security/
│           └── guardrails.py           # PII redaction, injection detection
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── InvoiceUpload.tsx
│       │   ├── Orders.tsx
│       │   ├── Inventory.tsx
│       │   ├── PricingAdvisor.tsx
│       │   ├── BusinessQA.tsx
│       │   ├── Reports.tsx
│       │   └── Settings.tsx
│       ├── components/
│       │   ├── InvoiceResult.tsx
│       │   ├── OrderExtraction.tsx
│       │   ├── StockAlertBadge.tsx
│       │   ├── ForecastCard.tsx
│       │   ├── ReportDisplay.tsx
│       │   └── ChatInterface.tsx
│       ├── services/
│       │   └── api.ts                  # Axios/fetch wrappers per endpoint group
│       └── hooks/
│           └── usePolling.ts           # For polling background job status
│
├── ml_models/                          # Saved model artifacts
│   └── .gitkeep
│
├── sample_data/
│   ├── invoices/                       # Sample invoice images for demo
│   ├── orders/                         # Sample WhatsApp messages
│   └── seed_sales.py                   # Script to generate 60 days of dummy sales
│
└── tests/
    ├── test_invoice_extraction.py
    ├── test_order_extraction.py
    ├── test_pricing.py
    ├── test_forecasting.py
    ├── test_rag.py
    ├── test_guardrails.py
    └── test_api_endpoints.py
```

---

## 8. Demo Script

> Use this script for your recruiter presentation. Each step should flow naturally and tell a business story.

---

### Step 1: Set the Scene (30 seconds)

**Say:**
> "Lebanese small businesses still manage most operations manually — paper invoices, WhatsApp orders, handwritten stock records. SoukPilot AI is a copilot that turns that messy input into structured operations and business insights."

**Show:** The inventory dashboard with realistic demo data loaded.

---

### Step 2: Upload a Supplier Invoice (2 minutes)

**Action:** Upload a real-looking invoice image.

**Narrate:**
> "The owner receives a paper invoice from their supplier. Instead of manually entering it, they just upload it."

**Show:**
- File upload UI with progress indicator.
- OCR extraction step visible (raw text box).
- LLM structured JSON output appearing.
- "Pepsi 330ml increased 8% vs. last invoice" price alert.
- Inventory quantities automatically updated in the dashboard.

**What this demonstrates:** OCR, LLM, structured output, validation, transaction, background worker, price comparison.

---

### Step 3: Extract a WhatsApp Order (1.5 minutes)

**Action:** Paste a realistic WhatsApp message.

**Message to paste:**
> "Salam, I want 3 black hoodies size L and 2 white ones size M, delivery to Hamra, cash on delivery"

**Show:**
- Raw message in input box.
- Extracted JSON: product, quantity, color, size, delivery area, payment method.
- Order created and visible in the orders table.
- Inventory reserved.

**What this demonstrates:** NLP, NER-style extraction, product matching, order management.

---

### Step 4: Ask the Business Assistant a Question (1.5 minutes)

**Action:** Type a question in the RAG Q&A interface.

**Question:** "Which products should I reorder this week and why?"

**Show:**
- Typing the question.
- System showing "retrieving relevant records…"
- Answer appearing: specific product names, reasoning, numbers.
- Source records shown below the answer.

**What this demonstrates:** Embeddings, vector search, RAG, grounded generation, source transparency.

---

### Step 5: Show Inventory Forecasting (1 minute)

**Show:**
- Forecasting dashboard with products ranked by stockout risk.
- "Nutella 400g — estimated stockout in 2.5 days. Reorder by Thursday."
- Highlight: "this prediction is from our ML model trained on 60 days of sales history."

**What this demonstrates:** ML pipeline, feature engineering, trained model artifact, inference endpoint.

---

### Step 6: Generate the Weekly Report (1 minute)

**Action:** Click "Generate Report."

**Show:**
- Loading state.
- Report appearing: sales up/down vs. last week, profit summary, top products, supplier price flags, reorder risks, AI recommendation.

**Narrate:**
> "Every Monday this runs automatically. The numbers are calculated in code, then the AI writes the explanation."

**What this demonstrates:** Aggregation queries, scheduled jobs, LLM summarization.

---

### Step 7: Show Engineering Depth (1.5 minutes)

**Show:**
- `docker-compose up` output — all 5+ services starting cleanly.
- FastAPI `/docs` — full Swagger UI with all endpoints.
- One test file running in the terminal with passing tests.
- Log output from a background worker processing an invoice.
- Guardrail block: paste a prompt injection into the order box, show it being caught.

**Narrate:**
> "This isn't just a demo app — it has a real service layer, background workers, database transactions, guardrails, and tests."

---

### Closing (30 seconds)

**Say:**
> "SoukPilot AI demonstrates the full stack: LLMs, OCR, embeddings, RAG, ML forecasting, background workers, database design, and production safety. Every major workflow starts with AI input and ends with a structured business outcome."

---

## 9. Tests & Evaluations

### Unit Tests

| Test File | What It Tests |
|---|---|
| `test_invoice_extraction.py` | LLM output parses correctly into Pydantic schema; handles missing fields gracefully |
| `test_order_extraction.py` | NER extraction from 5 different WhatsApp message styles |
| `test_pricing.py` | Margin calculations correct for edge cases (zero cost, zero price, negative margin) |
| `test_forecasting.py` | Feature engineering produces expected columns; model returns valid prediction |
| `test_guardrails.py` | PII redacted from phone/email; injection patterns caught; clean inputs pass through |

### Integration Tests

| Test | What It Tests |
|---|---|
| `test_api_endpoints.py` | `POST /api/invoices/upload` returns 202; `POST /api/orders/extract` returns order JSON |
| Invoice → inventory transaction | After invoice save, product stock is correctly updated |
| Order → stock reservation | After order create, stock decreases correctly |

### AI Evaluation Tests (EVALS.md)

**Invoice extraction evals:** 5 sample invoices with known ground-truth JSON. Measure field extraction accuracy.

**Order extraction evals:** 10 sample WhatsApp messages with known outputs. Check intent, product, quantity accuracy.

**RAG faithfulness evals:** 5 questions with known answers in the business data. Verify answer contains the correct fact. Verify "I don't know" fires when data is absent.

**Guardrails evals:** 5 injection attempts should all be blocked. 5 normal inputs should all pass through unblocked.

**Forecasting eval:** On held-out test data, log RMSE and MAE. Compare to naive baseline (last week's sales as prediction).

---

## 10. Prioritized Task List

### Tier 1 — Must Complete First (Days 1–5)

1. Docker Compose setup (all services running)
2. Postgres schema + Alembic migrations
3. FastAPI skeleton with health endpoint
4. Invoice upload endpoint + OCR integration
5. LLM invoice extraction with Pydantic validation
6. Save invoice + update inventory (transaction)
7. WhatsApp order extraction endpoint
8. Inventory dashboard (read-only, shows products + stock)
9. Redis + Celery worker connected to invoice processing
10. Basic guardrails (PII redaction, injection detection)

### Tier 2 — Core AI Features (Days 6–9)

11. Sales seed data script (60 days)
12. Forecasting pipeline (feature engineering + 3 models + inference endpoint)
13. Reorder alerts stored and shown on dashboard
14. Pricing/profit advisor (calculation + AI explanation)
15. RAG indexing pipeline (chunk → embed → store)
16. RAG retrieval + generation endpoint
17. Weekly report generation + scheduling
18. Report display page in frontend

### Tier 3 — Engineering Polish (Days 10–11)

19. Connect all frontend pages to live API
20. Error states and loading indicators in React
21. Structured logging in all AI services
22. API documentation verified in Swagger UI
23. Full test suite passing

### Tier 4 — Docs, Stretch, Demo Prep (Days 12–14)

24. Write README, ARCHITECTURE, AI_FEATURES, EVALS, SECURITY, RUNBOOK
25. Voice assistant (STT/TTS) — if time allows
26. Agentic tool-calling assistant — if time allows
27. Seed demo data and run demo dry run
28. Final GitHub push with clean commit history

---

## Key Principles (Do Not Forget)

1. **Every major feature must start with AI input.** Upload, paste, speak, or ask — then the system responds.
2. **Calculations happen in code. AI explains results.** Never trust an LLM to do arithmetic.
3. **Validate every LLM output with Pydantic before writing to the database.** No exceptions.
4. **Slow tasks go to the background worker.** OCR, indexing, reports, forecasting — all async via Redis/Celery.
5. **Make the demo tell a business story.** The recruiter should understand why this matters in 30 seconds.
6. **Show the engineering layer.** Docker, tests, logs, API docs — these are what separate a school project from a job-ready portfolio piece.

---

*Plan prepared for: SoukPilot AI — AI-First Operations Copilot for Lebanese SMEs*
*Build duration: 2 weeks*
*Target: Bootcamp capstone with maximum recruiter impact*
