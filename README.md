# SoukPilot AI

**AI-first operations copilot for Lebanese SMEs.**

SoukPilot AI turns the messy day-to-day reality of running a small business —
paper supplier invoices, WhatsApp orders, handwritten stock records — into
structured operations and actionable business insights, powered by LLMs, OCR,
RAG, and ML forecasting.

Built as a full-stack capstone project demonstrating production-grade AI
engineering: background workers, database transactions, Pydantic validation,
prompt safety guardrails, and a recruiter-ready UI.

---

## Features

| # | Feature | How it works |
|---|---|---|
| 1 | **Invoice OCR + LLM extraction** | Upload a supplier invoice image/PDF → OpenAI Vision OCR → GPT-4o-mini extracts structured JSON → Pydantic validated → inventory updated |
| 2 | **WhatsApp/Instagram order extraction** | Paste a customer message → LLM NER extraction → fuzzy product matching → order created and stock reserved |
| 3 | **Pricing / Profit Advisor** | Enter cost + selling price → Python computes margin → LLM explains results in plain language |
| 4 | **Inventory Forecasting (ML)** | 60 days of sales history → moving average + linear regression + random forest → best model auto-selected → reorder alerts |
| 5 | **Hybrid RAG Business Q&A** | Ask any question → parent-child chunking + BM25 keyword scoring fused with vector search (RRF) → grounded answer with source records, streamed token by token |
| 6 | **AI Weekly Business Report** | Celery beat runs every Monday → Python aggregates all metrics → LLM writes 4–6 sentence narrative → one-click PDF export |
| 7 | **Voice Copilot (STT → Agent → TTS)** | Speak a question → Whisper transcribes → agent calls live business tools → answer streams back → OpenAI TTS reads the response aloud |
| 8 | **Agentic Tool-Calling Assistant** | Type or speak any business question → GPT-4o tool loop queries live DB (stock, sales, orders, forecasts, reports) → streams answer with expandable tool-call badges |
| 9 | **AI Sales Anomaly Detection** | Rolling z-score (14-day window, 2σ threshold) scans every product daily → unusual spikes/drops surfaced on Dashboard with plain-English LLM explanations |
| 10 | **Guardrails + PII redaction** | Every user input scanned for prompt injection and PII before reaching any LLM |

---

## Quick Start

### Prerequisites
- Docker Desktop
- An OpenAI API key

### 1. Clone and configure

```bash
git clone <repo-url>
cd soukpilot-ai
cp .env.example .env
# Edit .env and set OPENAI_API_KEY
```

### 2. Start all services

```bash
docker compose up
```

This starts: **FastAPI backend** (`:8080`), **React frontend** (`:5173`),
**PostgreSQL**, **Redis**, **Celery worker**, **Celery beat**, and **ChromaDB**.

### 3. Seed demo data

```bash
# Full demo seed (products, 60-day sales, invoices, orders, reports, RAG index, ML retrain)
docker compose exec backend python sample_data/seed_demo.py
```

### 4. Open the app

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API (Swagger) | http://localhost:8080/docs |
| API (ReDoc) | http://localhost:8080/redoc |

---

## Project Structure

```
soukpilot-ai/
├── backend/
│   └── app/
│       ├── ai/            # LLM, OCR, embeddings, RAG, forecasting
│       ├── api/           # FastAPI routers (one file per domain)
│       ├── services/      # Business logic orchestration
│       ├── repositories/  # DB queries (SQLAlchemy)
│       ├── models/        # ORM models
│       ├── schemas/       # Pydantic schemas (request/response + LLM output validation)
│       ├── workers/       # Celery tasks
│       ├── security/      # Guardrails, PII redaction
│       └── core/          # Config, DB session, logging
├── frontend/
│   └── src/
│       ├── pages/         # One page component per feature
│       ├── components/    # Shared UI (PageShell)
│       └── services/      # Axios API wrappers
├── tests/                 # 51 pytest tests (no OpenAI or DB required)
├── sample_data/           # Demo invoices, seed script
└── ml_models/             # Saved scikit-learn model artifacts
```

---

## Running Tests

```bash
cd backend
python -m pytest tests/ -v
# 71 passed — no OpenAI key or live DB required
```

---

## Environment Variables

See `.env.example` for the full list. Required variables:

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o-mini + Whisper + embeddings) |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string (default: `redis://redis:6379/0`) |

---

## Tech Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Celery, Redis, PostgreSQL  
**AI:** OpenAI GPT-4o-mini (chat + tool-calling), Whisper-1 (STT), TTS-1/Nova (TTS), text-embedding-3-small, scikit-learn  
**Vector store:** ChromaDB  
**Retrieval:** BM25 Okapi (custom Python) + vector search fused with Reciprocal Rank Fusion (RRF)  
**Frontend:** React 18, TypeScript, Vite, React Router, Axios, SSE streaming  
**Infrastructure:** Docker Compose

---

## Documentation

| File | What's inside |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System diagram, layering rules, full AI data flows |
| [docs/AI_FEATURES.md](docs/AI_FEATURES.md) | Prompt templates, validation strategy, design decisions per feature |
| [docs/SECURITY.md](docs/SECURITY.md) | Guardrails design, PII redaction, agentic tool-call security |
| [docs/EVALS.md](docs/EVALS.md) | Test cases, evaluation methodology, benchmark results |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Deployment, seeding, retraining, troubleshooting |
| [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) | Step-by-step recruiter demo script |
| [docs/NEW_FEATURES.md](docs/NEW_FEATURES.md) | Post-MVP feature changelog |
| [docs/phases/](docs/phases/) | Build history: implementation plan + phase summaries |
