# SoukPilot AI

**AI-first operations copilot for Lebanese SMEs.**

SoukPilot AI turns the messy day-to-day reality of running a small business —
paper supplier invoices, WhatsApp orders, handwritten stock records — into
structured operations and actionable business insights, powered by LLMs, OCR,
RAG, and ML forecasting.

Built as a full-stack capstone project demonstrating production-grade AI
engineering: background workers, database transactions, Pydantic validation,
prompt safety guardrails, JWT multi-tenancy, and a recruiter-ready UI.

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
| 11 | **Full Multi-Tenant Architecture** | JWT embeds `business_id`; every SQL query scoped to it — complete data isolation between registered businesses |
| 12 | **2-Tier Super-Admin System** | Standalone `/superadmin` portal — create/delete tenants, view per-tenant usage stats, role separation enforced at the dependency level |
| 13 | **Order Review Queue** | Confidence score < 0.6 → order held for human review; approve or reject from a dedicated queue UI |
| 14 | **WhatsApp Webhook (Twilio)** | Inbound WhatsApp messages processed automatically via Twilio webhook with HMAC-SHA1 signature validation |
| 15 | **ML Drift Monitor (PSI)** | Sales distribution (last 7 days) vs. 60-day rolling baseline → PSI computed with adaptive binning; Dashboard panel with one-click "Run Check" → `stable` / `warning` / `alert`; signals when the ML forecasting model may need retraining |
| 16 | **CI Eval Gate (GitHub Actions)** | Every push runs the full pytest suite + `tests/eval_gate.py`; enforces 100% guardrail coverage, 100% extraction accuracy, 100% drift-eval pass, and ≥95% overall — blocks merges on any regression |

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
# Edit .env — set OPENAI_API_KEY and SECRET_KEY (generate with: openssl rand -hex 32)
```

### 2. Start all services

```bash
docker compose up
```

This starts: **FastAPI backend** (`:8080`), **React frontend** (`:5173`),
**PostgreSQL**, **Redis**, **Celery worker**, **Celery beat**, and **ChromaDB**.

### 3. Run migrations

```bash
docker compose exec backend alembic upgrade head
```

Creates all 17 tables and seeds the superadmin account (`superadmin` / `superadmin2024`).

### 4. Register your first business

Open **http://localhost:5173/register** and create a business account.
Or seed a demo tenant:

```bash
docker compose exec backend python sample_data/seed_demo.py
```

### 5. Open the app

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Super-Admin Portal | http://localhost:5173/superadmin |
| API (Swagger) | http://localhost:8080/docs |
| API (ReDoc) | http://localhost:8080/redoc |

---

## Project Structure

```
soukpilot-ai/
├── backend/
│   └── app/
│       ├── ai/            # LLM, OCR, embeddings, RAG, forecasting, drift, confidence
│       ├── api/           # FastAPI routers (one file per domain, + admin.py + webhooks.py)
│       ├── services/      # Business logic (+ admin_service, drift_service)
│       ├── repositories/  # DB queries (SQLAlchemy, all scoped by business_id)
│       ├── models/        # ORM models (+ users, businesses, drift_signals)
│       ├── schemas/       # Pydantic schemas (request/response + LLM output validation)
│       ├── workers/       # Celery tasks
│       ├── security/      # Guardrails, PII redaction
│       └── core/          # Config, DB session, JWT (security.py), deps.py
│   └── alembic/versions/  # Migrations 0001–0006
├── frontend/
│   └── src/
│       ├── pages/         # One page per feature (+ SuperAdmin.tsx)
│       ├── components/    # Shared UI (PageShell)
│       └── services/      # Axios API wrappers (+ adminApi, adminHttp)
├── tests/                 # 71 pytest tests (no OpenAI or DB required)
├── sample_data/           # Demo invoices, seed script
└── ml_models/             # Saved scikit-learn model artifacts
```

---

## Running Tests

```bash
cd backend
python -m pytest tests/ -v
# no OpenAI key or live DB required
```

### CI Eval Gate

Every push to any branch triggers `.github/workflows/ci.yml`, which runs pytest and then `tests/eval_gate.py` against the JUnit XML report. The gate enforces hard thresholds:

| Group | Threshold |
|---|---|
| Guardrail coverage | 100% |
| Invoice extraction accuracy | 100% |
| Forecasting eval | 100% |
| Drift monitoring eval | 100% |
| Overall pass rate | ≥ 95% |

A non-zero exit code from `eval_gate.py` fails the workflow and blocks the merge.

---

## Environment Variables

See `.env.example` for the full list. Required variables:

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o-mini + Whisper + embeddings) |
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing key — generate with `openssl rand -hex 32` |
| `REDIS_URL` | Redis connection string (default: `redis://redis:6379/0`) |
| `TWILIO_AUTH_TOKEN` | Required for WhatsApp webhook signature validation (optional if not using Twilio) |

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
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System diagram, layering rules, full AI data flows, JWT + multitenancy |
| [docs/AI_FEATURES.md](docs/AI_FEATURES.md) | Prompt templates, validation strategy, design decisions per feature |
| [docs/SECURITY.md](docs/SECURITY.md) | JWT auth, tenant isolation, 2-tier roles, guardrails, Twilio validation |
| [docs/EVALS.md](docs/EVALS.md) | Test cases, evaluation methodology, benchmark results |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Env vars, migrations, superadmin, deployment guide (Railway/Render/Fly), troubleshooting |
| [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) | Step-by-step demo script including superadmin and multitenancy steps |
| [docs/NEW_FEATURES.md](docs/NEW_FEATURES.md) | Post-MVP feature changelog (confidence scoring, order review queue) |
| [docs/NEW_FEATURES_2.md](docs/NEW_FEATURES_2.md) | Webhooks + drift detection changelog |
| [docs/NEW_FEATURES_3.md](docs/NEW_FEATURES_3.md) | Multi-tenancy + super-admin + drift detection (full detail) |
| [.github/workflows/ci.yml](.github/workflows/ci.yml) | GitHub Actions CI Eval Gate — pytest + accuracy thresholds |
| [docs/phases/](docs/phases/) | Build history: implementation plan + phase summaries |

---

## Deployment

SoukPilot can be deployed to any platform that supports Docker. The fastest
path for a presentation:

- **Railway**: push to GitHub → connect repo → set env vars → `alembic upgrade head`
- **Render**: web service (backend) + background worker + static site (frontend)
- **Fly.io**: `fly launch` with Fly Postgres + Fly Redis

See [docs/RUNBOOK.md](docs/RUNBOOK.md) for a full deployment checklist including
TLS, secret rotation, and the default superadmin password change.
