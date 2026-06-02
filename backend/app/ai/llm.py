"""Thin OpenAI client wrapper. Returns raw JSON strings for the extraction
layer to parse and validate."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import settings


@lru_cache(maxsize=1)
def _client():
    from openai import OpenAI  # lazy import

    return OpenAI(api_key=settings.openai_api_key)


def complete_json(prompt: str, *, temperature: float = 0.0) -> str:
    """Send a single-prompt completion forced into JSON mode.

    Returns the raw JSON string content (not yet validated)."""
    resp = _client().chat.completions.create(
        model=settings.openai_llm_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=temperature,
    )
    return resp.choices[0].message.content or "{}"


def complete_text(prompt: str, *, temperature: float = 0.4) -> str:
    """Free-form text completion (used for business explanations/reports)."""
    resp = _client().chat.completions.create(
        model=settings.openai_llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip()
