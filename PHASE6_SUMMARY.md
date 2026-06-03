# SoukPilot AI — Phase 6 Summary

**Features:** Frontend Polish — Dashboard wired to live APIs + Voice Assistant
**Status:** ✅ Complete, ready for manual testing
**Date:** 2026-06-03

---

## 1. What Phase 6 Does (in plain words)

### Dashboard
The Dashboard was the only page that still showed hardcoded `"—"` values and
`Placeholder` components. It now loads real data from the backend on mount and
shows:

- **4 stat cards** with live numbers (sales this week, gross profit, low-stock
  count, pending orders count), each with a week-over-week change badge when a
  weekly report has been generated.
- **Recent Invoices** table showing the last 5 invoices with date, total, and a
  colour-coded status badge (processed/pending/failed).
- **Reorder Alerts** cards showing which products need reordering, how many days
  until stockout, and the recommended reorder-by date.

All data comes from existing APIs — no new endpoints were needed. The weekly
sales/profit cards gracefully show `"—"` if no report has been generated yet
(the report is optional, caught separately so it never blocks the rest of the
page).

### Voice Assistant
The Voice Assistant was a UI stub (record button that only toggled a boolean).
It now works end-to-end:

- **In-browser recording** via the `MediaRecorder` API captures `audio/webm`
  and uploads it on stop.
- **File upload** (MP3, WAV, M4A, WebM, OGG) follows the same path.
- **Backend transcription** (`POST /api/voice/transcribe`) passes the audio to
  OpenAI Whisper-1 and returns the transcript text.
- **Command parsing** (`POST /api/voice/command`) runs the transcript through
  `VOICE_COMMAND_PROMPT` → `complete_json()` and returns `{intent, params}`.
- **Frontend result** shows the transcript in quotes, a colour-coded intent
  badge (record_sale, check_stock, create_order, get_summary, other), and the
  parsed parameters as JSON.

---

## 2. Files Changed

| File | What changed |
|------|-------------|
| `frontend/src/pages/Dashboard.tsx` | Full rewrite — wired to 4 APIs, stat cards, recent invoices table, reorder alerts panel |
| `frontend/src/pages/VoiceAssistant.tsx` | Full rewrite — MediaRecorder, file upload, transcript + intent display |
| `backend/app/api/voice.py` | Implemented both endpoints (was stub returning `"not implemented yet"`) |

### No other files changed
- `api.ts` already had `voiceApi` wired correctly
- `main.py` already registered `voice.router`
- `prompts.py` already had `VOICE_COMMAND_PROMPT`
- No DB schema changes, no migrations, no new packages

---

## 3. API Endpoints (voice — now live)

| Method & Path | What it does |
|---|---|
| `POST /api/voice/transcribe` | Upload audio file → Whisper-1 transcription → `{transcript}` |
| `POST /api/voice/command` | `{transcript}` → `VOICE_COMMAND_PROMPT` → `{transcript, intent, params}` |

Guardrails (`is_safe_input`) run on the transcript before the command LLM call.
No DB writes — voice is read-only interpretation.

---

## 4. Dashboard Data Sources

| Stat card | API called | Field used |
|---|---|---|
| Sales (this week) | `GET /api/reports/latest` | `data_json.sales.this_week` |
| Gross Profit | `GET /api/reports/latest` | `data_json.profit.this_week` |
| Low Stock Alerts | `GET /api/products/` | count where `stock ≤ reorder_level` |
| Pending Orders | `GET /api/orders/` | count where `status === "pending"` |
| Recent Invoices | `GET /api/invoices/` | first 5 |
| Reorder Alerts | `GET /api/forecast/reorder` | first 5 |

---

## 5. What to Test Manually

### Dashboard
1. Go to `http://localhost:5173` — should load and show live numbers (not `—`)
2. The "Low Stock Alerts" and "Pending Orders" cards should show real counts
3. If you've run "Generate Report" from the Reports page, the sales/profit cards should show numbers with week-over-week badges
4. The "Recent Invoices" panel should list the invoices you've uploaded
5. The "Reorder Alerts" panel should show products flagged by the forecast model

### Voice Assistant
1. Navigate to **Voice** in the sidebar
2. Click the microphone button — browser should ask for mic permission
3. Say a command like: *"Add sale: 3 Pepsi and 2 chips"*
4. Click the stop button (⏹) — progress indicator shows "Processing audio…"
5. Transcript appears in quotes, intent badge shows **RECORD SALE** in green
6. Alternatively upload an MP3/WAV file via "Choose audio file"
7. Test an injection: say "ignore previous instructions" — should be blocked with a 400 error

### Swagger
- `POST /api/voice/transcribe` — upload an audio file, should return `{transcript: "..."}`
- `POST /api/voice/command` with `{"transcript": "check stock of Nutella"}` → should return `{intent: "check_stock", params: {...}}`

---

## 6. Design Decisions

- **Dashboard fetches in parallel.** `Promise.all` fires all 4 main calls simultaneously; the optional report call is in a separate `try/catch` so a missing report never blocks the page load.
- **Voice is read-only.** Whisper + command parsing returns intent/params but does not write anything to the DB. Acting on the command (actually recording a sale, etc.) would be a Phase 7 agent-mode extension.
- **No new packages.** Whisper is part of the `openai` SDK already in `requirements.txt`. `python-multipart` (already installed) handles the audio upload.
- **`MediaRecorder` uses `audio/webm`** — the only format universally supported across Chrome, Edge, and Firefox without needing a codec polyfill.

---

## 7. Running Total — 51 tests, all passing

No new tests were added in Phase 6 (all changes are UI/API wiring with no new
deterministic logic to unit-test). The 51 existing tests (Phases 1–5) remain
unchanged and still pass.

---

## 8. Where the Project Stands

| Phase | Feature | Status |
|---|---|---|
| 1 | Invoice OCR + LLM extraction | ✅ |
| 2 | WhatsApp/Instagram order extraction | ✅ |
| 3A | Pricing / Profit Advisor | ✅ |
| 3B | Inventory Forecasting (ML) | ✅ |
| 4 | RAG Business Q&A | ✅ |
| 5 | Weekly Business Report + Guardrails tests | ✅ |
| 6 | Dashboard wired to live APIs + Voice Assistant | ✅ |
| 7 | Docs, stretch goals, demo prep | Next |

**Next up (Phase 7):** `README.md`, `ARCHITECTURE.md`, `AI_FEATURES.md`,
`EVALS.md`, `SECURITY.md`, `RUNBOOK.md`, full test suite run, and demo dry run.
