"""CI Eval Gate -- Week 6 eval-driven development.

Parses the pytest JUnit XML report and enforces thresholds:
  - Guardrail coverage: 100%
  - Extraction accuracy: 100%
  - Overall pass rate: >= 95%

Usage: python tests/eval_gate.py test-results.xml
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

GUARDRAIL_KEYWORDS = {
    "test_detects_injection_attempts",
    "test_clean_inputs_pass",
    "test_redacts_phone_number",
    "test_redacts_email",
    "test_clean_text_is_left_alone",
    "test_is_safe_input_contract",
}

EXTRACTION_KEYWORDS = {
    "test_parses_valid_invoice_json",
    "test_malformed_item_raises_validation_error",
    "test_empty_items_list_rejected",
    "test_blank_item_name_rejected",
    "test_optional_and_null_fields_are_allowed",
}

FORECASTING_EVAL_KEYWORDS = {
    "test_train_and_select_returns_valid_artifact_and_metrics",
    "test_predict_daily_demand_is_nonnegative_float",
    "test_forecast_product_recommends_reorder_when_stock_low",
    "test_save_and_load_roundtrip",
}

DRIFT_EVAL_KEYWORDS = {
    "test_psi_status_stable",
    "test_psi_status_warning",
    "test_psi_status_alert",
    "test_shifted_distribution_exceeds_alert_threshold",
    "test_identical_distributions_have_near_zero_psi",
}

OVERALL_PASS_THRESHOLD = 0.95


def _collect_failures(xml_path: str) -> tuple[set[str], int, int]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
    total = sum(int(s.get("tests", 0)) for s in suites)
    n_failed = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
    failed_names: set[str] = set()
    for tc in root.iter("testcase"):
        if tc.find("failure") is not None or tc.find("error") is not None:
            failed_names.add(tc.get("name", ""))
    return failed_names, total, n_failed


def run_gate(xml_path: str) -> bool:
    failures, total, n_failed = _collect_failures(xml_path)
    passed = total - n_failed
    pass_rate = passed / total if total > 0 else 0.0

    sep = "=" * 56
    print(f"\n{sep}\n  SOUKPILOT AI -- EVAL GATE REPORT\n{sep}")
    print(f"  Total : {total} | Passed : {passed} | Failed : {n_failed}")
    print(f"  Rate  : {pass_rate:.1%}\n{sep}")

    ok = True
    groups = [
        ("Guardrail coverage   ", GUARDRAIL_KEYWORDS),
        ("Extraction accuracy  ", EXTRACTION_KEYWORDS),
        ("Forecasting eval     ", FORECASTING_EVAL_KEYWORDS),
        ("Drift monitoring eval", DRIFT_EVAL_KEYWORDS),
    ]

    for label, keywords in groups:
        gf = keywords & failures
        status = f"FAIL  ({', '.join(sorted(gf))})" if gf else "PASS"
        print(f"  {label} : {status}")
        if gf:
            ok = False

    rate_ok = pass_rate >= OVERALL_PASS_THRESHOLD
    print(f"  Overall pass rate    : {'PASS' if rate_ok else 'FAIL'} ({pass_rate:.1%})")
    if not rate_ok:
        ok = False

    verdict = "[GATE PASSED] All thresholds met." if ok else "[GATE FAILED] One or more thresholds not met."
    print(f"\n{sep}\n  {verdict}\n{sep}\n")
    return ok


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python eval_gate.py <junit-xml-path>")
        sys.exit(1)
    xml_path = sys.argv[1]
    if not Path(xml_path).exists():
        print(f"ERROR: report not found at {xml_path}")
        sys.exit(1)
    sys.exit(0 if run_gate(xml_path) else 1)


if __name__ == "__main__":
    main()
