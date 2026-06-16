# SoukPilot AI — Demo Guide 2 (Live Railway)

> Presentation script for the **live deployed** app on Railway.
> Impact-ordered, with exact inputs to paste and one-liners to say at each step.
> Supersedes `DEMO_GUIDE.md` (which assumes a local `docker compose` setup).

---

## Warm-Up Checklist (do this 2–3 min before presenting)

Railway containers sleep when idle and the RAG index is wiped on every redeploy,
so warm everything before you're on stage:

- [ ] Open the live frontend URL and log in to the **demo tenant**. Confirm the
      exact credentials work *now* — don't discover a bad password on stage.
- [ ] Check the **status chip** (top-right of the topbar) reads **Live** (green).
      It hits the real `/health` endpoint. If it says Degraded/Offline, wait and refresh.
- [ ] Open **Business Q&A** and click **↻ Reindex data** once. The RAG index
      (`.pkl`) self-heals on first question, but pre-warming avoids a slow first answer.
- [ ] Fire one throwaway **AI Agent** question to warm the backend + model path.
- [ ] **Do not redeploy** right before presenting (it wipes the RAG index).

### Demo data you're working with

The seeded tenant stocks **groceries + apparel** — not tyres. Every question
must reference these real products:

| Product | Notes |
|---|---|
| Pepsi 330ml | high volume; price hike on latest invoice (+10.5%) |
| Lays Chips 45g | |
| Water 1.5L | price hike (+13.6%) |
| Nutella 400g | **LOW stock** — reorder item; price hike (+6.9%) |
| Nescafé 200g | |
| Black Hoodie | apparel, color/size variants |
| White T-Shirt | **LOW stock** — reorder item |

Low-stock / reorder items: **Nutella 400g** and **White T-Shirt**.
Supplier with the biggest price increases: **ABC Foods Trading**.

---

## Demo Flow (~10–12 min)

Lead with what makes people lean in, then show the depth underneath.

| # | Screen | Why here | Time |
|---|--------|----------|------|
| 1 | Dashboard | Orientation — "this is real, populated data" | 30s |
| 2 | Invoice Upload | The "it read my photo" moment | 2m |
| 3 | Orders (WhatsApp paste) | Relatable, Lebanese-SME-specific | 90s |
| 4 | Business Q&A (Hybrid RAG) | Technical credibility | 90s |
| 5 | AI Agent | Agentic tool-calling — the headline | 60s |
| 6 | Voice Copilot | The crowd-pleaser | 45s |
| 7 | Inventory + Reports | ML forecasting + PDF export | 60s |
| 8 | Widget Embed | "and it's productizable" | 30s |
| 9 | Super-Admin + multi-tenancy | Architecture maturity | 60s |

**5-minute version:** Invoice → Orders → Agent → Voice, then one line on
multi-tenancy. Those four carry the whole story.

---

## Step 1 — Dashboard (30s)

Land on the Dashboard after login.

**Point out:** sales this week + % change, gross profit, the
"products at/below reorder level" warning (**Nutella 400g** + **White T-Shirt**),
reorder alerts, recent invoices.

**Say:** *"This isn't mock data — 60 days of sales history, real invoices and
orders. Every AI operation feeds this one view in real time."*

---

## Step 2 — Invoice OCR + LLM Extraction (2 min)

Navigate to **Invoices**. Upload the known sample invoice (the seeded baseline
matters — see caveat).

