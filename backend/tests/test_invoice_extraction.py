"""Tests for the invoice extraction parsing/validation core.

These cover the deterministic layer (`parse_invoice_json`) without needing
OpenAI, EasyOCR, or a database — exactly the part we must trust before any
DB write happens.
"""
import json

import pytest
from pydantic import ValidationError

from app.ai.extraction import parse_invoice_json
from app.schemas.invoice import ExtractedInvoice


VALID_PAYLOAD = {
    "supplier": "ABC Foods",
    "date": "2026-05-27",
    "items": [
        {"name": "Pepsi 330ml", "quantity": 48, "unit_price": 0.42, "total": 20.16},
        {"name": "Lays Chips", "quantity": 24, "unit_price": 0.80, "total": 19.20},
    ],
    "invoice_total": 39.36,
    "currency": "USD",
}


def test_parses_valid_invoice_json():
    invoice = parse_invoice_json(json.dumps(VALID_PAYLOAD))

    assert isinstance(invoice, ExtractedInvoice)
    assert invoice.supplier == "ABC Foods"
    assert invoice.currency == "USD"
    assert len(invoice.items) == 2
    assert invoice.items[0].name == "Pepsi 330ml"
    assert invoice.items[0].quantity == 48
    assert invoice.items[0].unit_price == 0.42
    assert invoice.invoice_total == pytest.approx(39.36)


def test_optional_and_null_fields_are_allowed():
    """Missing supplier/date/total and a null item total should still validate."""
    payload = {
        "supplier": None,
        "date": None,
        "items": [{"name": "Water 1.5L", "quantity": 12, "unit_price": 0.25, "total": None}],
        "invoice_total": None,
    }
    invoice = parse_invoice_json(json.dumps(payload))

    assert invoice.supplier is None
    assert invoice.date is None
    assert invoice.invoice_total is None
    assert invoice.items[0].total is None
    assert invoice.currency == "USD"  # schema default


def test_malformed_item_raises_validation_error():
    """An item missing required quantity must be rejected before any DB write."""
    payload = {
        "supplier": "Bad Co",
        "items": [{"name": "Mystery Box", "unit_price": 5.0}],  # no quantity
    }
    with pytest.raises(ValidationError):
        parse_invoice_json(json.dumps(payload))


def test_empty_items_list_rejected():
    payload = {"supplier": "Empty Co", "items": []}
    with pytest.raises(ValidationError):
        parse_invoice_json(json.dumps(payload))


def test_blank_item_name_rejected():
    payload = {"items": [{"name": "   ", "quantity": 1, "unit_price": 1.0}]}
    with pytest.raises(ValidationError):
        parse_invoice_json(json.dumps(payload))
