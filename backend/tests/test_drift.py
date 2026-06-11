"""Tests for PSI drift detection math.

All tests are purely deterministic — no DB, no LLM, no network.
"""
import numpy as np
import pytest

from app.ai.drift import DEFAULT_BINS, PSI_ALERT, PSI_WARNING, compute_psi, psi_status


def test_identical_distributions_have_near_zero_psi():
    data = [float(i % 10) for i in range(100)]
    psi = compute_psi(data, data)
    assert psi < 0.01


def test_shifted_distribution_exceeds_alert_threshold():
    baseline = [1.0, 2.0, 3.0, 4.0, 5.0] * 20
    recent = [20.0, 25.0, 30.0, 35.0, 40.0] * 4   # completely disjoint range
    psi = compute_psi(baseline, recent)
    assert psi >= PSI_ALERT


def test_slight_perturbation_stays_stable():
    rng = np.random.default_rng(42)
    baseline = list(rng.normal(5.0, 1.0, 100))
    recent = list(rng.normal(5.2, 1.0, 20))         # tiny mean shift
    psi = compute_psi(baseline, recent)
    assert psi < PSI_ALERT


def test_empty_baseline_returns_zero():
    assert compute_psi([], [1.0, 2.0, 3.0]) == 0.0


def test_empty_recent_returns_zero():
    assert compute_psi([1.0, 2.0, 3.0], []) == 0.0


def test_both_empty_returns_zero():
    assert compute_psi([], []) == 0.0


def test_psi_status_stable():
    assert psi_status(0.0) == "stable"
    assert psi_status(0.05) == "stable"
    assert psi_status(PSI_WARNING - 0.001) == "stable"


def test_psi_status_warning():
    assert psi_status(PSI_WARNING) == "warning"
    assert psi_status(0.15) == "warning"
    assert psi_status(PSI_ALERT - 0.001) == "warning"


def test_psi_status_alert():
    assert psi_status(PSI_ALERT) == "alert"
    assert psi_status(0.5) == "alert"


def test_psi_is_nonnegative():
    rng = np.random.default_rng(7)
    for _ in range(10):
        b = list(rng.exponential(5, 50))
        r = list(rng.exponential(7, 15))
        assert compute_psi(b, r) >= 0.0


def test_psi_result_is_rounded_to_4_decimals():
    data = [float(i) for i in range(1, 51)]
    psi = compute_psi(data, data[:10])
    assert psi == round(psi, 4)
