# SoukPilot AI — AI Features

This document describes every AI-powered feature: what it does, the exact
prompt template, validation strategy, and key design decisions.

---

## Core Rule (applies to every feature)

> **Calculations happen in Python. The LLM only explains results.**

The LLM is never asked to do arithmetic. Every number in the system — margins,
profit, sales aggregations, forecast days-to-stockout — is computed
deterministically in Python and validated before the LLM ever sees it.

---

## Feature 1 — Invoice OCR + LLM Extraction

**File:** `backend/app/ai/ocr.py`, `backend/app/ai/extraction.py`

### Flow
```
image/PDF → OpenAI Vision (GPT-4o-mini) → raw text
         → INVOICE_EXTRACTION_PROMPT → complete_json()
         → ExtractedInvoice (Pydantic) — validates before DB write
         → invoice header + items + stock update (single transaction)
```

### Why Vision API instead of local OCR
EasyOCR and Tesseract require PyTorch (~1 GB) and GPU support. GPT-4o-mini's
Vision API achieves comparable accuracy on mixed-language Lebanese invoices
(Arabic product names, English/French labels, USD/LBP amounts) in a single API
call with zero local dependencies.

### Extraction Prompt
```
You are a data extraction assistant. Extract the following fields from this
invoice text as valid JSON only. Do not add any explanation.

Fields to extract:
- supplier (string)
- date (ISO format string, e.g. "2026-05-27")
- items (array of objects, each with: name, quantity, unit_price, total)
- invoice_total (float)
- currency (string, e.g. "USD" or "LBP")

Invoice text:
{ocr_text}

Respond with only valid JSON. If a field cannot be found, use null.
```

### Validation
`ExtractedInvoice` (Pydantic) enforces:
- `items` must have at least one entry (`min_length=1`)
- Each item: `quantity > 0`, `unit_price >= 0`, `name` not blank
- If validation fails → `ValidationError` is raised → Celery task catches it,
  marks invoice `failed`, rolls back. Nothing is written to the DB.

### Price comparison
After saving, each item's `unit_price` is compared to the previous invoice from
the same supplier. If the increase exceeds 5%, an `Alert` row is created and
shown on the Dashboard.

---

## Feature 2 — WhatsApp / Instagram Order Extraction

**File:** `backend/app/ai/extraction.py`, `backend/app/services/order_service.py`

### Flow
```
customer message → guardrails.is_safe_input()
                → ORDER_EXTRACTION_PROMPT → complete_json()
                → ExtractedOrder (Pydantic)
                → order header + items + stock deduction (single transaction)
```

### Extraction Prompt
```
You are an order extraction assistant for a Lebanese small business.
Extract the following fields from this customer message as valid JSON only.

Fields:
- intent (one of: new_order, inquiry, complaint, other)
- items (array of objects, each with: product, quantity, color, size
         — use null if not mentioned)
- delivery_area (string or null)
- payment_method (one of: cash_on_delivery, bank_transfer, other, null)
- notes (string or null)

Customer message:
{message}

Respond with only valid JSON.
```

### Validation
`ExtractedOrder` (Pydantic) validates `intent` against the allowed enum. Items
are validated for positive `quantity`. Invalid LLM output raises
`ValidationError` and the order is not saved.

### Product matching
Extracted product names (e.g. "hoodie black L") are fuzzy-matched against
`products.name` using `rapidfuzz.process.extractOne` with an 80% similarity
threshold. Below threshold → a new placeholder product is created for the owner
to resolve manually.

### Inventory rule
Only `intent = new_order` deducts stock. Inquiries and complaints are logged
but never touch inventory.

---

## Feature 3 — Pricing / Profit Advisor

**File:** `backend/app/services/pricing_service.py`

### Flow
```
{ cost, sell, delivery, packaging }
  → calculate_margin()  ← pure Python, no LLM
  → PRICING_EXPLANATION_PROMPT → complete_text()
  → { total_cost, profit, margin_pct, sell_for_25pct, explanation }
```

