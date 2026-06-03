# SoukPilot AI — Runbook

Operational guide for starting, stopping, seeding, maintaining, and
troubleshooting SoukPilot AI.

---

## Prerequisites

- Docker Desktop (with Compose v2)
- OpenAI API key with GPT-4o-mini, Whisper-1, and text-embedding-3-small access

---

## Starting the Stack

```bash
# First time — copy and fill in .env
cp .env.example .env
# Set OPENAI_API_KEY in .env

# Start all services (add --build on first run)
docker compose up --build

# Start in background
docker compose up -d

# View logs
docker compose logs -f backend
docker compose logs -f worker
```

### Run database migrations (first run only)
```bash
docker compose exec backend alembic upgrade head
```
This creates all 14 tables.

Services and their default ports:

| Service | Port | Purpose |
|---|---|---|
| `frontend` | 5173 | React UI |
| `backend` | 8080 | FastAPI (also serves `/docs`) |
| `postgres` | 5432 | PostgreSQL |
| `redis` | 6379 | Celery broker/result backend |
| `worker` | — | Celery worker (processes tasks) |
| `beat` | — | Celery beat scheduler (weekly report, retrain) |
| `chromadb` | 8000 | Vector store for RAG |

### Verify everything is up
- API health: http://localhost:8080/health → `{"status":"ok","database":"connected"}`
- API docs (Swagger): http://localhost:8080/docs
- Frontend: http://localhost:5173

---

## Stopping the Stack

```bash
docker compose down          # stop containers, keep volumes
docker compose down -v       # stop containers AND delete all data (full reset)
```

---

## Seeding Demo Data

The seed script generates 60 days of realistic sales history for 10 products
and creates the default business, products, and suppliers.

```bash
docker compose exec backend python sample_data/seed_sales.py
```

After seeding:
- Navigate to **Inventory** — shows 10 products with realistic stock levels
- Navigate to **Reports** → click **Generate Report Now** — the weekly report
  will have real numbers
- Navigate to **Dashboard** — stat cards populate

---

## Rebuilding the RAG Index

After adding new invoices or orders, rebuild the vector index:

```bash
# Via the UI: Business Q&A → click "↻ Reindex data"

# Via curl
curl -X POST http://localhost:8080/api/qa/index
```

The index is rebuilt from scratch on each call — stale chunks are removed.

---

## Retraining the Forecast Model

The model retrains automatically every week via Celery beat. To trigger
manually:

```bash
# Via curl
curl -X POST http://localhost:8080/api/forecast/retrain
```

The best model (by RMSE) is saved to `ml_models/best_model.joblib`. If no
artifact exists, the first call to `/api/forecast/reorder` trains one
automatically.

---

## Generating a Weekly Report

Reports run automatically every Monday at 08:00 Asia/Beirut. To generate on
demand:

```bash
# Via the UI: Reports page → "Generate Report Now"

# Via curl
curl -X POST http://localhost:8080/api/reports/generate
```

---

## Running the Test Suite

```bash
# Inside the running backend container
docker compose exec backend python -m pytest tests/ -v

# On the host (requires Python 3.12 + pip install -r backend/requirements.txt)
cd backend && python -m pytest tests/ -v
```

Expected: **51 tests passing**. No OpenAI key or database connection needed.

---

## Rebuilding Images

Only needed after changing `backend/requirements.txt` or `frontend/package.json`:

```bash
docker compose build backend worker beat
docker compose up -d
```

---

## Clearing Stale Bytecode

If a Python change doesn't take effect inside the container:

```bash
docker compose exec backend find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
docker compose restart backend worker
```

---

## Environment Variables Reference

| Variable | Default | Required | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | — | ✅ | OpenAI API key |
| `DATABASE_URL` | — | ✅ | PostgreSQL DSN |
| `REDIS_URL` | `redis://redis:6379/0` | | Celery broker URL |
| `OPENAI_LLM_MODEL` | `gpt-4o-mini` | | Model for extraction + narration |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | | Model for RAG embeddings |
| `CHROMA_HOST` | `chromadb` | | ChromaDB hostname |
| `CHROMA_PORT` | `8000` | | ChromaDB port |
| `UPLOAD_DIR` | `/app/uploads` | | Where invoice files are stored |
| `MAX_UPLOAD_SIZE_MB` | `20` | | Max invoice upload size |
| `APP_ENV` | `development` | | `development` or `production` |
| `ALLOWED_ORIGINS` | `http://localhost:5173,...` | | Comma-separated CORS origins |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `database: unreachable` on `/health` | Postgres still starting — wait 10 s and retry |
| Invoice stuck in `pending` | Check `docker compose logs worker` — worker may be down |
| Invoice marked `failed` | Bad `OPENAI_API_KEY` or OCR returned no text — check worker logs |
| "Forecasting model not available" | No sales history — run the seed script or `POST /api/forecast/retrain` |
| RAG returns "I don't have enough data" | Index not built — call `POST /api/qa/index` |
| ChromaDB connection refused | ChromaDB still starting — wait 15 s and retry |
| "Potential prompt injection detected" on a legitimate message | A phrase matched the injection pattern — review and adjust `guardrails.py` conservatively |
| Frontend shows "Failed to load dashboard data" | Backend not reachable — check `docker compose ps` and `curl http://localhost:8080/health` |
| Weekly report not running on schedule | Check `docker compose logs beat`; manually trigger `POST /api/reports/generate` |
| Migrations not applied | Run `docker compose exec backend alembic upgrade head` |

---

## Full Reset

```bash
# Stop everything and wipe all data (DB + Redis + ChromaDB volumes)
docker compose down -v

# Restart fresh
docker compose up --build

# Apply migrations
docker compose exec backend alembic upgrade head

# Re-seed
docker compose exec backend python sample_data/seed_sales.py
```
