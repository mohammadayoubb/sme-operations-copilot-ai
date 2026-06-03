# SoukPilot AI — Phase 5 Summary

**Features:** Weekly Business Report + Guardrails Tests
**Status:** ✅ Complete, tested (Swagger + frontend), committed to `main`
**Date:** 2026-06-03

---

## 1. What Phase 5 Does (in plain words)

The owner can click **"Generate Report Now"** and get a full weekly business
summary — sales vs. last week, profit trend, top-selling products, reorder
risks, and an AI-written narrative that ties it all together.

The report also runs **automatically every Monday at 8 AM** via the Celery
beat scheduler, so the owner always has a fresh summary waiting at the start
of the week.

The core rule: **all the numbers are computed in Python**. The LLM reads the
already-computed data and writes 4–6 sentences of business commentary. It never
does arithmetic.

---

## 2. Flow

```
Owner clicks Generate (Frontend)
        │  POST /api/reports/generate
        ▼
  report_service.generate(db)
    1. build_report_data() — pure Python aggregation:
         • sales & profit this week vs last week (with % change)
         • top 5 products by revenue
         • low-stock risks (reuses forecasting model)
         • supplier price changes from invoices
         • most & least profitable products (margin_pct formula)
    2. _narrate(data) — LLM writes the narrative (WEEKLY_REPORT_PROMPT)
    3. report_repo.create_report() — persisted to the reports table
        ▼
  { id, period, summary_text, data_json, created_at }
        ▼
  Frontend: narrative card + metric cards + top products + reorder risks

Also runs on schedule:
  Celery beat → generate_weekly_report task (every Monday 08:00 Asia/Beirut)
```

---

## 3. What the Report Contains

| Section | Source | How it's computed |
|---|---|---|
| Sales this week / last week / % change | `sales` table | Python sum + `pct_change()` |
| Profit this week / last week / % change | `sales` + product cost prices | `rev_profit()` — revenue minus cost×qty |
| Top 5 products by revenue | `sales` table | Python sort-by-sum |
| Reorder risks | Forecasting model | `forecasting_service.get_reorder_recommendations()` |
| Supplier price changes | `invoice_items.price_change_pct` | DB query over the week's invoices |
| Most / least profitable products | `products.cost_price` + `selling_price` | `margin_pct()` formula |
| AI narrative | All of the above, as a JSON blob | `WEEKLY_REPORT_PROMPT` → `complete_text()` |

**Live output from the first generated report:**
- Sales: **$278.50** this week vs $326.50 last (−14.7%)
- Profit: **$118.67** vs $139.55 (−15.0%)
- Top product: **Nutella 400g** ($115.50 revenue, 21 units)
- Risks: Water 1.5L, Nutella, Lays flagged for reorder
- AI narrative correctly cited every number and gave a restock recommendation

---

## 4. Files

| File | Purpose |
|------|---------|
| `backend/app/models/report.py` | `Report` ORM model (maps the existing `reports` table) |
| `backend/app/models/__init__.py` | Registers `Report` |
| `backend/app/repositories/report_repo.py` | `create_report`, `list_reports`, `get_latest`, `get` |
| `backend/app/schemas/report.py` | `ReportOut`, `ReportListItem` |
| `backend/app/services/report_service.py` | Python aggregation helpers + LLM narration + orchestration |
| `backend/app/api/reports.py` | `GET /`, `GET /latest`, `POST /generate` |
| `backend/app/workers/report_tasks.py` | `generate_weekly_report` Celery task |
| `frontend/src/pages/Reports.tsx` | Generate button, narrative card, metric cards, history |
| `backend/tests/test_reports.py` | 7 pure-Python aggregation tests |
| `backend/tests/test_guardrails.py` | 13 guardrails tests (PII + injection) |
| `backend/tests/conftest.py` | Dummy env bootstrap so host tests collect without a real `.env` |

---

## 5. API Endpoints

| Method & Path | Purpose |
|---|---|
| `GET /api/reports/` | List all generated reports (newest first) |
| `GET /api/reports/latest` | Full latest report (narrative + data_json) — `404` if none yet |
| `POST /api/reports/generate` | Aggregate + narrate + persist now (synchronous) |