### Margin Calculation (Python — no LLM)
```python
total_cost    = cost + delivery + packaging
profit        = sell - total_cost
margin_pct    = (profit / sell) * 100  if sell > 0  else 0
sell_for_25pct = total_cost / (1 - 0.25)  if total_cost > 0  else 0
```

### Explanation Prompt
```
A small business owner has the following product financials:
- Cost price: ${cost}
- Selling price: ${sell}
- Delivery cost: ${delivery}
- Packaging cost: ${packaging}
- Calculated profit: ${profit}
- Profit margin: {margin_pct}%

Write 2-3 sentences explaining these results in simple business language.
End with one specific, actionable recommendation to improve the margin.
```

The LLM receives the already-computed numbers and only writes the explanation.

---

## Feature 4 — Inventory Forecasting (ML)

**File:** `backend/app/ai/forecasting.py`, `backend/app/services/forecasting_service.py`

### Flow
```
60 days sales history → daily_series()
  → feature engineering (avg_daily_sales, days_of_stock_remaining, …)
  → train 3 models: MovingAverage(7), LinearRegression, RandomForestRegressor
  → evaluate each with RMSE on a held-out 20% split
  → save best model artifact (joblib)
  → forecast_product(): days_until_stockout = current_stock / avg_daily_sales
  → reorder_recommended = True if days_until_stockout <= reorder_lead_time
```

### Features engineered per product
- `sales_last_7d` — total units sold in the past 7 days
- `sales_last_30d` — total units sold in the past 30 days
- `avg_daily_sales` — rolling mean over available history
- `days_of_stock_remaining` — current stock ÷ avg daily sales
- `day_of_week` — encoded (0–6)
- `is_weekend` — binary flag

### Model selection
The model with the lowest RMSE on the test split is saved as the active
artifact. On first request, if no artifact exists, the service trains one
on-the-fly from whatever sales history is available.

### No LLM involved
Forecasting is entirely deterministic ML. The LLM is not used in this feature.
The report service reuses the forecast output to populate the "Reorder Risks"
section of the weekly report.

---

## Feature 5 — Hybrid RAG Business Q&A

**File:** `backend/app/ai/rag.py`, `backend/app/ai/embeddings.py`,
`backend/app/ai/vector_store.py`, `backend/app/services/rag_service.py`

### Indexing flow (parent-child chunking)
```
invoices + orders + products
  → plain-text parent document (stored in Postgres documents table)
  → chunk_text into 400-char child chunks with metadata: {parent_id, chunk_index}
  → text-embedding-3-small (1536-dim vectors)
  → ChromaDB upsert (child chunks only, parent_id in metadata)
```

Child chunks are small for precise vector matching; the full parent document is
fetched from Postgres and passed to the LLM for richer context.

### Hybrid retrieval flow (BM25 + Vector + RRF)
```
question → guardrails.is_safe_input()
         → embed question (text-embedding-3-small)
         → ChromaDB.query(top_k=15)   ← 3× over-retrieve
         → bm25_score(candidates, question tokens)
               tf  = term_freq / doc_len
               idf = log((N - df + 0.5) / (df + 0.5))
               BM25 score = Σ idf × tf × (k1+1) / (tf + k1×(1-b+b×dl/avgdl))
         → reciprocal_rank_fusion(vector_ranks, bm25_ranks, k=60) → top 5
         → fetch full parent documents from Postgres for each top-5 chunk
         → RAG_QA_PROMPT → stream_text() → SSE token stream
         → { answer, grounded, sources }
```

BM25 is implemented in ~25 lines of native Python (no external library).
Both ranked lists are fused with RRF: `score = Σ 1/(k + rank_i)`.

### RAG Prompt
```
You are a business assistant for a Lebanese small business owner. Answer the
owner's question using ONLY the business records provided below.
If the answer cannot be found in the records, say exactly:
"I don't have enough data to answer that."

Business records:
{context}

Owner's question: {question}

Provide a clear, direct answer. Mention which records support your answer
when relevant.
```

### Groundedness and UI
`grounded = True` when the answer does not contain the fallback phrase. Source
records (with similarity scores) are returned alongside the answer so the owner
can verify. The UI shows two badges: **GROUNDED** and **HYBRID**, plus a stats
line: *"15 candidates · BM25 reranked · 5 sources"*. The answer streams in
token by token via SSE.

