"""Tests for the order extraction parsing/validation core.

These cover the deterministic layer (`parse_order_json`) without needing
OpenAI or a database — exactly the part we must trust before any DB write
happens.
"""
import json

import pytest
from pydantic import ValidationError

from app.ai.extraction import parse_order_json
from app.schemas.order import ExtractedOrder


VALID_PAYLOAD = {
    "intent": "new_order",
    "items": [
        {"product": "hoodie", "quantity": 3, "color": "black", "size": "L"},
        {"product": "hoodie", "quantity": 2, "color": "white", "size": "M"},
    ],
    "delivery_area": "Hamra",
    "payment_method": "cash_on_delivery",
    "notes": None,
}


def test_parses_valid_order_json():
    order = parse_order_json(json.dumps(VALID_PAYLOAD))

    assert isinstance(order, ExtractedOrder)
    assert order.intent == "new_order"
    assert order.delivery_area == "Hamra"
    assert order.payment_method == "cash_on_delivery"
    assert order.notes is None
    assert len(order.items) == 2
    assert order.items[0].product == "hoodie"
    assert order.items[0].quantity == 3
    assert order.items[0].color == "black"
    assert order.items[1].size == "M"


def test_optional_and_null_fields_are_allowed():
    """An inquiry with no items and null delivery/payment should still validate."""
    payload = {
        "intent": "inquiry",
        "items": [],
        "delivery_area": None,
        "payment_method": None,
        "notes": "Do you have red ones?",
    }
    order = parse_order_json(json.dumps(payload))

    assert order.intent == "inquiry"
    assert order.items == []
    assert order.delivery_area is None
    assert order.payment_method is None
    assert order.notes == "Do you have red ones?"


def test_item_null_color_and_size_allowed():
    payload = {
        "intent": "new_order",
        "items": [{"product": "t-shirt", "quantity": 1, "color": None, "size": None}],
    }
    order = parse_order_json(json.dumps(payload))

    assert order.items[0].color is None
    assert order.items[0].size is None
    assert order.payment_method is None  # schema default


def test_bad_intent_rejected():
    """An intent outside the allowed set must be rejected before any DB write."""
    payload = {"intent": "refund_request", "items": []}
    with pytest.raises(ValidationError):
        parse_order_json(json.dumps(payload))


def test_zero_quantity_rejected():
    payload = {
        "intent": "new_order",
        "items": [{"product": "hoodie", "quantity": 0, "color": "black", "size": "L"}],
    }
    with pytest.raises(ValidationError):
        parse_order_json(json.dumps(payload))


def test_blank_product_rejected():
    payload = {"intent": "new_order", "items": [{"product": "   ", "quantity": 1}]}
    with pytest.raises(ValidationError):
        parse_order_json(json.dumps(payload))
