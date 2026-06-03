"""RAG retrieval + grounded generation.

Basic flow: embed → vector search → build context → LLM answer.
Advanced flow (retrieve_reranked): vector search for more candidates → BM25
rerank via Reciprocal Rank Fusion → parent lookup for full context → LLM answer.

The plain answer_question() is kept unchanged so its unit tests stay valid.
rag_service.ask() uses retrieve_reranked for the full advanced flow.
"""
from __future__ import annotations

# Must match the refusal phrase in RAG_QA_PROMPT.
NO_DATA_ANSWER = "I don't have enough data to answer that."


def chunk_text(text: str, size: int = 400, overlap: int = 50) -> list[str]:
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


# ── BM25 + Reciprocal Rank Fusion ────────────────────────────────────

def bm25_scores(question: str, documents: list[str]) -> list[float]:
    """BM25 Okapi relevance scores for each document against the question.

    Implemented natively (no external dependency) using the standard formula:
        score(D, Q) = sum_t IDF(t) * tf(t,D)*(k1+1) / (tf(t,D) + k1*(1-b+b*|D|/avgdl))
    with k1=1.5, b=0.75, smooth IDF.
    """
    import math

    k1, b = 1.5, 0.75
    tokenized = [doc.lower().split() for doc in documents]
    query_terms = question.lower().split()
    n = len(tokenized)

    if n == 0 or not query_terms:
        return [0.0] * n

    avgdl = sum(len(d) for d in tokenized) / n

    # Document frequency per term.
    df: dict[str, int] = {}
    for doc in tokenized:
        for term in set(doc):
            df[term] = df.get(term, 0) + 1

    scores = []
    for doc in tokenized:
        tf: dict[str, int] = {}
        for term in doc:
            tf[term] = tf.get(term, 0) + 1
        dl = len(doc)
        score = 0.0
        for term in query_terms:
            f = tf.get(term, 0)
            if f == 0:
                continue
            idf = math.log((n - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5) + 1)
            score += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / avgdl))
        scores.append(score)
    return scores


def rrf_rerank(hits: list[dict], question: str, k: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion: blend vector rank with BM25 rank.

    hits is already sorted by vector similarity (best first). We compute
    BM25 ranks for the same docs and combine: score = 1/(k+vec_rank) + 1/(k+bm25_rank).
    Higher combined score = better.
    """
    if len(hits) <= 1:
        return hits

    docs = [h.get("document", "") for h in hits]
    bm25_s = bm25_scores(question, docs)

    # bm25 rank order (descending score → ascending rank position)
    bm25_order = sorted(range(len(hits)), key=lambda i: -bm25_s[i])
    bm25_rank = {idx: rank for rank, idx in enumerate(bm25_order)}

    scored = []
    for vec_rank, (i, h) in enumerate(zip(range(len(hits)), hits)):
        rrf = 1.0 / (k + vec_rank) + 1.0 / (k + bm25_rank[i])
        scored.append((rrf, h))

    scored.sort(key=lambda x: -x[0])
    return [h for _, h in scored]


def retrieve_reranked(question: str, top_k: int = 5) -> tuple[list[dict], dict]:
    """Hybrid retrieval: vector search for more candidates, then BM25 rerank.

    Returns (reranked_hits[:top_k], retrieval_stats).
    """
    candidates = retrieve(question, top_k=top_k * 3)
    if not candidates:
        return [], {"candidates": 0, "reranked": False, "returned": 0}

    reranked = rrf_rerank(candidates, question)
    final = reranked[:top_k]
    return final, {
        "candidates": len(candidates),
        "reranked": True,
        "returned": len(final),
    }


# ── Generation ────────────────────────────────────────────────────────

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
    """Basic RAG flow (used by unit tests). Returns {answer, grounded, sources}.

    Production code uses rag_service.ask() which calls retrieve_reranked and
    does parent-document lookup for richer context.
    """
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