**While it processes**, narrate the **pending → processing → processed** poll so
the wait feels intentional. When done, point at the extracted JSON (supplier,
date, line items) and the **price-increase alert** (e.g. *"Pepsi 330ml up 10.5%
vs the previous invoice from ABC Foods"*).

**Say:** *"Every field was extracted by the LLM. The price comparison is pure
Python — the LLM only reads, Python calculates."*

> ⚠️ Use the **known sample invoice only**. A random invoice may extract products
> that don't match inventory and won't trigger the price alert (which needs a
> prior invoice from the same supplier to compare against).

---

## Step 3 — WhatsApp Order Extraction (90s)

Navigate to **Orders**. Paste:

```
Salam, bddi 3 black hoodies size L w 2 white ones size M, delivery to Hamra, cash on delivery
```

**Point out:** intent `new_order`, items with color + size extracted, delivery
area Hamra, payment cash_on_delivery, guardrail scan ran first.

Second one for variety:
```
Hi! Can I get 5x Pepsi 330ml and 2x Nutella 400g delivered to Achrafieh? Bank transfer ok
```

**Say:** *"The owner pastes a WhatsApp message exactly as it arrives — mixed
Arabic and English — and gets a structured order. Fuzzy matching maps 'Pepsi'
to 'Pepsi 330ml' automatically."*

---

## Step 4 — Business Q&A / Hybrid RAG (90s)

Navigate to **Business Q&A**. (Already reindexed during warm-up.) Ask in order:

1. `Which supplier raised prices the most?`
2. `What were my top selling products this week?`

**Point out:** the **GROUNDED** badge (answer only uses indexed records), the
**HYBRID** badge (vector + BM25 fused), the stats line, and source cards.

Then the guardrail flex:
`What is the weather like in Beirut?` → **NO DATA** refusal.

**Say:** *"Hybrid RAG — vector search fused with BM25 keyword ranking via
Reciprocal Rank Fusion, then the full source record goes to the model. The
badges prove the retrieval actually ran — and it refuses to answer outside the
business's own data."*

---

## Step 5 — AI Agent (60s)

Navigate to **AI Agent**. Ask:

```
What is my current stock situation and which products need restocking?
```

**Point out:** real backend tool calls (`get_inventory`, `get_forecast`, etc.),
expandable tool badges showing input/output, final synthesized answer.

**Say:** *"This is an agentic loop — the model decides which tools to call,
calls real backend APIs, reads the results, and decides if it needs more. Expand
any badge to see the live call."*

---

## Step 6 — Voice Copilot (45s) — highest-risk step

Navigate to **Voice**. Speak a short, unambiguous question:

> *"What are my top selling products this week?"*

**Say:** *"Whisper transcribes, the same agent answers over live data, and
OpenAI TTS reads it back — full speech-to-speech."*

> ⚠️ Mic permissions, room noise, and accents all add failure modes. Test on the
> exact machine/room beforehand. Fallback line if it misfires: *"and if the
> room's noisy, the same thing works typed in the Agent tab"* — then pivot.
> Don't let a failed voice demo eat your momentum.

---

## Step 7 — Inventory + Reports (60s)

**Inventory:** point at reorder recommendation cards for **Nutella 400g** and
**White T-Shirt** (stock left, avg daily sales, days to stockout, reorder-by date)
and the LOW/CRITICAL/OK badges.

**Say:** *"Forecasting trained on 60 days of history — it compared a moving
average, linear regression, and random forest, and picked the best by RMSE."*

**Reports:** show the weekly report (sales vs last week, gross profit, top 5,
price-change flags, low-stock risks, AI narrative) and click **Export PDF**.

**Say:** *"The numbers are all aggregated in Python. The LLM only writes the
narrative — it never calculates anything."*

---

## Step 8 — Widget Embed (30s)

Navigate to **Widget Embed** (Widget Settings). Show the embeddable snippet/token.

**Say:** *"The same assistant drops into any external website as a chat widget —
this is the productized, customer-facing version of the agent."*

---

## Step 9 — Super-Admin + Multi-Tenancy (60s)

Open `/superadmin` and log in with the superadmin credentials.

**Point out:** separate portal (no business sidebar), tenant table with per-tenant
counts, expand a tenant's stats cards, the Add Tenant form, two-step delete.

**Say:** *"The superadmin token has no business_id — it literally cannot read any
tenant's orders or invoices. Every row carries a business_id; the JWT embeds it
on login; every query is scoped to it. Two tenants can have a product with the
same name and never see each other's records."*

---

## Closing (30s)

> *"SoukPilot AI demonstrates the full AI engineering stack — OCR, LLM
> extraction, order NLP, hybrid RAG, ML forecasting, agentic tool-calling,
> voice, PDF export, guardrails, multi-tenancy, and a two-tier admin system.
> Every feature starts with messy real-world input and ends with structured,
> isolated business data."*

---

## Handling "How does feature X work?"

Give the one-sentence architecture answer, then offer depth
(`docs/ARCHITECTURE.md`, `docs/AI_FEATURES.md`).

- **"Is it really reading the invoice?"** → *"Vision does OCR, GPT-4o-mini
  extracts structured JSON, Pydantic validates it before anything touches the DB."*
- **"How is the Q&A not hallucinating?"** → *"Grounded RAG — answers can only
  cite indexed business records; the GROUNDED badge enforces it."*
- **"What stops cross-tenant data leaks?"** → *"Every row carries a business_id;
  the JWT embeds it; every query is scoped to it."*
- **"How do you stop the LLM doing math wrong?"** → *"It doesn't do math — all
  numbers are computed in Python. The LLM only handles language."* (Best
  credibility line — use it whenever math comes up.)
- **"What if the AI gets an order wrong?"** → *"Confidence scoring — anything
  below 0.6 goes to a human review queue instead of auto-fulfilling."*
- **"Is the agent calling real tools?"** → *"Real backend API calls — expand a
  tool badge to see the actual input and output."*

If a question goes past what you can answer confidently, don't bluff:
*"Great question — the full data flow is in my architecture doc, happy to walk
through it after."* That reads as more competent than a shaky improvisation.

---

## Things to Avoid

- Don't run any `docker compose` / `pytest` commands — this is the live Railway app.
- Don't upload a random invoice — use the known sample so the price alert fires.
- Don't ask about products that aren't seeded (no tyres) — match the table above.
- Don't redeploy right before presenting (wipes the RAG index).
- Don't toggle the status chip (it cycles Live→Degraded→Offline for show) right
  before a real action — it can confuse you about real backend health.

---

## Quick Reference — Copy-Paste Inputs

| Step | Input |
|---|---|
| Order 1 | `Salam, bddi 3 black hoodies size L w 2 white ones size M, delivery to Hamra, cash on delivery` |
| Order 2 | `Hi! Can I get 5x Pepsi 330ml and 2x Nutella 400g delivered to Achrafieh? Bank transfer ok` |
| RAG Q1 | `Which supplier raised prices the most?` |
| RAG Q2 | `What were my top selling products this week?` |
| RAG no-data | `What is the weather like in Beirut?` |
| Agent | `What is my current stock situation and which products need restocking?` |
| Voice (speak) | `What are my top selling products this week?` |
