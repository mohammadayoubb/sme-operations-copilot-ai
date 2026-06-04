# SoukPilot AI — Security

## Overview

SoukPilot AI is a single-owner MVP. The security model prioritises AI-specific
risks (prompt injection, unvalidated LLM output, data leakage via logs) over
traditional auth hardening. Traditional auth (JWT, OAuth) is explicitly
de-scoped for the capstone — the API runs in a trusted Docker network.

---

## Threat Model

| Threat | Risk | Mitigation |
|---|---|---|
| Prompt injection via customer messages | High | Pattern detection before any LLM call |
| Prompt injection inside uploaded invoices | Medium | Detected and flagged (not blocked) — logged as security alert |
| LLM returns malformed/unsafe output | High | Pydantic validation before every DB write |
| PII in application logs | Medium | `redact_pii()` applied before logging |
| Malicious file upload | Medium | MIME type + size validation; no execution of uploaded files |
| Unauthenticated API access | Low (single-owner) | No auth layer in MVP scope |

---

## Guardrails (`app/security/guardrails.py`)

### 1. Prompt Injection Detection

Applied to **every user-supplied string** before it reaches any LLM:
- Order messages (`POST /api/orders/extract`)
- QA questions (`POST /api/qa/ask`, `POST /api/qa/ask/stream`)
- Agent chat messages (`POST /api/agent/chat`, `POST /api/agent/chat/stream`)
- Voice transcripts (`POST /api/voice/command`, routed to agent)

```python
INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all instructions",
    r"forget everything",
    r"you are now",
    r"new persona",
    r"system prompt",
    r"reveal your instructions",
    r"disregard.*instructions",
    r"act as (?!a business)",
    r"jailbreak",
]

def detect_injection(text: str) -> bool:
    lower = text.lower()
    return any(re.search(p, lower) for p in INJECTION_PATTERNS)
```

A positive detection returns HTTP 400 to the client. The request never
reaches the LLM.

**Invoice uploads** are handled differently: the injected text appears
*inside a document* that the LLM processes as data. We detect and log it
(creating an `Alert` row) but do not block it — a real invoice with unusual
wording should still be processed. The alert lets the owner know the document
may contain adversarial content.

### 2. PII Redaction

Applied to **log entries** before writing. Stored user messages (in
`orders.raw_message`, `invoices.raw_ocr_text`) keep the original text for
business traceability, but logs never expose raw PII.

```python
PHONE_RE = re.compile(r"\+?[\d\s\-\(\)]{7,15}")
EMAIL_RE = re.compile(r"[\w\.\-]+@[\w\.\-]+\.\w+")

def redact_pii(text: str) -> str:
    text = PHONE_RE.sub("[PHONE REDACTED]", text)
    text = EMAIL_RE.sub("[EMAIL REDACTED]", text)
    return text
```

### 3. LLM Output Validation

**Every JSON response from the LLM is validated by a Pydantic schema before
any database write. No exceptions.**

```
complete_json(prompt)          ← raw string from OpenAI
    → json.loads(raw)          ← JSONDecodeError if malformed
    → ExtractedInvoice.model_validate(data)   ← ValidationError if schema fails
```

If either error is raised:
- The Celery task catches it and marks the invoice `failed`
- The DB transaction is rolled back
- A structured error is returned to the API caller
- The raw LLM output is logged for debugging

This guarantees: **no unvalidated data from an LLM ever reaches the database**.

---

## File Upload Security

`POST /api/invoices/upload`:
1. Extension whitelist check: `{.png, .jpg, .jpeg, .bmp, .tiff, .webp, .pdf}`
2. Size limit: 20 MB (configurable via `MAX_UPLOAD_SIZE_MB`)
3. Files saved to a dedicated upload directory (`/app/uploads/`) with a
   UUID-based filename — the original filename is never used on disk
4. Files are never executed; they are read as bytes and passed to Vision API

`POST /api/voice/transcribe`:
1. Extension whitelist: `{.mp3, .mp4, .mpeg, .mpga, .m4a, .wav, .webm, .ogg, .flac}`
2. Size limit: 25 MB (Whisper API limit)

`POST /api/voice/speak`:
1. Accepts only `{"text": "..."}` — no file upload
2. Input length capped at 4 096 characters before reaching the TTS API
3. The text sent to TTS is the agent's own output, not raw user input, so it
   has already passed through the agent's tool loop and is not an injection
   vector. No additional guardrail scan is applied to TTS input.

---

## The No-LLM-Arithmetic Rule

Every numeric result in the system (margins, profits, sales totals,
days-to-stockout) is computed in Python before the LLM ever sees it. The LLM
is only given pre-computed numbers and asked to write an explanation.

**Why this matters:** LLMs make arithmetic errors, especially with floating
point. A system that lets the LLM compute a profit margin and then stores that
number in the DB has no correctness guarantee. By computing first and explaining
second, every number in SoukPilot AI can be verified independently of any LLM
call.

---

## Infrastructure Security

- All services communicate inside a Docker Compose network; only ports 8080
  (backend) and 5173 (frontend) are exposed to the host.
- `OPENAI_API_KEY` and `DATABASE_URL` are read from `.env` at startup; never
  hardcoded or committed.
- `.env` is in `.gitignore`.
- CORS is configured to allow only `localhost:5173` and `localhost:3000` in
  development (`ALLOWED_ORIGINS` env var).

---

## Agentic Tool-Call Security

The agent (`agent_service.py`) runs a GPT-4o tool-calling loop. Security
properties:

- **Read-only by default**: six of seven tools only SELECT from the database.
  No data is mutated.
- **One write tool** (`create_order`): routes through the existing
  `order_service` pipeline — guardrail check → LLM extraction → Pydantic
  validation → transaction. The same safety layer that protects the Orders
  page applies here.
- **Iteration cap**: the loop exits after 8 iterations. A model that loops
  indefinitely (e.g. due to a confused tool call) cannot run forever.
- **System prompt scoping**: the agent system prompt restricts the model to
  business data retrieval. It cannot call arbitrary code, access the filesystem,
  or invoke any endpoint outside the tool list.

---

## Known Limitations (MVP scope)

- **No authentication**: the API has no JWT, API key, or session layer. Suitable
  for a single-owner local deployment; would require auth before any
  multi-user or cloud deployment.
- **No rate limiting**: endpoints are not rate-limited in the current MVP.
- **No HTTPS**: runs over plain HTTP in Docker Compose. A production deployment
  would add TLS termination (nginx/Caddy).
- **Regex-based injection detection**: covers common patterns but can be bypassed
  by sufficiently creative attackers. A more robust approach would use an LLM
  classifier as a second layer (planned for post-MVP).
