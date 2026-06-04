# SoukPilot AI — New Features Added (Post Phase 7)

## 7. Full Voice Copilot (STT → Agent → TTS)

**What it does:**
Turns the Voice Assistant page into a genuine voice-first operations copilot. The owner speaks, the AI agent answers using live business data, and responds out loud — no typing required.

**Full flow:**
1. Press mic → MediaRecorder captures audio in WebM
2. Stop → audio blob sent to `POST /api/voice/transcribe` (OpenAI Whisper)
3. Transcript is routed directly into the streaming agent loop (`POST /api/agent/chat/stream`)
4. Tool badges appear live as the agent calls tools (check_stock, get_reorder_alerts, etc.)
5. Final answer streams in token by token
6. `POST /api/voice/speak` converts the response to MP3 using OpenAI TTS (nova voice)
7. Audio plays automatically in the browser — mic is ready for the next question

**Key UX details:**
- Mic button pulses red while recording, pulses indigo while speaking
- Animated dots during transcription / thinking phases
- 🎙 voice badge on user messages so it's clear the input came from audio
- 🔇 Mute toggle: disable TTS while still seeing tool-call details and streamed text
- Browser SpeechSynthesis fallback if TTS endpoint fails
- Multi-turn: conversation history is preserved so follow-up questions work naturally
- Whisper language auto-detection removed (`language="en"` dropped) — handles Arabic, French, and English

**New backend endpoint:** `POST /api/voice/speak` — takes `{"text":"..."}`, returns `audio/mpeg` via OpenAI TTS nova

**Changed files:**
- `backend/app/api/voice.py` — added `/speak` endpoint; removed hardcoded `language="en"` from Whisper
- `frontend/src/services/api.ts` — added `voiceApi.speak`
- `frontend/src/pages/VoiceAssistant.tsx` — complete redesign: recording → Whisper → agent streaming → TTS playback

---

## 1. Advanced RAG — Hybrid Reranking + Parent-Child Chunking

**What it does:**
Upgraded the Business Q&A page from basic vector search to a professional hybrid retrieval pipeline.

**How it works:**
- **Parent-child chunking**: documents are split into small 400-char child chunks for precise vector search, but the full parent document is stored in Postgres and passed to the LLM for richer context
- **BM25 + Vector fusion**: retrieves 3× more candidates than needed (e.g. 15 for top-5), then scores them with BM25 Okapi (keyword frequency × IDF), and combines both ranked lists using Reciprocal Rank Fusion (RRF)
- BM25 is implemented natively (~25 lines of Python) — no external dependency

**What you see in the UI:**
- **HYBRID** badge (indigo) next to the GROUNDED badge
- Stats line: *"15 candidates · BM25 reranked · 5 sources"*

**Key files:** `backend/app/ai/rag.py`, `backend/app/services/rag_service.py`

---

## 2. PDF Report Export

**What it does:**
Adds an "Export PDF" button to the Reports page that generates a print-optimised HTML report and triggers a browser download.

**How it works:**
- Backend generates a self-contained HTML file with inline CSS (no external deps)
- Frontend receives the HTML as text and uses `window.print()` via a hidden iframe
- Works without any PDF library — no fpdf2, no wkhtmltopdf

**Key files:** `backend/app/api/reports.py`, `frontend/src/pages/Reports.tsx`

---

## 3. Agentic Tool-Calling Assistant

**What it does:**
A full agentic loop on the AI Agent page — the model decides which tools to call, executes them against live DB data, reads the results, and loops until it has enough information to answer.

**Tools available:**
| Tool | What it does |
|---|---|
| `check_stock` | List all products + stock levels |
| `get_reorder_alerts` | Products that need reordering + days until stockout |
| `get_sales_summary` | This week vs last week revenue + profit |
| `get_latest_report` | Pull the full weekly report |
| `list_recent_orders` | Recent customer orders with items |
| `get_price_history` | Cost history for a product across invoices |
| `create_order` | Create a new order via natural language |

**Key files:** `backend/app/services/agent_service.py`, `backend/app/api/agent.py`, `frontend/src/pages/AgentChat.tsx`

---

## 4. Streaming LLM Responses (SSE)

**What it does:**
Both the AI Agent and Business Q&A now stream responses token by token, like ChatGPT. No more silent waiting — text builds up in real time.

**How it works:**
- Backend uses FastAPI `StreamingResponse` with Server-Sent Events (SSE)
- Tool-calling rounds stay non-streaming (need full JSON to parse tool calls)
- Final answer is a genuine streaming OpenAI call piped straight to the browser
- Frontend uses `fetch` + `ReadableStream` to parse SSE (EventSource doesn't support POST)

**What you see:**
- **Agent**: tool badges appear with a ⏳ spinner while executing, then the answer streams in word by word with a blinking `▌` cursor
- **Q&A**: source cards appear immediately after retrieval, then the answer streams in

**New endpoints:**
- `POST /api/agent/chat/stream`
- `POST /api/qa/ask/stream`

**Key files:** `backend/app/ai/llm.py` (`stream_text`), `backend/app/services/agent_service.py` (`chat_stream`), `backend/app/services/rag_service.py` (`ask_stream`)

---

## 5. AI Sales Anomaly Detection

**What it does:**
Automatically scans every product's daily sales history for unusual spikes or drops and shows them on the Dashboard with plain-English AI explanations.

**How it works:**
- **Algorithm**: rolling z-score with a 14-day baseline window and 2σ threshold
- Only reports anomalies from the last 7 days (recent = actionable)
- All statistics (mean, std, z-score, % deviation) are pure Python + numpy — the LLM never calculates anything
- All detected anomalies are batched into **one LLM call** for explanations regardless of count
- Std floor of `max(10% of mean, 0.5)` prevents division-by-near-zero on flat baselines

**What you see on the Dashboard:**
- New **"AI Anomaly Alerts"** panel (hidden when no anomalies)
- Each alert shows: ↑/↓ direction, product name, date, deviation %, actual vs expected units, and a one-sentence AI explanation

**New endpoint:** `GET /api/anomaly/alerts`

**Key files:** `backend/app/ai/anomaly.py`, `backend/app/services/anomaly_service.py`, `backend/app/api/anomaly.py`

---

## 6. Phase 8 — Demo Seed + Guide

**`sample_data/seed_demo.py`** — one command that seeds everything needed for a demo:
- 7 products (5 grocery + 2 apparel)
- 419 sales rows over 60 days with weekly seasonality
- 2 invoices from the same supplier — the second has 10.5% / 6.9% / 13.6% price increases to trigger alerts
- 3 orders (WhatsApp + Instagram + manual) with items
- Weekly report (AI-generated)
- Forecasting model retrain
- RAG reindex

**`DEMO_GUIDE.md`** — step-by-step recruiter walkthrough with exact copy-paste inputs for every demo moment.

---

## Test Coverage

| Before | After |
|---|---|
| 51 tests | 71 tests |

New tests added:
- 11 RAG tests (BM25 scoring, RRF reranking, retrieve_reranked interface, parent-child metadata)
- 9 anomaly detection tests (spike/drop detection, lookback filtering, field validation, sort order)
