# SoukPilot AI — Phase Stretch: Advanced RAG Summary

**Feature:** Advanced RAG — Hybrid Reranking + Parent-Child Chunking
**Status:** ✅ Complete, 62 tests passing (11 new)
**Date:** 2026-06-03

---

## 1. What This Phase Does (in plain words)

The original RAG pipeline did one thing: embed the question, run cosine similarity
against stored chunks, return the top 5 hits. It worked, but it had two weaknesses:

1. **Flat chunking (1500 chars)** — large chunks are noisy. The retrieval vector
   represents too many ideas at once, hurting precision.

2. **Vector-only ranking** — cosine similarity is semantic but keyword-blind.
   If the owner asks "which supplier raised Nutella prices?", a document that
   literally contains "Nutella prices" should rank higher — but pure vector
   similarity might miss it if semantically similar docs crowd it out.

This phase fixes both:

**Parent-child chunking:** The full document text (parent) is stored in the
`documents` Postgres table. Small 400-char chunks (children) are embedded and
stored in the vector store. Retrieval searches children (more precise), then
looks up the parent full text to pass to the LLM (richer context).

**BM25 hybrid reranking via Reciprocal Rank Fusion:** We retrieve `top_k × 3`
candidates from the vector store (e.g., 15 for top_k=5). Then we score the same
candidates with BM25 Okapi (keyword frequency × IDF). The two ranked lists are
combined using Reciprocal Rank Fusion: `score = 1/(k+vec_rank) + 1/(k+bm25_rank)`.
The final top-5 is from this merged ranking. No extra LLM calls, no heavy
dependencies — the BM25 algorithm is implemented natively in ~25 lines of Python.

---

## 2. Key Files Changed

| File | Change |
|---|---|
| `backend/app/ai/rag.py` | Added `bm25_scores()`, `rrf_rerank()`, `retrieve_reranked()`. Reduced default chunk size to 400/50 (child chunks). `answer_question()` kept unchanged for unit test compatibility. |
| `backend/app/services/rag_service.py` | `index_all()` uses 400-char child chunks. `ask()` now calls `retrieve_reranked()` and does parent lookup from the `documents` table before building LLM context. Returns `retrieval_stats` in response. |
| `backend/app/schemas/qa.py` | Added `retrieval_stats: dict = {}` to `QAResponse`. |
| `frontend/src/pages/BusinessQA.tsx` | Added HYBRID badge (indigo), retrieval stats line ("15 candidates · BM25 reranked · 5 sources"), and `RetrievalStats` TypeScript interface. |
| `backend/tests/test_rag.py` | 11 new tests covering: BM25 scoring, RRF reranking order, `retrieve_reranked` interface, child chunk metadata structure, and the updated chunk size default. |

---

## 3. Design Decisions

**No external package for BM25.** `rank-bm25` was the obvious choice but Docker
containers have no internet access at runtime. The Okapi BM25 formula is
well-defined and trivial to implement (25 lines). This also makes the codebase
self-contained — no dependency update needed, no rebuild required.

**`answer_question()` left unchanged.** Production code calls `rag_service.ask()`
which uses the new hybrid flow. The basic `answer_question()` still exists for
the unit tests that monkeypatch `retrieve` and `generate_answer`. This way the
pre-existing tests needed no rewriting.

**Parent lookup uses the DB, not the vector store.** Parents are already stored
in the `documents` Postgres table from the indexing step. Fetching them by
`(source_type, source_id)` is a cheap indexed query — no need to extend the
vector store.

**RRF constant k=60** is the standard default from the original RRF paper. It
prevents a single top-ranked result from dominating when the other list ranks it
poorly.

---

## 4. What the UI Now Shows

- **HYBRID badge** (indigo/purple) appears next to the GROUNDED badge whenever
  reranking ran.
- **Stats line** under the answer header: `"15 candidates · BM25 reranked · 5 sources"`
- Source cards unchanged — they now show full parent text instead of a single
  400-char child snippet, which reads more naturally.

---

## 5. Demo Talking Points

> "Our RAG uses hybrid retrieval. We first retrieve 15 candidate chunks from the
> vector store using semantic search, then we rerank them with BM25 — a classic
> information retrieval algorithm that scores keyword frequency against the full
> corpus. We blend the two ranked lists using Reciprocal Rank Fusion. The final
> answer is grounded in the full parent document, not just the matched chunk.
> You can see the HYBRID badge and the retrieval stats in the UI."

---

## 6. Tests

```
62 passed (11 new)

New tests in tests/test_rag.py:
  test_chunk_text_child_size_default          — default chunk size is 400
  test_bm25_scores_length_matches_documents   — output length matches input
  test_bm25_scores_keyword_match_ranks_higher — keyword doc scores highest
  test_bm25_scores_empty_query_returns_zeros  — empty query → all zero
  test_rrf_rerank_single_hit_unchanged        — no-op on single document
  test_rrf_rerank_keyword_match_moves_up      — BM25 promotes keyword match
  test_rrf_rerank_preserves_all_hits          — no hits lost or duplicated
  test_retrieve_reranked_returns_empty_when_no_hits
  test_retrieve_reranked_fetches_3x_candidates — confirms top_k*3 call
  test_retrieve_reranked_stats_fields          — stats dict shape
  test_child_chunk_metadata_keys               — parent-lookup contract
```

---

## 7. Manual Test Steps

1. Open the app at http://localhost:5173 → **Business Q&A**
2. Click **↻ Reindex data** (rebuilds with new 400-char child chunks)
3. Ask: *"Which product should I reorder and why?"*
4. Verify the answer card shows:
   - **HYBRID** badge (indigo) next to GROUNDED
   - Stats line: `"15 candidates · BM25 reranked · 5 sources"` (or fewer if index is small)
   - Sources show full parent document text (longer than before)
5. Try a keyword-heavy question: *"Which supplier raised Nutella prices?"*
   — the BM25 layer specifically helps here by boosting exact keyword matches.

---

## 8. Where the Project Stands

| Phase | Feature | Status |
|---|---|---|
| 1 | Invoice OCR + LLM extraction | ✅ |
| 2 | WhatsApp/Instagram order extraction | ✅ |
| 3A | Pricing / Profit Advisor | ✅ |
| 3B | Inventory Forecasting (ML) | ✅ |
| 4 | RAG Business Q&A | ✅ |
| 5 | Weekly Business Report + Guardrails | ✅ |
| 6 | Dashboard wired to live APIs + Voice Assistant | ✅ |
| 7 | Observability logs + full documentation | ✅ |
| Stretch | Agentic tool-calling assistant | ✅ |
| Stretch | PDF report export | ✅ |
| **Stretch** | **Advanced RAG (hybrid reranking + parent-child)** | ✅ |
| 8 | Demo dry run + final prep | Next |
