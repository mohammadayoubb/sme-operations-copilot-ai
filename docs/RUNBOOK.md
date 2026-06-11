# SoukPilot AI — Runbook

Operational guide for starting, stopping, seeding, maintaining, and
troubleshooting SoukPilot AI.

---

## Prerequisites

- Docker Desktop (with Compose v2)
- OpenAI API key with access to: GPT-4o-mini (chat + tool-calling), Whisper-1 (STT), TTS-1 (voice), text-embedding-3-small (embeddings)

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
This runs all 6 migrations (0001–0006) and creates all 17 tables, including
the `users` table, widget tokens, drift signals, and the seeded `superadmin`
account.

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

The comprehensive seed script creates everything needed for a full demo run in
one command.

```bash
# Recommended: full demo seed
docker compose exec backend python sample_data/seed_demo.py
```

This seeds:
- 7 products (5 grocery + 2 apparel) with realistic stock levels
- 419 sales rows over 60 days with weekly seasonality
- 2 invoices from the same supplier (second invoice has deliberate 10–14% price
  increases to trigger price-change alerts)
- 3 orders (WhatsApp + Instagram + manual) with line items
- AI-generated weekly report
- Forecasting model retrain
- RAG index rebuild

After seeding:
- **Dashboard** — stat cards, reorder alerts, and AI anomaly alerts (if any)
- **Inventory** — 7 products with stock levels and reorder badges
- **Reports** — latest weekly report ready; click "Export PDF" to download
- **Business Q&A** — index is built; ask "Which supplier raised prices?"
- **AI Agent** — ask "What should I reorder?" to see the tool-calling loop
- **Voice Copilot** — speak any of the above questions

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

Expected: **71 tests passing**. No OpenAI key or database connection needed.

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
| `SECRET_KEY` | — | ✅ | JWT signing key — generate with `openssl rand -hex 32` |
| `JWT_EXPIRE_HOURS` | `24` | | Token lifetime in hours |
| `REDIS_URL` | `redis://redis:6379/0` | | Celery broker URL |
| `OPENAI_LLM_MODEL` | `gpt-4o-mini` | | Model for extraction + narration |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | | Model for RAG embeddings |
| `CHROMA_HOST` | `chromadb` | | ChromaDB hostname |
| `CHROMA_PORT` | `8000` | | ChromaDB port |
| `UPLOAD_DIR` | `/app/uploads` | | Where invoice files are stored |
| `MAX_UPLOAD_SIZE_MB` | `20` | | Max invoice upload size |
| `APP_ENV` | `development` | | `development` or `production` |
| `ALLOWED_ORIGINS` | `http://localhost:5173,...` | | Comma-separated CORS origins |
| `TWILIO_ACCOUNT_SID` | — | | Twilio account SID (WhatsApp webhooks) |
| `TWILIO_AUTH_TOKEN` | — | | Twilio auth token for webhook signature validation |
| `TWILIO_WHATSAPP_NUMBER` | — | | Twilio WhatsApp sender number (e.g. `whatsapp:+14155238886`) |

---

## Superadmin Access

The superadmin account is seeded by migration 0006.

**Default credentials:** `superadmin` / `superadmin2024`
**Portal URL:** http://localhost:5173/superadmin

Change the password immediately after any public deployment:

```bash
# Generate a new bcrypt hash
docker compose exec backend python -c "
from app.core.security import hash_password
print(hash_password('your-new-password'))
"

# Update the DB
docker compose exec postgres psql -U soukpilot -d soukpilot -c \
  "UPDATE users SET hashed_password = '<paste hash here>' WHERE username = 'superadmin';"
```

The superadmin token is stored in the browser under `soukpilot_admin_token`,
separate from the tenant `soukpilot_token`. Log out from each independently.

---

## Deployment Guide (Presentation / Production)

SoukPilot runs as a Docker Compose stack; any platform that supports Docker
or can run individual services works. The recommended path for a quick
presentation deployment is **Railway** (all services in one project) or
**Render + Supabase** (managed Postgres).

### Option A — Railway (easiest)

1. Push the repo to GitHub.
2. Create a new Railway project → "Deploy from GitHub".
3. Railway detects `docker-compose.yml` automatically.
4. Set environment variables in Railway's Variables panel (copy from `.env`).
5. Railway assigns a public domain; set `ALLOWED_ORIGINS` to that domain.
6. After first deploy, open a Railway shell and run:
   ```bash
   alembic upgrade head
   python sample_data/seed_demo.py
   ```

### Option B — Render

1. **Database:** Create a Render Postgres instance; copy the DSN.
2. **Redis:** Create a Render Redis instance; copy the URL.
3. **Backend:** New "Web Service" → Docker → set all env vars → deploy.
4. **Worker:** New "Background Worker" → same Docker image → set
   `CMD` to `celery -A app.worker worker --loglevel=info`.
5. **Frontend:** New "Static Site" → `npm run build` → publish `dist/`.
   Set `VITE_API_URL` to the backend's public URL before building.

### Option C — Fly.io

```bash
fly auth login
fly launch --dockerfile backend/Dockerfile --name soukpilot-api
fly secrets set OPENAI_API_KEY=... DATABASE_URL=... SECRET_KEY=...
fly deploy
```

Create a Fly Postgres and Redis separately and link them via `DATABASE_URL`
and `REDIS_URL` secrets.

### Pre-deployment checklist

- [ ] `SECRET_KEY` is a random 32-byte hex string (not the default)
- [ ] Default superadmin password has been changed
- [ ] `ALLOWED_ORIGINS` includes only your production domain
- [ ] `APP_ENV=production` is set
- [ ] HTTPS is configured on the hosting platform (all three options above
      provide TLS automatically)
- [ ] Migrations have been run: `alembic upgrade head`
- [ ] Demo data seeded if presenting: `python sample_data/seed_demo.py`

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
| "Invalid credentials" on superadmin login | Migration 0006 may not have run — run `alembic upgrade head` |
| Superadmin login redirects to regular app | Browser saved old token; clear `localStorage` or open incognito |
| JWT 401 on all business routes after re-deploy | `SECRET_KEY` changed — old tokens are invalidated; log in again |
| Twilio webhook returns 403 | `TWILIO_AUTH_TOKEN` env var not set or incorrect |
| Voice mic button does nothing | Browser requires HTTPS or `localhost` for microphone access — ensure you're on `http://localhost:5173` |
| Voice transcription returns empty transcript | Recording was too short or silent — speak clearly for at least 1 second |
| TTS audio does not play | Check browser autoplay policy; some browsers block audio without a prior user gesture — the mic press counts as one |
| "TTS failed" error in voice response | `OPENAI_API_KEY` lacks TTS-1 access, or text exceeded API limits — browser SpeechSynthesis fallback will engage automatically |
| AI anomaly alerts not appearing on Dashboard | No anomalies detected (normal) OR insufficient sales history (< 7 days per product) — run `seed_demo.py` to generate history |
| Agent chat returns "Something went wrong" | Max 8 tool iterations reached without a final answer — rephrase the question more specifically |

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
