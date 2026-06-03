"""RAG retrieval + grounded generation.

Pure orchestration: embed the question → vector search → build context → ask the
LLM to answer using ONLY that context. Returns the answer plus its source records.
If nothing is retrieved we refuse with a fixed message instead of calling the LLM
(so "I don't know" is guaranteed when there's no evidence).
"""
from __future__ import annotations

# Must match the refusal phrase in RAG_QA_PROMPT.
NO_DATA_ANSWER = "I don't have enough data to answer that."


def chunk_text(text: str, size: int = 1500, overlap: int = 200) -> list[str]:
    """Split text into overlapping character windows. Short text → one chunk."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    step = max(1, size - overlap)
    chunks: list[str] = []
    for start in range(0, len(text), step):
        chunk = text[start:start + size].strip()
        if chunk:
            chunks.append(chunk)
        if start + size >= len(text):
            break
    return chunks


def build_context(hits: list[dict]) -> str:
    """Render retrieved chunks as a numbered list for the prompt."""
    lines = []
    for i, h in enumerate(hits, 1):
        lines.append(f"[{i}] {h.get('document', '').strip()}")
    return "\n".join(lines)


def retrieve(question: str, top_k: int = 5) -> list[dict]:
    from app.ai import embeddings, vector_store

    qvec = embeddings.embed_text(question)
    return vector_store.query(qvec, n_results=top_k)


def generate_answer(question: str, context: str) -> str:
    from app.ai.llm import complete_text
    from app.ai.prompts import RAG_QA_PROMPT

    prompt = RAG_QA_PROMPT.format(context=context, question=question)
    return complete_text(prompt)


def _to_source(hit: dict) -> dict:
    meta = hit.get("metadata") or {}
    dist = hit.get("distance")
    return {
        "source_type": meta.get("source_type"),
        "source_id": meta.get("source_id"),
        "content": hit.get("document", ""),
        # cosine distance → similarity score in [0, 1]
        "score": round(1.0 - float(dist), 4) if dist is not None else None,
    }


def answer_question(question: str, top_k: int = 5) -> dict:
    """Full RAG flow. Returns {answer, grounded, sources}."""
    hits = retrieve(question, top_k)
    if not hits:
        return {"answer": NO_DATA_ANSWER, "grounded": False, "sources": []}

    context = build_context(hits)
    answer = generate_answer(question, context)
    return {
        "answer": answer,
        "grounded": True,
        "sources": [_to_source(h) for h in hits],
    }
