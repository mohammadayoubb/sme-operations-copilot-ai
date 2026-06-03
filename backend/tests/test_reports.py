"""Tests for the weekly-report aggregation maths (pure Python, no LLM/DB).

These cover the deterministic helpers the report is built from — the LLM only
narrates the numbers, so the numbers themselves must be right.
"""
import pytest

from app.services.report_service import margin_pct, pct_change, rev_profit


def test_pct_change_normal():
    assert pct_change(120, 100) == 20.0
    assert pct_change(80, 100) == -20.0


def test_pct_change_no_baseline_returns_none():
    # avoid divide-by-zero when there was no prior-week activity
    assert pct_change(50, 0) is None


def test_rev_profit_basic():
    # rows: (product_id, quantity, total); cost_map: product_id -> unit cost
    rows = [(1, 10, 7.50), (2, 5, 6.25)]   # Pepsi: 10 @0.75, Lays: 5 @1.25
    cost_map = {1: 0.42, 2: 0.80}
    revenue, profit = rev_profit(rows, cost_map)
    assert revenue == pytest.approx(13.75)          # 7.50 + 6.25
    # profit = 13.75 - (0.42*10 + 0.80*5) = 13.75 - 8.20
    assert profit == pytest.approx(5.55)


def test_rev_profit_empty():
    assert rev_profit([], {}) == (0.0, 0.0)


def test_rev_profit_unknown_product_costs_zero():
    revenue, profit = rev_profit([(99, 3, 30.0)], {})  # no cost on record
    assert revenue == pytest.approx(30.0)
    assert profit == pytest.approx(30.0)


def test_margin_pct():
    assert margin_pct(7, 10) == 30.0


def test_margin_pct_zero_or_missing_is_none():
    assert margin_pct(5, 0) is None       # zero selling price
    assert margin_pct(None, 10) is None   # unknown cost