---

## 6. Guardrails Tests (also Phase 5)

The guardrail code was built in Phase 1 but never had its own test file. Phase 5
adds **`test_guardrails.py`** covering:

- **PII redaction** — phone numbers (`+961 70 123 456`) and emails
  (`owner@souk.com.lb`) are replaced; clean text is left untouched.
- **Injection detection** — 6 parameterised attack strings (all caught) and 3
  clean business inputs (all passed through).
- **`is_safe_input` contract** — returns `(True, None)` for clean, `(False, reason)`
  for injections.

---

## 7. Tests

### New in Phase 5 — 20 tests
```bash
cd backend && python -m pytest tests/test_reports.py tests/test_guardrails.py -q
# 7 report math + 13 guardrails = 20 passed
```

**`test_reports.py`** (pure Python, no LLM/DB):
| Test | What it checks |
|---|---|
| `test_pct_change_normal` | 20% up, −20% down |
| `test_pct_change_no_baseline_returns_none` | zero division → `None` |
| `test_rev_profit_basic` | Pepsi + Lays revenue and profit |
| `test_rev_profit_empty` | no sales → (0, 0) |
| `test_rev_profit_unknown_product_costs_zero` | missing cost_map entry → cost = 0 |
| `test_margin_pct` | (7, 10) → 30% |
| `test_margin_pct_zero_or_missing_is_none` | zero sell / None cost → None |

### Running total — 51 tests, all passing
```
25 (Phases 1–3) + 6 RAG (Phase 4) + 20 (Phase 5) = 51 passed
```

---

## 8. The `conftest.py` Fix

Running the test suite on a host without a real `.env` caused collection to fail
with a Pydantic validation error on `DATABASE_URL` / `OPENAI_API_KEY` (because
`report_service.py` imports the config at module load time). Added
`backend/tests/conftest.py` which sets dummy defaults via `os.environ.setdefault`
before any tests collect. Docker containers have real values and are unaffected.
This also incidentally fixed how the Phase 4 RAG and Phase 3 forecasting tests
were collecting.

---

## 9. Design Decisions (the "why")

- **Sync endpoint for generate.** Like the forecasting retrain, running synchronously
  gives immediate feedback in Swagger and the frontend. The Celery task exists
  separately for the scheduled Monday run.
- **Reuses the forecasting service.** Low-stock risks come from
  `forecasting_service.get_reorder_recommendations()` — no duplicated logic.
- **`pct_change` returns `None` when previous = 0.** Displaying "∞%" or "N/A" is
  less useful than the frontend just showing "— no prior week", which is what the
  `ChangeBadge` component does.

---

## 10. Commits (on `main`)

```
test(reports): guardrails + report aggregation tests, conftest env bootstrap
feat(reports): build Weekly Reports page
feat(reports): weekly report service, API, and Celery task
feat(reports): add Report model, repo, and schemas (Phase 5)
docs(phase4): fix test count (37 -> 31)
```

---

## 11. Where the Project Stands

All core MVP features are now complete:

| Phase | Feature | Status |
|---|---|---|
| 1 | Invoice OCR + LLM extraction | ✅ |
| 2 | WhatsApp/Instagram order extraction | ✅ |
| 3A | Pricing / Profit Advisor | ✅ |
| 3B | Inventory Forecasting (ML) | ✅ |
| 4 | RAG Business Q&A | ✅ |
| 5 | Weekly Business Report + Guardrails tests | ✅ |
| — | Voice Assistant (stretch) | Stubbed |
| — | Multi-tenancy | Deferred post-project |

Remaining stubbed features: **Voice Assistant** (`/api/voice`, Whisper STT +
OpenAI TTS) — the highest-impact remaining stretch goal.
After the full feature build, the project plan also calls for documentation
(`README.md`, `ARCHITECTURE.md`, `AI_FEATURES.md`, `EVALS.md`, `SECURITY.md`,
`RUNBOOK.md`) and a demo dry run.
