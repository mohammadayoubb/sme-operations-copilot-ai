"""Tests for the RAG core (chunking, context building, grounded answering).

The retrieval and generation calls are monkeypatched, so these run with no
network, no vector store, and no database — they verify the grounding logic:
real context in → answer + sources; no context → a guaranteed "I don't know".
"""
from app.ai import rag


# ── chunking ───────────────────────────────────────────────────────

def test_chunk_text_short_returns_single_chunk():
    assert rag.chunk_text("a short summary") == ["a short summary"]


def test_chunk_text_empty_returns_nothing():
    assert rag.chunk_text("   ") == []


def test_chunk_text_long_overlaps_and_covers():
    text = "x" * 4000
    chunks = rag.chunk_text(text, size=1500, overlap=200)
    assert len(chunks) > 1
    assert all(len(c) <= 1500 for c in chunks)
    # full coverage: total chars across chunks exceeds the original (overlap)
    assert sum(len(c) for c in chunks) >= len(text)


# ── context building ───────────────────────────────────────────────

def test_build_context_numbers_each_hit():
    hits = [{"document": "Invoice #1 ..."}, {"document": "Order #2 ..."}]
    ctx = rag.build_context(hits)
    assert "[1] Invoice #1 ..." in ctx
    assert "[2] Order #2 ..." in ctx


# ── grounded answering ─────────────────────────────────────────────

def test_answer_question_refuses_when_no_evidence(monkeypatch):
    monkeypatch.setattr(rag, "retrieve", lambda q, top_k=5: [])

    def _should_not_run(*a, **k):  # generation must NOT be called with no context
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
    # the retrieved context was passed to generation
    assert "Invoice #1 from supplier ABC" in captured["context"]
    # sources are mapped with similarity = 1 - distance
    assert len(result["sources"]) == 2
    assert result["sources"][0]["source_type"] == "invoice"
    assert result["sources"][0]["source_id"] == 1
    assert result["sources"][0]["score"] == 0.9
    assert result["sources"][1]["score"] == 0.75
