# SoukPilot AI — New Features (Post-Stretch)

## Overview

Two advanced features added after the stretch phase, designed to make the demo
stand out and demonstrate production-level thinking.

---

## Feature 1: Human-in-the-loop Review Queue with Confidence Scores

### What it does

After the LLM extracts an order, a deterministic confidence scorer (pure Python,
no LLM) evaluates the extraction quality and assigns a score from 0.0 to 1.0.

- **High confidence (≥ 0.85):** order is auto-committed, inventory is deducted immediately
- **Low confidence (< 0.85):** order is parked in a review queue — no inventory is touched until a human approves or rejects it

This quietly demonstrates production thinking: the system knows what it doesn't
know, and routes uncertainty to a human instead of blindly committing bad data.

### How confidence is scored

All logic is in `backend/app/ai/confidence.py` — deterministic, testable, no LLM involved.

| Condition | Deduction |
|---|---|
| No items extracted at all | Returns 0.20 immediately |
| Missing delivery area | −0.12 |
| Missing payment method | −0.08 |
| More than 6 items (suspicious) | −0.10 |
| Product name shorter than 2 chars | −0.15 per item |

Threshold is set to **0.85** (demo-friendly — any order missing delivery or
payment routes to review).

### What you see in the UI

- Confidence badge on every order: green (≥ 85%), amber (50–85%), red (< 50%)
- Amber **"Human Review Queue"** panel appears on the Orders page when items are pending
- Each queued order shows: raw message, extracted fields, confidence badge, **Approve & Commit** / **Reject** buttons
- Approving deducts inventory and moves the order to pending
- Rejecting cancels the order with no inventory change
- Orders in the recent list show "Review Queue" instead of a status dropdown while pending

### New API endpoints

| Method | Endpoint | What it does |
|---|---|---|
| `GET` | `/api/orders/review-queue` | List all queued orders, lowest confidence first |
| `POST` | `/api/orders/{id}/approve` | Approve: deduct inventory, set status to pending |
| `POST` | `/api/orders/{id}/reject` | Reject: cancel order, no inventory change |

### New / changed files

| File | Change |
|---|---|
| `backend/app/ai/confidence.py` | New — confidence scoring logic |
| `backend/alembic/versions/0003_order_review_queue.py` | New — adds `confidence_score` and `review_status` columns to orders |
| `backend/app/models/order.py` | Added `confidence_score`, `review_status` columns |
| `backend/app/schemas/order.py` | Exposed new fields in all response schemas |
| `backend/app/services/order_service.py` | Integrates confidence scoring; added `approve_order()`, `reject_order()` |
| `backend/app/repositories/order_repo.py` | Added `list_review_queue()`, new fields in `create_order()` |
| `backend/app/api/orders.py` | Three new endpoints: review-queue, approve, reject |
| `frontend/src/services/api.ts` | Added `reviewQueue()`, `approve()`, `reject()` calls |
| `frontend/src/pages/Orders.tsx` | Review queue panel, confidence badges, approve/reject buttons |

### How to run the migration

The two new columns must exist in the database before the backend will work:

```bash
docker-compose exec backend alembic upgrade head
```

---

### How to test

#### Test 1 — Trigger the review queue

Paste this into the Orders page (no delivery area, no payment method → scores 0.80 → below 0.85 threshold):

```
Salam bddi 3 black hoodies w 2 white ones size M
```

Expected result:
- Amber review queue panel appears
- Confidence badge shows ~80%
- No inventory deducted yet

#### Test 2 — Approve from the queue

Click **Approve & Commit** on the queued order.

Expected result:
- Order disappears from the queue
- Inventory is deducted
- Order status changes to `pending`

#### Test 3 — Reject from the queue

Paste the same message again, then click **Reject**.

Expected result:
- Order disappears from the queue
- Inventory unchanged
- Order status set to `cancelled`

#### Test 4 — Auto-approved high-confidence order

Paste a complete message:

```
Salam bddi 3 black hoodies size L, delivery to Hamra, cash on delivery
```

Expected result:
- No review queue — order goes straight to `pending`
- Confidence badge shows 100% (green)
- Inventory deducted immediately

---

## Feature 2: Real WhatsApp Webhook (Twilio)

### What it does

Twilio receives WhatsApp messages on the sandbox number and forwards them to the
backend via HTTP POST. The backend extracts the order exactly like the manual
paste flow, then sends a reply back to the sender via TwiML.

