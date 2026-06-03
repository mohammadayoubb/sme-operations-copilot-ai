"""Pydantic schemas for the RAG business Q&A feature."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class QARequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class QASource(BaseModel):
    source_type: Optional[str] = None     # invoice, order, product
    source_id: Optional[int] = None
    content: str
    score: Optional[float] = None          # cosine similarity in [0, 1]


class QAResponse(BaseModel):
    answer: str
    grounded: bool                         # False when no evidence was found
    sources: list[QASource] = []
    retrieval_stats: dict = {}             # {"candidates": 15, "reranked": True, "parents_shown": 5}


class IndexResponse(BaseModel):
    status: str
    documents_indexed: int
    chunks_indexed: int
