# Deploying SoukPilot AI to Railway

Step-by-step guide for a public demo deployment. Total time: ~20 minutes.

## Architecture on Railway

Railway cannot share a volume between two services, but SoukPilot's backend
and Celery worker **must** share a filesystem (`uploads/` — backend saves
invoice files, worker OCRs them; `ml_models/` — worker trains the forecast
model and writes the RAG index, backend reads them). So instead of mirroring
docker-compose 1:1, the deployment uses **4 Railway services**:

| Railway service | Source | Notes |
|---|---|---|
| **Postgres** | Railway database catalog | managed, persistent |
| **Redis** | Railway database catalog | managed |
| **app** | this repo, `Dockerfile.railway` | uvicorn + Celery worker + Celery beat in one container, volume at `/data` |
| **frontend** | this repo, `frontend/Dockerfile.prod` | static Vite build served with SPA fallback |

> **Note:** ChromaDB does *not* need to be deployed. Despite older docs, the
> vector store is a local joblib index in `ML_MODELS_DIR`
> (`backend/app/ai/vector_store.py`); `chromadb` is commented out in
> `requirements.txt` and `docker-compose.yml`.

`deploy/start.sh` runs `alembic upgrade head` automatically on every deploy,
so migrations (including the superadmin seed in migration 0006) need no
manual step.

## Step 1 — Push to GitHub

The repo is already at `github.com/mohammadayoubb/sme-operations-copilot-ai`.
Make sure the deploy files are pushed (`Dockerfile.railway`, `deploy/start.sh`,
`frontend/Dockerfile.prod`).

## Step 2 — Create the project + databases