This means during a live demo, someone in the audience can send a WhatsApp
message and watch the order appear in the Orders page in real time — no
copy-pasting involved.

### How it works

1. Sender writes a WhatsApp message to the Twilio sandbox number
2. Twilio POSTs form data (`From`, `Body`) to `POST /api/webhooks/whatsapp`
3. Backend runs guardrail check → LLM extraction → confidence scoring
4. Order is created (auto-approved or queued based on confidence)
5. Backend returns TwiML XML with a confirmation reply
6. Twilio delivers the reply back to the sender's WhatsApp

### Signature validation

The webhook validates `X-Twilio-Signature` using HMAC-SHA1 against `TWILIO_AUTH_TOKEN`.
If `TWILIO_AUTH_TOKEN` is blank in `.env`, validation is skipped — safe for local
dev and demo. Set the token in production to lock it down.

No external dependencies — validation uses Python stdlib `hmac` + `hashlib`.

### New / changed files

| File | Change |
|---|---|
| `backend/app/api/webhooks.py` | New — WhatsApp webhook handler + TwiML response + signature validation |
| `backend/app/core/config.py` | Added `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` |
| `backend/app/main.py` | Registered webhook router |
| `.env.example` | Documented Twilio env vars + ngrok instructions |

### Environment variables

Add these to your `.env` (all optional for dev — leave blank to skip signature validation):

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

---

### How to set up (one time)

#### Step 1 — Twilio sandbox

1. Create a free account at [twilio.com](https://twilio.com)
2. Go to **Messaging → Try it out → Send a WhatsApp message**
3. From your phone, send `join <your-sandbox-keyword>` to `+1 415 523 8886` on WhatsApp
4. Wait for the "You are now connected" reply

#### Step 2 — ngrok (expose local backend)

ngrok is installed at `C:\Users\user\AppData\Local\ngrok-latest\ngrok.exe`.

Run it (in a terminal that stays open during the demo):

```powershell
& "C:\Users\user\AppData\Local\ngrok-latest\ngrok.exe" http 8080
```

Copy the `https://...ngrok-free.dev` URL from the output.

To get the URL programmatically:
```powershell
(Invoke-RestMethod http://localhost:4040/api/tunnels).tunnels[0].public_url
```

#### Step 3 — Set webhook in Twilio

Go to **Messaging → Try it out → Send a WhatsApp message → Sandbox Settings**

Set **"When a message comes in"** to:
```
https://<your-ngrok-url>/api/webhooks/whatsapp
```
Method: **POST** → click **Save**

---

### How to test

#### Test 1 — curl (no phone needed)

```bash
curl -X POST http://localhost:8080/api/webhooks/whatsapp \
  -d "From=whatsapp:+96170000000&Body=Salam bddi 3 black hoodies size L delivery Hamra cash"
```

Expected: TwiML XML response + order appears in Orders page.

#### Test 2 — Live WhatsApp

Send a message from your phone to the Twilio sandbox number.

Expected:
- ngrok inspector at `http://localhost:4040` shows the POST request
- Order appears in the Orders page
- Twilio delivers a reply to your WhatsApp

#### Test 3 — Low confidence via WhatsApp

Send:
```
bddi shi
```

Expected:
- Order lands in the review queue (amber panel)
- Twilio replies: "Got your order! It's been flagged for a quick review (confidence: X%)"

#### Monitor requests

- **ngrok inspector:** `http://localhost:4040` — full request/response for every tunnel hit
- **Twilio logs:** Monitor → Logs → Messaging in the Twilio console

---

## Demo Script

### Review queue moment (~90 seconds)

1. Paste `Salam bddi 3 black hoodies w 2 white ones size M` into the Orders page
2. Show the amber review queue panel appear with the confidence badge
3. Say: *"The AI flagged this — missing delivery area and payment method. It doesn't commit anything until a human reviews it."*
4. Click **Approve & Commit**
5. Say: *"Approved — inventory is now deducted. That's the difference between a demo and a production system."*

### WhatsApp live moment (~60 seconds)

1. Have someone in the audience send a WhatsApp to the sandbox number (show the number on screen)
2. Keep the Orders page open and visible
3. The order appears live
4. Say: *"That message just came off WhatsApp. No copy-paste — the webhook received it, the AI extracted it, and it's in the system."*
5. If it lands in the review queue: bonus — show confidence score and approve it live
