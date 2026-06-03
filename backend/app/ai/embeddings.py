"""OpenAI embedding generation.

We generate embeddings ourselves (text-embedding-3-small) and hand the vectors to
ChromaDB, so Chroma is used purely as a vector store — no server-side embedding
model needed.
"""
from __future__ import annotations

from app.core.config import settings


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns one vector per input, in order."""
    if not texts:
        return []
    from app.ai.llm import _client  # reuse the cached OpenAI client

    resp = _client().embeddings.create(model=settings.openai_embedding_model, input=texts)
    return [d.embedding for d in resp.data]


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]
