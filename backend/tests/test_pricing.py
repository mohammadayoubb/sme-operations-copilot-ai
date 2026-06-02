"""Tests for the pure-Python pricing math (`calculate_margin`).

This is the part that must be exactly right — the LLM only explains these
numbers, it never computes them. No OpenAI or DB needed here.
"""
import pytest

from app.services.pricing_service import calculate_margin


def test_handoff_example():
    """cost=7, sell=10, delivery=1, packaging=0.5 → profit 1.5, margin 15%, 25%-price 11.33."""
    r = calculate_margin(cost=7, sell=10, delivery=1, packaging=0.5)
    assert r["total_cost"] == pytest.approx(8.5)
    assert r["profit"] == pytest.approx(1.5)
    assert r["margin_pct"] == pytest.approx(15.0)
    assert r["sell_for_25pct"] == pytest.approx(11.33, abs=0.01)


def test_no_extra_costs():
    r = calculate_margin(cost=8, sell=10)
    assert r["total_cost"] == pytest.approx(8.0)
    assert r["profit"] == pytest.approx(2.0)
    assert r["margin_pct"] == pytest.approx(20.0)


def test_zero_cost():
    """Zero cost (and no extras) → 100% margin, and a 25% price of 0."""
    r = calculate_margin(cost=0, sell=5)
    assert r["total_cost"] == pytest.approx(0.0)
    assert r["profit"] == pytest.approx(5.0)
    assert r["margin_pct"] == pytest.approx(100.0)
    assert r["sell_for_25pct"] == pytest.approx(0.0)


def test_zero_sell_does_not_divide_by_zero():
    """A zero selling price must not blow up; margin is reported as 0%."""
    r = calculate_margin(cost=5, sell=0, delivery=1, packaging=0)
    assert r["total_cost"] == pytest.approx(6.0)
    assert r["profit"] == pytest.approx(-6.0)
    assert r["margin_pct"] == 0.0
    assert r["sell_for_25pct"] == pytest.approx(8.0)  # 6 / 0.75


def test_negative_margin():
    """Selling below total cost → negative profit and negative margin."""
    r = calculate_margin(cost=10, sell=8, delivery=2, packaging=1)
    assert r["total_cost"] == pytest.approx(13.0)
    assert r["profit"] == pytest.approx(-5.0)
    assert r["margin_pct"] == pytest.approx(-62.5)  # -5 / 8 * 100


def test_sell_for_25pct_actually_yields_25pct():
    """Feeding the recommended price back in should produce ~25% margin."""
    base = calculate_margin(cost=7, sell=10, delivery=1, packaging=0.5)
    recomputed = calculate_margin(
        cost=7, sell=base["sell_for_25pct"], delivery=1, packaging=0.5
    )
    assert recomputed["margin_pct"] == pytest.approx(25.0, abs=0.05)