---

## Feature 6 — AI Weekly Business Report

**File:** `backend/app/services/report_service.py`,
`backend/app/workers/report_tasks.py`

### Aggregation (Python — no LLM)
```python
this_week  = sales with sale_date in [today-6, today]
last_week  = sales with sale_date in [today-13, today-7]

revenue    = sum(sale.total)
profit     = sum(sale.total - product.cost_price * sale.quantity)
change_pct = (this - last) / last * 100  # None if last == 0
```

Also aggregates: top 5 products by revenue, supplier price changes, low-stock
risks (from forecasting), most/least profitable products by margin.

### Narrative Prompt
```
You are writing a weekly business summary for a Lebanese small business owner.
Use the structured data below to write a clear 4-6 sentence summary.
Highlight wins, risks, and end with one actionable recommendation.

Data:
{data_json}

Write in simple, direct language.
```

The LLM receives the pre-computed JSON blob and only writes the narrative.

### Schedule
Celery beat fires `generate_weekly_report` every Monday at 08:00 Asia/Beirut.
The owner can also trigger it on-demand from the Reports page.

---

## Feature 7 — Voice Copilot (STT → Agent → TTS)

**Files:** `backend/app/api/voice.py`, `backend/app/services/agent_service.py`,
`frontend/src/pages/VoiceAssistant.tsx`

### Full pipeline
```
1. Browser MediaRecorder → audio/webm blob
2. POST /api/voice/transcribe
      OpenAI Whisper-1 (language auto-detected: AR / FR / EN)
      → { transcript }
3. POST /api/agent/chat/stream { message: transcript, history }
      Full tool-calling agent loop (see Feature 9)
      → SSE stream: tool_start · tool_result · text · done
4. POST /api/voice/speak { text: final_response }
      OpenAI TTS-1, voice: "nova"
      → audio/mpeg (MP3 bytes)
      Browser Audio element plays response aloud
      Fallback: window.speechSynthesis if TTS endpoint fails
```

### Endpoints
| Endpoint | Purpose |
|---|---|
| `POST /api/voice/transcribe` | Audio upload → Whisper transcript |
| `POST /api/voice/command` | Transcript → intent classification (legacy, kept for reference) |
| `POST /api/voice/speak` | Text → OpenAI TTS MP3 audio |

### Language support
`language` parameter removed from Whisper call — auto-detection handles Arabic,
French, and English naturally, matching Lebanese SME multilingual usage.

### TTS constraints
Input text is capped at 600 characters before sending to TTS (trimmed at the
last word boundary) to keep audio responses concise. The full text is always
displayed in the chat UI regardless of the TTS cap.

### UI states
| State | Visual |
|---|---|
| `idle` | Mic button, static |
| `recording` | Red pulsing ring animation |
| `transcribing` | Animated dot spinner |
| `thinking` | Animated dot spinner + tool badges streaming |
| `speaking` | Indigo pulsing ring animation |

A **Mute** toggle disables TTS playback while keeping the streamed text and
tool-call badges fully visible. Conversation history is preserved across turns
so follow-up voice questions work naturally.

---

## Feature 9 — Agentic Tool-Calling Assistant

**Files:** `backend/app/services/agent_service.py`, `backend/app/api/agent.py`,
`frontend/src/pages/AgentChat.tsx`

### Design
A GPT-4o tool-calling loop that queries live business data and synthesises
answers. The agent decides which tools to call, executes them against the
database, reads results, and loops until it has enough information.

**Invariant:** All calculations stay in Python. The agent never computes
numbers — it only reads pre-computed data and writes explanations.

### Tool catalogue
| Tool | DB operation | Returns |
|---|---|---|
| `check_stock` | SELECT products | All products with current stock vs reorder level |
| `get_reorder_alerts` | Joins products + forecasting | Products needing reorder + days until stockout |
| `get_sales_summary` | Aggregates sales (this week vs last) | Revenue, profit, % change |
| `get_latest_report` | SELECT reports ORDER BY created_at DESC | Full weekly report text + data |
| `list_recent_orders` | SELECT orders + items | Last N orders with line items |
| `get_price_history` | SELECT invoice_items (fuzzy product match) | Unit-price history across invoices |
| `create_order` | Calls order_service (full guardrail + extraction) | Created order JSON |

