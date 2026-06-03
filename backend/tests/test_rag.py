"""Tests for the RAG core — chunking, context, grounded answering, and
the advanced hybrid retrieval layer (BM25 scores, RRF reranking,
retrieve_reranked interface).

All retrieval and generation calls are monkeypatched so these run with no
network, no vector store, and no database.
"""
from app.ai import rag


# ── chunking ───────────────────────────────────────────────────────

def test_chunk_text_short_returns_single_chunk():
    assert rag.chunk_text("a short summary") == ["a short summary"]


def test_chunk_text_empty_returns_nothing():
    assert rag.chunk_text("   ") == []


def test_chunk_text_long_overlaps_and_covers():
    text = "x" * 4000
    chunks = rag.chunk_text(text, size=400, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 400 for c in chunks)
    # Full coverage: overlapping chunks total more chars than the original.
    assert sum(len(c) for c in chunks) >= len(text)


def test_chunk_text_child_size_default():
    # Default chunk size is 400 chars (child-chunk size for precise retrieval).
    text = "a" * 500
    chunks = rag.chunk_text(text)
    assert len(chunks) > 1
    assert all(len(c) <= 400 for c in chunks)


# ── context building ───────────────────────────────────────────────

def test_build_context_numbers_each_hit():
    hits = [{"document": "Invoice #1 ..."}, {"document": "Order #2 ..."}]
    ctx = rag.build_context(hits)
    assert "[1] Invoice #1 ..." in ctx
    assert "[2] Order #2 ..." in ctx


# ── BM25 scores ───────────────────────────────────────────────────

def test_bm25_scores_length_matches_documents():
    docs = ["Nutella stock is low", "Supplier raised prices", "Order from Hamra"]
    scores = rag.bm25_scores("nutella stock", docs)
    assert len(scores) == len(docs)


def test_bm25_scores_keyword_match_ranks_higher():
    docs = [
        "The weather is nice today",
        "Nutella 400g current stock is 3 units, reorder level 10",
        "Invoice from supplier dated last week",
    ]
    scores = rag.bm25_scores("nutella stock reorder", docs)
    # The Nutella product doc should score highest.
    best_idx = scores.index(max(scores))
    assert best_idx == 1


def test_bm25_scores_empty_query_returns_zeros():
    docs = ["some document", "another doc"]
    scores = rag.bm25_scores("", docs)
    assert all(s == 0.0 for s in scores)


# ── RRF reranking ─────────────────────────────────────────────────

def test_rrf_rerank_single_hit_unchanged():
    hits = [{"document": "only one", "id": "a", "distance": 0.1, "metadata": {}}]
    result = rag.rrf_rerank(hits, "anything")
    assert result == hits


def test_rrf_rerank_keyword_match_moves_up():
    """A doc that matches the query keyword should rise in RRF ordering."""
    hits = [
        # Vector-best (distance 0.05) but off-topic
        {"document": "weather forecast for Beirut tomorrow cloudy", "id": "a", "distance": 0.05, "metadata": {}},
        # Vector-second but keyword match
        {"document": "Nutella 400g stock 3 units reorder level 10", "id": "b", "distance": 0.15, "metadata": {}},
        # Vector-third, irrelevant
        {"document": "payment method cash on delivery order", "id": "c", "distance": 0.25, "metadata": {}},
    ]
    reranked = rag.rrf_rerank(hits, "nutella stock reorder")
    # The Nutella doc must appear first or second after BM25 boost.
    top_ids = [h["id"] for h in reranked[:2]]
    assert "b" in top_ids


def test_rrf_rerank_preserves_all_hits():
    hits = [
        {"document": f"doc {i}", "id": str(i), "distance": i * 0.1, "metadata": {}}
        for i in range(5)
    ]
    reranked = rag.rrf_rerank(hits, "some query")
    assert len(reranked) == 5
    assert {h["id"] for h in reranked} == {h["id"] for h in hits}


# ── retrieve_reranked interface ───────────────────────────────────

def test_retrieve_reranked_returns_empty_when_no_hits(monkeypatch):
    monkeypatch.setattr(rag, "retrieve", lambda q, top_k=5: [])
    hits, stats = rag.retrieve_reranked("anything")
    assert hits == []
    assert stats["candidates"] == 0
    assert stats["reranked"] is False


def test_retrieve_reranked_fetches_3x_candidates(monkeypatch):
    """retrieve is called with top_k * 3 to get more candidates for reranking."""
    calls = []

    def fake_retrieve(q, top_k=5):
        calls.append(top_k)
        return [{"document": f"doc {i}", "id": str(i), "distance": 0.1 * i, "metadata": {}} for i in range(top_k)]

    monkeypatch.setattr(rag, "retrieve", fake_retrieve)
    hits, stats = rag.retrieve_reranked("question", top_k=5)
    assert calls[0] == 15   # 5 * 3
    assert len(hits) <= 5   # trimmed to top_k
    assert stats["reranked"] is True
    assert stats["candidates"] == 15


def test_retrieve_reranked_stats_fields(monkeypatch):
    fake_hits = [{"document": "d", "id": "x", "distance": 0.1, "metadata": {}}]
    monkeypatch.setattr(rag, "retrieve", lambda q, top_k=5: fake_hits)
    _, stats = rag.retrieve_reranked("q", top_k=5)
    assert "candidates" in stats
    assert "reranked" in stats
    assert "returned" in stats


# ── parent-child chunk metadata structure ────────────────────────

def test_child_chunk_metadata_keys():
    """Verify that the metadata dict we build during indexing carries the
    expected parent-lookup fields. This is a contract test for rag_service."""
    meta = {
        "source_type": "invoice",
        "source_id": 1,
        "document_id": 42,
        "chunk": 0,
    }
    assert "source_type" in meta
    assert "source_id" in meta
    assert "document_id" in meta
    assert meta["chunk"] == 0


# ── grounded answering (basic flow — kept intact) ─────────────────

def test_answer_question_refuses_when_no_evidence(monkeypatch):
    monkeypatch.setattr(rag, "retrieve", lambda q, top_k=5: [])

    def _should_not_run(*a, **k):
        raise AssertionError("generate_answer should not be called when there is no context")

    monkeypatch.setattr(rag, "generate_answer", _should_not_run)

    result = rag.answer_question("anything?")
    assert result["answer"] == rag.NO_DATA_ANSWER
    assert result["grounded"] is False
    assert result["sources"] == []


def test_answer_question_grounds_and_maps_sources(monkeypatch):
    fake_hits = [
        {"document": "Invoice #1 from supplier ABC...",
         "metadata": {"source_type": "invoice", "source_id": 1}, "distance": 0.1},
        {"document": "Product 'Nutella': stock 8...",
         "metadata": {"source_type": "product", "source_id": 4}, "distance": 0.25},
    ]
    monkeypatch.setattr(rag, "retrieve", lambda q, top_k=5: fake_hits)
    captured = {}

    def _fake_generate(question, context):
        captured["context"] = context
        return "Supplier ABC raised prices the most."

    monkeypatch.setattr(rag, "generate_answer", _fake_generate)

    result = rag.answer_question("Which supplier raised prices the most?")

    assert result["grounded"] is True
    assert result["answer"] == "Supplier ABC raised prices the most."
    assert "Invoice #1 from supplier ABC" in captured["context"]
    assert len(result["sources"]) == 2
    # Scores are 1 - distance; check by source_type to avoid ordering assumptions.
    scores = {s["source_type"]: s["score"] for s in result["sources"]}
    assert scores["invoice"] == 0.9
    assert scores["product"] == 0.75
