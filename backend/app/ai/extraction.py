"""Invoice extraction: prompt → LLM → JSON → validated Pydantic model.

`parse_invoice_json` is deliberately free of any OpenAI/heavy imports so it can
be unit-tested in isolation (it's the deterministic core we actually verify).
"""
from __future__ import annotations

import json

from app.ai.prompts import INVOICE_EXTRACTION_PROMPT, ORDER_EXTRACTION_PROMPT
from app.schemas.invoice import ExtractedInvoice
from app.schemas.order import ExtractedOrder


def parse_invoice_json(raw: str) -> ExtractedInvoice:
    """Parse a raw JSON string from the LLM and validate it against the schema.

    Raises json.JSONDecodeError on malformed JSON and pydantic.ValidationError
    when the structure/values don't satisfy the contract.
    """
    data = json.loads(raw)
    return ExtractedInvoice.model_validate(data)


def extract_invoice(ocr_text: str) -> ExtractedInvoice:
    """Run the full extraction: build prompt, call the LLM, validate output."""
    from app.ai.llm import complete_json  # lazy: avoids openai import in tests

    prompt = INVOICE_EXTRACTION_PROMPT.format(ocr_text=ocr_text)
    raw = complete_json(prompt)
    return parse_invoice_json(raw)


def parse_order_json(raw: str) -> ExtractedOrder:
    """Parse a raw JSON string from the LLM and validate it against the schema.

    Raises json.JSONDecodeError on malformed JSON and pydantic.ValidationError
    when the structure/values don't satisfy the contract.
    """
    data = json.loads(raw)
    return ExtractedOrder.model_validate(data)


def extract_order(message: str) -> ExtractedOrder:
    """Run the full order extraction: build prompt, call the LLM, validate output."""
    from app.ai.llm import complete_json  # lazy: avoids openai import in tests

    prompt = ORDER_EXTRACTION_PROMPT.format(message=message)
    raw = complete_json(prompt)
    return parse_order_json(raw)
