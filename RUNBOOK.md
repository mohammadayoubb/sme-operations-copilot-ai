# SoukPilot AI — Runbook

## Prerequisites
- Docker + Docker Compose
- An OpenAI API key

## 1. Configure environment
```bash
cp .env.example .env
# edit .env and set: OPENAI_API_KEY=sk-...your-real-key
```

## 2. Start all services
```bash
docker compose up --build
```
Services: `postgres`, `redis`, `chromadb`, `backend` (8080), `worker`, `beat`, `frontend` (5173).

## 3. Run database migrations (first run only)
In a second terminal:
```bash
docker compose exec backend alembic upgrade head
```
This creates all 14 tables.

## 4. Verify it's up
- API health: http://localhost:8080/health → `{"status":"ok","database":"connected"}`
- API docs (Swagger): http://localhost:8080/docs
- Frontend: http://localhost:5173

## 5. Test the invoice pipeline (Phase 1)
1. Open the frontend → **Invoices** page.
2. Upload `sample_data/invoices/sample_invoice_abc_foods.png`.
3. The page shows "OCR + AI extraction running…" then displays the structured
   result: supplier, date, line items, totals, and any price-change flags.
4. Re-upload the same invoice with a changed price to see a **price-increase alert**.

What happens under the hood:
- `POST /api/invoices/upload` saves the file, creates a `pending` invoice row,
  and enqueues a Celery job.
- The `worker` runs OCR (EasyOCR) → LLM extraction → Pydantic validation →
  one DB transaction (invoice + items + stock update + inventory movements +
  price comparison + alerts).
- The frontend polls `GET /api/invoices/{id}/status` until `processed`.

## Running tests
```bash
docker compose exec backend pytest -v
# or locally (extraction tests need only pydantic + pytest):
cd backend && pytest tests/test_invoice_extraction.py -v
```

## Common issues
| Symptom | Fix |
|---|---|
| `database: unreachable` on /health | Postgres still starting; wait, then retry |
| Invoice stuck on `pending` | Check `docker compose logs worker` |
| Invoice → `failed` | Usually a bad/missing `OPENAI_API_KEY` or OCR found no text |
| First OCR call is slow | EasyOCR downloads its model on first use (one-time) |
| Migrations not applied | Run `docker compose exec backend alembic upgrade head` |