1. [railway.app](https://railway.app) → **New Project**.
2. In the project canvas: **Create → Database → PostgreSQL**.
3. **Create → Database → Redis**.

## Step 3 — Deploy the app service (backend + worker + beat)

1. **Create → GitHub Repo** → select the repo.
2. Before the first deploy finishes, open the service → **Settings**:
   - **Build → Dockerfile Path:** `Dockerfile.railway`
   - **Volumes:** attach a volume, mount path **`/data`**
   - **Networking → Generate Domain**, target port **8080**
     (note this domain — it's the `VITE_API_URL` for the frontend)
3. **Variables** tab — add:

   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   OPENAI_API_KEY=sk-...
   SECRET_KEY=<openssl rand -hex 32 — never the default>
   JWT_EXPIRE_HOURS=24
   APP_ENV=production
   ALLOWED_ORIGINS=https://<frontend-domain>        # fill in after Step 4
   UPLOAD_DIR=/data/uploads
   ML_MODELS_DIR=/data/ml_models
   ```

   Optional (WhatsApp webhook): `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`,
   `TWILIO_WHATSAPP_FROM`. See **WhatsApp orders in the demo** below.

4. Deploy. Watch the logs: you should see `Running database migrations...`,
   the Celery banner, then uvicorn on port 8080.
5. Verify: `https://<app-domain>/health` →
   `{"status":"ok","database":"connected"}`, and `/docs` loads.

## Step 4 — Deploy the frontend

1. **Create → GitHub Repo** → same repo again (second service).
2. **Settings**:
   - **Root Directory:** `frontend`
   - **Build → Dockerfile Path:** `Dockerfile.prod`
   - **Networking → Generate Domain**, target port **4173**
3. **Variables** tab:

   ```
   VITE_API_URL=https://<app-domain>
   ```

   ⚠️ `VITE_API_URL` is baked in at **build** time. If you change it, you
   must trigger a redeploy (Railway does this automatically when the
   variable changes).

4. Go back to the **app** service and set
   `ALLOWED_ORIGINS=https://<frontend-domain>` (no trailing slash), which
   triggers an app redeploy.

## Step 5 — Seed demo data

Install the Railway CLI and open a shell in the app container:

```bash
npm i -g @railway/cli
railway login
railway link        # pick the project + app service
railway ssh
# inside the container:
python sample_data/seed_demo.py
```

(The image sets `PYTHONPATH=/app` and bundles `sample_data/`, so the script
runs directly — no stdin piping needed like in local dev.)

## Step 6 — Change the superadmin password

Still inside `railway ssh`:

```bash
python -c "from app.core.security import hash_password; print(hash_password('your-new-password'))"
```

Then in the Railway **Postgres** service → **Data** tab (or `railway connect postgres`):

```sql
UPDATE users SET hashed_password = '<paste hash>' WHERE username = 'superadmin';
```

## Step 7 — Demo checklist

- [ ] `https://<frontend-domain>` loads; register a business or log in
- [ ] `https://<frontend-domain>/superadmin` → superadmin login works
- [ ] Dashboard shows seeded stats + reorder alerts
- [ ] Business Q&A: "Which supplier raised prices?" (index built by seed)
- [ ] AI Agent: "What should I reorder?"
- [ ] Voice Copilot works (mic requires HTTPS — Railway domains are HTTPS ✓)
- [ ] Upload a sample invoice → status flips `pending → processed`
      (proves the Celery worker is alive)

## WhatsApp orders in the demo (Twilio sandbox)

The webhook (`POST /api/webhooks/whatsapp`) extracts an order from the
message via LLM, creates it, and replies with a confirmation over WhatsApp.

1. Create a free [Twilio](https://www.twilio.com) account (trial is enough).
2. Console → **Messaging → Try it out → Send a WhatsApp message**. From your
   phone, send the shown join code (e.g. `join <two-words>`) to the sandbox
   number `+1 415 523 8886`.
3. In **Sandbox settings**, set *"When a message comes in"* to
   `https://<app-domain>/api/webhooks/whatsapp`, method **POST**. Save.
4. On the Railway **app** service, set:

   ```
   TWILIO_ACCOUNT_SID=AC...
   TWILIO_AUTH_TOKEN=...          # Console → Account Info
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   ```

   (If `TWILIO_AUTH_TOKEN` is left blank, signature validation is skipped —
   the webhook still works, but anyone who finds the URL can post fake
   orders. Fine for a rehearsal, set it for the real demo.)
5. WhatsApp the sandbox number something like
   *"Hi, I want 2 black hoodies size L and 1 white t-shirt, delivery to
   Hamra, cash on delivery"* → you get a confirmation reply, and the order
   appears on the **Orders** page.

**Demo caveats:**

- The webhook can't know which tenant a message belongs to, so it hardcodes
  **business_id=1** — the first business in the DB (the one `seed_demo.py`
  creates). Demo WhatsApp orders while logged into *that* business, not a
  newly registered one.
- Twilio sandbox only delivers to phones that have joined (step 2), and the
  join expires after 72 hours — **re-send the join code the day of the
  presentation**.
- Signature validation requires the uvicorn proxy-header flags already set
  in `deploy/start.sh`; without them Twilio's signature (computed over the
  `https://` URL) never matches and every webhook returns 403.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Frontend loads but every API call 404s against the frontend domain | `VITE_API_URL` was empty at build time — set it and redeploy the frontend |
| Browser console shows CORS errors | `ALLOWED_ORIGINS` on the app service doesn't exactly match the frontend origin (scheme + host, no trailing slash) |
| `relation "users" does not exist` / superadmin login fails | Migrations didn't run — check deploy logs for the `alembic upgrade head` output |
| Invoice stuck in `pending` | Worker died inside the container — check app service logs for the Celery banner and tracebacks |
| Data disappears after redeploy | Volume not mounted at `/data`, or `UPLOAD_DIR`/`ML_MODELS_DIR` don't point into it (Postgres data is safe regardless — it lives in the managed DB) |
| JWT 401 on everything after a redeploy | `SECRET_KEY` changed between deploys — keep it stable in Variables |

## Fallback: Render / Fly.io

If Railway is unavailable, the same combined-container approach works
anywhere that runs a Dockerfile with one persistent volume:

- **Render:** Web Service from `Dockerfile.railway` + Render Disk at `/data`
  + managed Postgres + Key Value (Redis). Frontend as a Static Site
  (`npm run build`, publish `frontend/dist`, set `VITE_API_URL` env var).
  Note: Render's free Postgres expires after 30 days; disks require a paid
  instance.
- **Fly.io:** `fly launch` with `Dockerfile.railway`, a Fly volume mounted at
  `/data`, Fly Postgres, and Upstash Redis. Frontend as a second app from
  `frontend/Dockerfile.prod`.
