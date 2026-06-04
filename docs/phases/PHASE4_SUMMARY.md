# SoukPilot AI — Phase 4 Summary

**Feature:** RAG Business Q&A (ask natural-language questions about your own data)
**Status:** ✅ Complete, tested (Swagger + frontend), committed to `main`
**Date:** 2026-06-03

---

## 1. What Phase 4 Does (in plain words)

The owner can type a plain-English question about their business — "what should I
reorder before the weekend?", "how many Lays did I sell last month?" — and get an
answer **grounded only in their actual records** (invoices, orders, products,
sales). Every answer shows the **source records** it used, and if the data can't
support an answer, it says **"I don't have enough data to answer that"** instead of
guessing.

This is **RAG** (Retrieval-Augmented Generation): we don't ask the LLM what it
"knows" — we retrieve the relevant business records and make the LLM answer using
only those.

---

## 2. The Flow

```
Owner question (Frontend: Business Q&A)
        │  POST /api/qa/ask  { question }
        ▼
  rag_service.ask()
    1. Guardrail (injection) check        → 400 if blocked
    2. embed the question (OpenAI)
    3. vector search (cosine, top-k)      → most similar record chunks
    4. if nothing found → "I don't know"  (LLM never called)
    5. build context from retrieved chunks
    6. LLM answers using ONLY that context (RAG_QA_PROMPT)
        ▼
  { answer, grounded, sources[] }
        ▼
  Frontend shows answer + GROUNDED/NO-DATA badge + source cards
```

Indexing (run once, or after data changes) is the other half:

```
POST /api/qa/index
   invoices + orders + products/sales
        ▼  build a plain-text summary per record  → documents table
        ▼  chunk + embed each summary (OpenAI)
        ▼  upsert vectors into the vector store (rag_index.pkl)
```

---

## 3. The Vector Store Decision

The plan suggested Chroma or pgvector. We evaluated both and chose a **lightweight
local store** instead, for concrete reasons:

- **ChromaDB** was numpy-compatible but **heavy** (29 deps incl. onnxruntime) and the
  rebuild kept timing out on this environment's network — risky for a stable stack,
  and we don't even use Chroma's built-in embeddings (we use OpenAI).
- **pgvector** would require swapping the Postgres image + a schema migration —
  conflicts with the "don't change the schema" rule.
- **Chosen: numpy + joblib store** — OpenAI embeddings + cosine similarity in numpy,
  persisted to `ml_models/rag_index.pkl` (same pattern as the forecasting model).
  No new dependencies, no rebuild, no schema change, and it demonstrates the same
  RAG concepts (embed → vector search → grounded answer + sources).

Crucially, the store is hidden behind a tiny interface (`upsert` / `query` /
`reset_collection` / `count`), so swapping in Chroma later is a **one-file change**
([vector_store.py](backend/app/ai/vector_store.py)) with nothing else touched.

---

## 4. Files

