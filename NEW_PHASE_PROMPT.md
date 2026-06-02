# Reusable "Start a New Phase" Prompt

Copy everything in the box below into a fresh Claude Code session whenever you
start a new phase. Edit only the ONE line that says which phase you're on.
If you don't know the phase number, just write "the next phase" and Claude will
infer it from the roadmap.

---

```
I'm building SoukPilot AI — an AI-first operations copilot for Lebanese SMEs.
The project lives in this repo and is built phase by phase.

>>> I want to build: Phase ___  (e.g. "Phase 4 — RAG Business Q&A", or just "the next unfinished phase")

Before writing ANY code, get yourself fully oriented by reading these in order:

1. `IMPLEMENTATION_PLAN.md` — the full 2-week roadmap and scope. Find the phase
   I named above and read its goal + checklist. This is the source of truth for
   WHAT to build.

2. The most recent `PHASE*_SUMMARY.md` file — this tells you exactly what already
   exists and works. Do not rebuild anything described there.

3. These canonical files, to learn the patterns you MUST follow (do not invent
   new conventions — copy what's already there):
   - `backend/app/ai/llm.py`        (how we call the LLM)
   - `backend/app/ai/prompts.py`    (all prompts live here; one for this phase may
                                      already be written — use it, don't duplicate)
   - `backend/app/ai/extraction.py` (prompt -> LLM -> parse -> Pydantic validate)
   - `backend/app/services/invoice_service.py` (service orchestration + one DB transaction)
   - `backend/app/repositories/invoice_repo.py` (repository query pattern)
   - `backend/app/schemas/invoice.py`           (Pydantic request/response + LLM-output schemas)
   - `backend/app/api/invoices.py`              (API endpoint pattern)
   - `frontend/src/services/api.ts`             (frontend API methods — often already wired)
   - `frontend/src/pages/InvoiceUpload.tsx`     (frontend page pattern)
   - `frontend/src/components/PageShell.tsx`    (shared page wrapper)

Also note: the `backend/app/api/`, `backend/app/services/`, `backend/app/repositories/`,
and `backend/app/workers/` folders usually ALREADY contain a stub file for this
phase. Fill the stub in — don't create a parallel file.

NON-NEGOTIABLE RULES (apply to every phase):
- Calculations happen in Python code. The LLM only explains results. Never ask
  the LLM to do arithmetic.
- Validate every LLM output with a Pydantic schema BEFORE any database write.
  If validation fails, nothing is saved.
- Layering: API calls Service, Service calls Repository, Repository touches the DB.
- Run guardrails (`app/security/guardrails.py`) on user input before sending to an LLM.
- Slow work (OCR, embeddings, report generation, model training) goes to a Celery
  background task, not the request thread.
- Do NOT change the database schema unless the phase truly needs it. If it does,
  write a new Alembic migration — never edit the existing one.

ENVIRONMENT:
- Run with `docker compose up` (backend :8080, frontend :5173, Swagger at /docs).
- DB: postgres, db=`soukpilot_db`, user=`soukpilot`, pass=`soukpilot_secret`.
- Only rebuild images if you add a package to requirements.txt:
  `docker compose build backend worker beat && docker compose up -d`
- After editing Python, if a change doesn't take effect, clear stale bytecode:
  remove `__pycache__` and restart the affected container.

HOW TO WORK:
1. Confirm your understanding of the phase scope back to me in a short checklist
   BEFORE coding.
2. Build the feature following the patterns above.
3. Write unit tests for the deterministic core (parsing/validation/calculations)
   that run without OpenAI or a live DB. Run them and show me they pass.
4. Tell me exactly what to test manually in Swagger and in the frontend.
5. When I confirm it works, commit in small logical groups with clear messages
   (models/schemas, then service/repo/api, then frontend, then tests/docs).
   End each commit message with:
   Co-Authored-By: Claude <noreply@anthropic.com>
6. Finally, write a `PHASE<N>_SUMMARY.md` that explains, in plain language, what
   was built, the key files, the design decisions, and any issues we fixed — so
   the next session can pick up cleanly using this same prompt.

Start with step 1: read the files, then give me the scope checklist.
```

---

## Why this works without coming back here

- The new session reads `IMPLEMENTATION_PLAN.md` to learn **what** to build.
- It reads the latest `PHASE*_SUMMARY.md` to learn **what already exists**.
- It reads the canonical Phase 1 files to learn **how** we build things.
- The rules and workflow are baked into the prompt, so quality stays consistent.
- Step 6 makes each session leave behind a fresh summary, so the chain never breaks.

## The only thing you edit
The single line:
`>>> I want to build: Phase ___`

Everything else stays the same every time.
