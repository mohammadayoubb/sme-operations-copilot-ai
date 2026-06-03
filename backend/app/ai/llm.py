"""Thin OpenAI client wrapper. Returns raw JSON strings for the extraction
layer to parse and validate."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


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
    content = resp.choices[0].message.content or "{}"
    logger.info(
        "llm_complete_json",
        model=settings.openai_llm_model,
        temperature=temperature,
        prompt_chars=len(prompt),
        response_chars=len(content),
        prompt_tokens=getattr(resp.usage, "prompt_tokens", None),
        completion_tokens=getattr(resp.usage, "completion_tokens", None),
    )
    return content


def stream_text(messages: list[dict], *, temperature: float = 0.4):
    """Stream a chat completion. Yields string token chunks."""
    stream = _client().chat.completions.create(
        model=settings.openai_llm_model,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    for chunk in stream:
        text = chunk.choices[0].delta.content
        if text:
            yield text


def complete_text(prompt: str, *, temperature: float = 0.4) -> str:
    """Free-form text completion (used for business explanations/reports)."""
    resp = _client().chat.completions.create(
        model=settings.openai_llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    content = (resp.choices[0].message.content or "").strip()
    logger.info(
        "llm_complete_text",
        model=settings.openai_llm_model,
        temperature=temperature,
        prompt_chars=len(prompt),
        response_chars=len(content),
        prompt_tokens=getattr(resp.usage, "prompt_tokens", None),
        completion_tokens=getattr(resp.usage, "completion_tokens", None),
    )
    return content