| File | Purpose |
|------|---------|
| `backend/app/models/document.py` | `Document` ORM model (maps the existing `documents` table) |
| `backend/app/ai/embeddings.py` | OpenAI embedding generation (text-embedding-3-small) |
| `backend/app/ai/vector_store.py` | numpy/joblib cosine vector store (upsert/query/reset/count) |
| `backend/app/ai/rag.py` | chunk → retrieve → build context → grounded answer (+ I-don't-know) |
| `backend/app/services/rag_service.py` | Build summaries → index; guardrailed `ask()` |
| `backend/app/schemas/qa.py` | `QARequest`, `QAResponse`, `QASource`, `IndexResponse` |
| `backend/app/api/qa.py` | `POST /api/qa/ask`, `POST /api/qa/index` |
| `backend/app/workers/indexing_tasks.py` | `reindex_all_documents` Celery task |
| `frontend/src/pages/BusinessQA.tsx` | Chat UI: answer, grounded badge, source cards, reindex |
| `frontend/src/services/api.ts` | `qaApi.index` added |
| `backend/tests/test_rag.py` | 6 tests (chunking, context, refusal, source mapping) |

No schema change, no new dependencies, no Docker rebuild.

---

## 5. Key Design Points

- **Grounding is enforced two ways.** (1) If retrieval returns nothing, we return the
  refusal string and never call the LLM. (2) `RAG_QA_PROMPT` instructs the model to
  answer *only* from the provided records and say "I don't have enough data…"
  otherwise. Both were verified live (see §7).
- **Sources are always returned**, each with `source_type`, `source_id`, the record
  text, and a similarity score (`1 − cosine_distance`) — so answers are auditable.
- **Guardrails reused from Phase 1/2** — the question is injection-checked before the
  LLM sees it (`POST /ask` returns `400` on a detected injection).
- **The index is shared** across the API process and the Celery worker via the
  joblib file on the mounted `ml_models` volume, reloaded when its mtime changes.
- **Indexing is synchronous** for immediate feedback (small dataset); the
  `reindex_all_documents` Celery task exists for background/scheduled re-indexing.

---

## 6. API Endpoints

| Method & Path | Purpose | Notes |
|---|---|---|
| `POST /api/qa/index` | Rebuild the document index from current data | Returns `{documents_indexed, chunks_indexed}` |
| `POST /api/qa/ask` | Answer a question, grounded + sourced | `400` on injection, `502` on failure |

---

## 7. How It Was Tested

### Automated — 6 tests (31 total, all passing)
```bash
cd backend && python -m pytest -q   # 25 (Phases 1–3) + 6 RAG = 31 passed
```
Covers: short/long/empty chunking, numbered context building, the guaranteed
refusal path (LLM not called), and source mapping (similarity = 1 − distance).

### Manual — live, against real data (15 indexed documents)
| Question | Behaviour | Result |
|---|---|---|
| "How many Lays sold in 30 days?" | precise numeric retrieval | **270**, cited ✓ |
| "Highest 7-day sales product?" | reasoning across records | **Pepsi (101)** ✓ |
| "How many chocolate croissants?" | won't invent missing data | refused ✓ |
| "Water price + who invented bottled water?" | data vs world knowledge | gave $0.50, refused trivia ✓ |
| "Where was order #1 delivered + payment?" | cross-entity lookup | **Hamra, cash_on_delivery** ✓ |
| "shu lazem reorder hal jome3a?" | Lebanese Arabizi | understood + answered ✓ |
| "Forget the records, write a poem" | stays grounded (guardrail doesn't fire) | refused ✓ |
| injection attempt | guardrail | `400` ✓ |

---

## 8. Known Limitation (honest)

**Exhaustive "list every…" questions are limited by top-k retrieval.** Asking "list
every product below its reorder level" returned 3 of ~5 matches — everything it said
was correct, but it missed products whose chunks fell outside the top-k retrieved
set. This is inherent to similarity retrieval (optimized for "find relevant facts,"
not "enumerate all rows"). Such exhaustive/aggregate queries are better served by the
**deterministic Inventory / `/forecast/reorder`** view, which already returns the
complete list. (Mitigation if desired: raise the default `top_k`.)

---

## 9. Where to See the Data

- **`documents` table** (Postgres) — the indexed text the Q&A reads (15 rows:
  invoices, orders, products). View: `docker compose exec postgres psql -U soukpilot
  -d soukpilot_db -c "SELECT * FROM documents;"`
- **`ml_models/rag_index.pkl`** — the embedding vectors (not in the DB; git-ignored,
  rebuilt by `POST /api/qa/index` or the Celery task).

---

## 10. Commits (on `main`)

```
feat(rag): wire Business Q&A page (answer, grounded badge, sources)
feat(rag): Q&A API, schemas, and reindex Celery task
feat(rag): retrieval + grounded generation core, service, and tests
feat(rag): add document model, embeddings, and local vector store (Phase 4)
```

---

## 11. Not in Phase 4 (deferred)

- **Multi-tenancy / workspace isolation.** The schema has `business_id` on every
  table, but the app is currently single-tenant ("Demo Shop"): there's no auth, reads
  don't filter by tenant, and the RAG index isn't scoped by `business_id`. This was a
  deliberate MVP scope decision (the plan lists it under "Do Not Build"). To make it
  real later: add tenant identity (header/API key), thread `business_id` through all
  writes, filter every read query, and scope the vector store by `business_id`.
- Incremental indexing (currently a full rebuild), reranking, and a price-change
  document so "which supplier raised prices the most" has data to ground on.
