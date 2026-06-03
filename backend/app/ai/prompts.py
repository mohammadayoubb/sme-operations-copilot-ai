# All LLM prompt templates live here (Phase 1+)

INVOICE_EXTRACTION_PROMPT = """\
You are a data extraction assistant. Extract the following fields from this invoice text as valid JSON only. Do not add any explanation.

Fields to extract:
- supplier (string)
- date (ISO format string, e.g. "2026-05-27")
- items (array of objects, each with: name, quantity, unit_price, total)
- invoice_total (float)
- currency (string, e.g. "USD" or "LBP")

Invoice text:
{ocr_text}

Respond with only valid JSON. If a field cannot be found, use null.
"""

ORDER_EXTRACTION_PROMPT = """\
You are an order extraction assistant for a Lebanese small business. Extract the following fields from this customer message as valid JSON only.

Fields:
- intent (one of: new_order, inquiry, complaint, other)
- items (array of objects, each with: product, quantity, color, size — use null if not mentioned)
- delivery_area (string or null)
- payment_method (one of: cash_on_delivery, bank_transfer, other, null)
- notes (string or null)

Customer message:
{message}

Respond with only valid JSON.
"""

PRICING_EXPLANATION_PROMPT = """\
A small business owner has the following product financials:
- Cost price: ${cost}
- Selling price: ${sell}
- Delivery cost: ${delivery}
- Packaging cost: ${packaging}
- Calculated profit: ${profit}
- Profit margin: {margin_pct}%

Write 2-3 sentences explaining these results in simple business language. End with one specific, actionable recommendation to improve the margin.
"""

RAG_QA_PROMPT = """\
You are a business assistant for a Lebanese small business owner. Answer the owner's question using ONLY the business records provided below.
If the answer cannot be found in the records, say exactly: "I don't have enough data to answer that."

Business records:
{context}

Owner's question: {question}

Provide a clear, direct answer. Mention which records support your answer when relevant.
"""

WEEKLY_REPORT_PROMPT = """\
You are writing a weekly business summary for a Lebanese small business owner. Use the structured data below to write a clear 4-6 sentence summary.
Highlight wins, risks, and end with one actionable recommendation.

Data:
{data_json}

Write in simple, direct language.
"""

ANOMALY_EXPLANATION_PROMPT = """\
You are a business analyst for a Lebanese small business. The system detected unusual sales patterns.
For each anomaly below, write ONE plain-language sentence explaining what it likely means for the owner.
Be specific: mention the product, the direction, and a practical implication or action.

Anomalies:
{anomaly_list}

Respond with ONLY valid JSON: {{"explanations": ["sentence 1", "sentence 2", ...]}}
One explanation per anomaly, in the same order.
"""

VOICE_COMMAND_PROMPT = """\
You are a voice command interpreter for a Lebanese small business. The owner just spoke a command.
Extract the intent and parameters as valid JSON only.

Possible intents: record_sale, check_stock, create_order, get_summary, other

Transcript: "{transcript}"

Respond with only valid JSON: {{"intent": "...", "params": {{...}}}}
"""
