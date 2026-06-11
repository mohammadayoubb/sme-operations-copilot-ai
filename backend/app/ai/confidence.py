"""Deterministic confidence scoring for LLM-extracted orders.

Score is in [0.0, 1.0]. Below CONFIDENCE_THRESHOLD the order is routed to
the human review queue instead of being auto-committed.

All logic is pure Python — the LLM never scores itself.
"""
from __future__ import annotations

from app.schemas.order import ExtractedOrder

CONFIDENCE_THRESHOLD = 0.85  # demo-friendly: any missing field routes to review


def compute_confidence(extracted: ExtractedOrder) -> float:
    """Return a confidence score for the extraction quality.

    Only 'new_order' extractions go through review — inquiries, complaints,
    and other intents don't touch inventory so they're always auto-approved.
    """
    if extracted.intent != "new_order":
        return 1.0

    score = 1.0

    if not extracted.items:
        return 0.20  # Nothing extracted — strong signal of garbled input

    # Missing fulfillment fields
    if not extracted.delivery_area:
        score -= 0.12

    if not extracted.payment_method:
        score -= 0.08

    # Suspiciously large item count — likely a multi-order or garbled message
    if len(extracted.items) > 6:
        score -= 0.10

    # Very short / suspicious product names
    for item in extracted.items:
        name = (item.product or "").strip()
        if len(name) < 2:
            score -= 0.15

    return round(max(0.0, min(1.0, score)), 2)


def confidence_label(score: float) -> str:
    if score >= CONFIDENCE_THRESHOLD:
        return "high"
    if score >= 0.50:
        return "medium"
    return "low"