`create_order` is the only write tool. It routes through the existing
`order_service` pipeline — guardrail check, LLM extraction, Pydantic validation,
DB transaction — so all safety guarantees apply.

### Streaming (SSE)
`POST /api/agent/chat/stream` emits Server-Sent Events:

| Event type | Payload | When |
|---|---|---|
| `tool_start` | `{ tool, args }` | Tool call begins |
| `tool_result` | `{ tool, result }` | Tool returns |
| `text` | `{ text }` | Each streaming token of the final answer |
| `done` | — | Stream complete |
| `error` | `{ error }` | Unrecoverable failure |

Tool rounds are non-streaming (need full JSON to parse tool calls). Only the
final answer uses `stream_text()`. The frontend renders tool badges with a ⏳
spinner while pending, then switches to the tool icon with expandable JSON.

### Safety limits
- Max 8 tool-calling iterations before the agent is forced to answer with
  available data (prevents runaway loops)
- System prompt scoped to read business data — model cannot call arbitrary code

---

## Feature 10 — AI Sales Anomaly Detection

**Files:** `backend/app/ai/anomaly.py`, `backend/app/services/anomaly_service.py`,
`backend/app/api/anomaly.py`

### Algorithm (deterministic Python — no LLM for detection)
```python
# For each product with at least 7 days of sales history:
baseline = daily_sales.rolling(window=14).mean()
std      = daily_sales.rolling(window=14).std()
std      = max(std, 0.1 * mean, 0.5)   # floor prevents near-zero division
z_score  = (actual - baseline) / std

# Flag if: |z_score| >= 2.0 AND date within last 7 days
direction = "spike" if z_score > 0 else "drop"
deviation_pct = (actual - baseline) / baseline * 100
```

The 2σ threshold means roughly 5% of normal days would be flagged by chance
(balanced for actionability vs. noise).

### LLM role (explanation only)
All detected anomalies are collected and passed to the LLM in **one batch
call**, regardless of how many anomalies were found. The LLM writes a
one-sentence plain-English explanation for each:

```
A Lebanese small business had the following unusual sales days.
For each anomaly, write ONE sentence explaining what likely happened.
Anomalies: {anomalies_json}
Return JSON: [{"product": ..., "date": ..., "explanation": ...}]
```

This follows the core rule: statistics in Python, explanations in the LLM.

### UI
A new **"AI Anomaly Alerts"** panel appears on the Dashboard when anomalies
exist. Each card shows: ↑/↓ direction, product name, date, deviation %, actual
vs expected units, and the AI explanation. The panel is hidden entirely when no
anomalies are detected.

**Endpoint:** `GET /api/anomaly/alerts`

---

## Feature 8 — Guardrails

**File:** `backend/app/security/guardrails.py`

### PII Redaction
Applied to all log entries. Phone numbers and email addresses are replaced with
`[PHONE REDACTED]` and `[EMAIL REDACTED]` before any text is written to logs.

```python
PHONE_RE = re.compile(r"\+?[\d\s\-\(\)]{7,15}")
EMAIL_RE = re.compile(r"[\w\.\-]+@[\w\.\-]+\.\w+")
```

### Prompt Injection Detection
Every user-supplied string (order messages, QA questions, voice transcripts)
is checked against a pattern list before reaching any LLM:

```python
INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all instructions",
    r"forget everything",
    r"you are now",
    r"new persona",
    r"system prompt",
    r"reveal your instructions",
    r"disregard.*instructions",
    r"act as (?!a business)",
    r"jailbreak",
]
```

A match returns `(False, "Potential prompt injection detected.")`, which the
service layer converts to an HTTP 400 response. The request never reaches the
LLM.

### LLM Output Validation
Every `complete_json()` response is parsed and validated by a Pydantic schema
before any DB write. Invalid LLM output raises `ValidationError`, which rolls
back the transaction and returns a structured error to the caller.
