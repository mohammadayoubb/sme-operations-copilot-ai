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
| 5 | **RAG Business Q&A** | Ask any question → OpenAI embeddings + Chroma vector search → grounded answer with source records |
| 6 | **AI Weekly Business Report** | Celery beat runs every Monday → Python aggregates all metrics → LLM writes 4–6 sentence narrative |
| 7 | **Voice Assistant** | Record or upload audio → Whisper STT → LLM command intent parsing → structured response |
| 8 | **Guardrails + PII redaction** | Every user input scanned for prompt injection and PII before reaching any LLM |

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
docker compose exec backend python sample_data/seed_sales.py
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
# 51 passed — no OpenAI key or live DB required
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
**AI:** OpenAI GPT-4o-mini, Whisper-1, text-embedding-3-small, scikit-learn  
**Vector store:** ChromaDB  
**Frontend:** React 18, TypeScript, Vite, React Router, Axios  
**Infrastructure:** Docker Compose

---

## Architecture Overview

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system diagram and data
flow descriptions.

## AI Features Deep Dive

See [AI_FEATURES.md](AI_FEATURES.md) for prompt templates, validation
strategies, and design decisions for each AI feature.

## Security

See [SECURITY.md](SECURITY.md) for the guardrails design and PII redaction
approach.

## Evaluations

See [EVALS.md](EVALS.md) for test cases and evaluation methodology.

## Operations

See [RUNBOOK.md](RUNBOOK.md) for deployment, seeding, retraining, and
troubleshooting.
