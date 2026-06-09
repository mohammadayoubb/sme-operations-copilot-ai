"""Agentic tool-calling assistant.

The agent receives a user message + conversation history, reasons about which
tools to call, executes them against the live DB, feeds the results back to the
LLM, and repeats until the model stops requesting tools.  The final response is
grounded in real business data retrieved through tool calls.

Design rules:
- Read-only tools (check_stock, get_reorder_alerts, etc.) return plain-Python
  data — no LLM involved in the data retrieval itself.
- The one write tool (create_order) routes through the existing order_service,
  which runs guardrails + Pydantic validation — no safety shortcuts.
- Calculations (stock levels, margins, profit) stay in Python; the LLM only
  synthesises the results into a natural-language reply.
- Max 8 iterations to prevent infinite loops.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.repositories import invoice_repo, order_repo, product_repo, report_repo, sales_repo
from app.security.guardrails import is_safe_input
from app.services import forecasting_service

logger = get_logger(__name__)

MAX_ITERATIONS = 8

SYSTEM_PROMPT = """\
You are SoukPilot, an AI operations assistant for a Lebanese small business.
You have access to the business's live data through tools.
Always use tools to look up real data before answering questions about stock,
sales, orders, or prices.
Be concise and direct. Use numbers when you have them.
"""

_ARABIC_RE = re.compile(r'[؀-ۿ]')


def _lang_reminder(message: str) -> str:
    """Return a system-role language reminder injected right before the user's turn."""
    if _ARABIC_RE.search(message):
        return "LANGUAGE RULE: The owner just wrote/spoke in Arabic. Your reply MUST be entirely in Arabic. Do not use English at all."
    return "LANGUAGE RULE: The owner just wrote/spoke in English. Your reply MUST be entirely in English. Do not use Arabic at all."

# ── Tool definitions (OpenAI function-calling schema) ──────────────────────

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "check_stock",
            "description": (
                "List all products with their current stock level and reorder level. "
                "Use this when the owner asks about stock, inventory, or product quantities."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_reorder_alerts",
            "description": (
                "Get the list of products that need to be reordered, with days until stockout. "
                "Use when the owner asks what to reorder, what's running low, or what to buy."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_summary",
            "description": (
                "Get this week's and last week's revenue and profit totals with percentage change. "
                "Use when the owner asks about sales performance, revenue, or profit."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_latest_report",
            "description": (
                "Get the full AI-generated weekly business report if one exists. "
                "Use when the owner asks for a summary or report of the business."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_recent_orders",
            "description": "List the most recent customer orders with their items and status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of orders to return (default 5, max 20).",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_history",
            "description": (
                "Get the unit-price history for a specific product across invoices. "
                "Use when the owner asks how a product's cost has changed over time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Name of the product to look up (fuzzy-matched).",
                    }
                },
                "required": ["product_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": (
                "Create a new customer order from a natural-language description. "
                "Use when the owner says 'record an order', 'add an order', or describes "
                "items a customer wants. Runs the same AI extraction + validation as the "
                "Orders page."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The order description in natural language.",
                    }
                },
                "required": ["message"],
            },
        },
    },
]


# ── Tool implementations ────────────────────────────────────────────────────

def _check_stock(db: Session, business_id: int) -> dict:
    products = product_repo.list_products(db, business_id)
    items = [
        {
            "name": p.name,
            "current_stock": float(p.current_stock or 0),
            "reorder_level": float(p.reorder_level or 0),
            "status": (
                "critical" if (p.current_stock or 0) <= 0
                else "low" if (p.current_stock or 0) <= (p.reorder_level or 0)
                else "ok"
            ),
        }
        for p in products
    ]
    return {"products": items, "total": len(items)}


def _get_reorder_alerts(db: Session, business_id: int) -> dict:
    recs = forecasting_service.get_reorder_recommendations(db, business_id)
    return {
        "reorder_needed": [
            {
                "product": r.product_name,
                "current_stock": r.current_stock,
                "avg_daily_sales": r.avg_daily_sales,
                "days_until_stockout": r.days_until_stockout,
                "reorder_by": r.reorder_by_date,
            }
            for r in recs
        ],
        "count": len(recs),
    }


def _get_sales_summary(db: Session, business_id: int) -> dict:
    from app.services.report_service import pct_change, rev_profit

    today = date.today()
    start = today - timedelta(days=6)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=6)

    products = product_repo.list_products(db, business_id)
    cost_map = {p.id: float(p.cost_price or 0) for p in products}

    sales = sales_repo.get_all_sales(db, business_id)
    this_rows = [(s.product_id, s.quantity, s.total) for s in sales if s.sale_date and start <= s.sale_date <= today]
    last_rows = [(s.product_id, s.quantity, s.total) for s in sales if s.sale_date and prev_start <= s.sale_date <= prev_end]

    rev_this, profit_this = rev_profit(this_rows, cost_map)
    rev_last, profit_last = rev_profit(last_rows, cost_map)

    return {
        "period": {"start": start.isoformat(), "end": today.isoformat()},
        "revenue": {"this_week": rev_this, "last_week": rev_last, "change_pct": pct_change(rev_this, rev_last)},
        "profit": {"this_week": profit_this, "last_week": profit_last, "change_pct": pct_change(profit_this, profit_last)},
        "transactions": len(this_rows),
    }


def _get_latest_report(db: Session, business_id: int) -> dict:
    report = report_repo.get_latest(db, business_id)
    if report is None:
        return {"available": False, "message": "No weekly report has been generated yet."}
    return {
        "available": True,
        "period": {"start": str(report.period_start), "end": str(report.period_end)},
        "summary": report.summary_text,
        "data": report.data_json,
    }


def _list_recent_orders(db: Session, business_id: int, limit: int = 5) -> dict:
    limit = min(max(1, limit), 20)
    orders = order_repo.list_orders(db, business_id)[:limit]
    result = []
    for o in orders:
        items = order_repo.get_items(db, o.id)
        result.append({
            "id": o.id,
            "source": o.source,
            "status": o.status,
            "delivery_area": o.delivery_area,
            "payment_method": o.payment_method,
            "created_at": str(o.created_at),
            "items": [
                {"product": i.product_name, "quantity": i.quantity, "color": i.color, "size": i.size}
                for i in items
            ],
        })
    return {"orders": result, "count": len(result)}


def _get_price_history(db: Session, business_id: int, product_name: str) -> dict:
    from rapidfuzz import fuzz, process

    products = product_repo.list_products(db, business_id)
    if not products:
        return {"error": "No products found."}

    names = {p.id: p.name for p in products}
    best = process.extractOne(product_name, names, scorer=fuzz.token_sort_ratio)
    if not best or best[1] < 60:
        return {"error": f"No product matching '{product_name}' found."}

    product_id, matched_name = best[2], best[0]
    history = product_repo.price_history(db, product_id)
    return {
        "product": matched_name,
        "history": [{"date": str(d), "unit_price": p} for d, p in history],
        "data_points": len(history),
    }


def _create_order(db: Session, message: str) -> dict:
    from app.services.order_service import GuardrailError, extract_and_create_order

    try:
        order = extract_and_create_order(db, message, source="agent")
        db.commit()
        items = order_repo.get_items(db, order.id)
        return {
            "success": True,
            "order_id": order.id,
            "status": order.status,
            "delivery_area": order.delivery_area,
            "payment_method": order.payment_method,
            "items": [
                {"product": i.product_name, "quantity": i.quantity}
                for i in items
            ],
        }
    except GuardrailError as e:
        return {"success": False, "error": f"Input blocked: {e}"}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}


# ── Tool dispatcher ─────────────────────────────────────────────────────────

def _execute_tool(db: Session, business_id: int, name: str, args: dict) -> Any:
    logger.info("agent_tool_call", tool=name, args=list(args.keys()))
    if name == "check_stock":
        return _check_stock(db, business_id)
    if name == "get_reorder_alerts":
        return _get_reorder_alerts(db, business_id)
    if name == "get_sales_summary":
        return _get_sales_summary(db, business_id)
    if name == "get_latest_report":
        return _get_latest_report(db, business_id)
    if name == "list_recent_orders":
        return _list_recent_orders(db, business_id, limit=args.get("limit", 5))
    if name == "get_price_history":
        return _get_price_history(db, business_id, args.get("product_name", ""))
    if name == "create_order":
        return _create_order(db, args.get("message", ""))
    return {"error": f"Unknown tool: {name}"}


# ── Agent loop ──────────────────────────────────────────────────────────────

def chat(
    db: Session,
    message: str,
    history: list[dict],
    business_id: int | None = None,
) -> dict:
    """Run the agentic tool-calling loop and return the final response.

    Returns:
        {
            "response": str,           # final assistant message
            "tool_calls": [            # tools that were invoked (in order)
                {"tool": str, "args": dict, "result": dict}
            ]
        }
    """
    message = (message or "").strip()
    if not message:
        raise ValueError("message cannot be empty")

    safe, reason = is_safe_input(message)
    if not safe:
        logger.warning("agent_input_blocked", reason=reason)
        raise ValueError(f"Input blocked by guardrails: {reason}")

    if business_id is None:
        raise ValueError("business_id is required")

    # Build message list: system + prior history + language reminder + new user turn
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history:
        if h.get("role") in ("user", "assistant"):
            messages.append({"role": h["role"], "content": h["content"]})
    # Language reminder sits right before the user's turn so it overrides history context
    messages.append({"role": "system", "content": _lang_reminder(message)})
    messages.append({"role": "user", "content": message})

    from app.ai.llm import _client
    from app.core.config import settings

    tool_calls_log: list[dict] = []
    iterations = 0

    while iterations < MAX_ITERATIONS:
        iterations += 1
        resp = _client().chat.completions.create(
            model=settings.openai_llm_model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        msg = resp.choices[0].message

        # No tool calls → final answer
        if not msg.tool_calls:
            final = (msg.content or "").strip()
            logger.info(
                "agent_response",
                iterations=iterations,
                tools_called=len(tool_calls_log),
                response_chars=len(final),
            )
            return {"response": final, "tool_calls": tool_calls_log}

        # Append assistant message with tool calls
        messages.append(msg)

        # Execute each tool and feed results back
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            result = _execute_tool(db, business_id, tc.function.name, args)
            tool_calls_log.append({"tool": tc.function.name, "args": args, "result": result})

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, default=str),
            })

    # Safety: max iterations reached — ask model to wrap up without tools
    # (non-streaming path only — streaming path has its own wrap-up below)
    messages.append({
        "role": "user",
        "content": "Please give me your final answer based on what you've found so far.",
    })
    resp = _client().chat.completions.create(
        model=settings.openai_llm_model,
        messages=messages,
    )
    final = (resp.choices[0].message.content or "").strip()
    logger.warning("agent_max_iterations_reached", iterations=iterations)
    return {"response": final, "tool_calls": tool_calls_log}


# ── Streaming agent loop ─────────────────────────────────────────────────────

def chat_stream(db: Session, message: str, history: list[dict], business_id: int | None = None):
    """Streaming version of chat(). Yields SSE-formatted strings.

    SSE event types:
      tool_start  — a tool is about to be called {tool, args}
      tool_result — tool finished {tool, result}
      text        — a streamed answer token {text}
      done        — stream complete {tool_calls: [...]}
      error       — guardrail or other error {error}
    """
    import json as _json

    message = (message or "").strip()
    if not message:
        yield f'data: {_json.dumps({"type": "error", "error": "message cannot be empty"})}\n\n'
        return

    safe, reason = is_safe_input(message)
    if not safe:
        logger.warning("agent_input_blocked", reason=reason)
        yield f'data: {_json.dumps({"type": "error", "error": f"Input blocked: {reason}"})}\n\n'
        return

    if business_id is None:
        yield f'data: {_json.dumps({"type": "error", "error": "business_id is required"})}\n\n'
        return

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history:
        if h.get("role") in ("user", "assistant"):
            messages.append({"role": h["role"], "content": h["content"]})
    # Language reminder sits right before the user's turn so it overrides history context
    messages.append({"role": "system", "content": _lang_reminder(message)})
    messages.append({"role": "user", "content": message})

    from app.ai.llm import _client, stream_text
    from app.core.config import settings

    tool_calls_log: list[dict] = []
    iterations = 0

    while iterations < MAX_ITERATIONS:
        iterations += 1
        # Tool-calling round must be non-streaming so we can parse JSON tool calls.
        resp = _client().chat.completions.create(
            model=settings.openai_llm_model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            # No more tools — stream the final answer token by token.
            full = ""
            for token in stream_text(messages, temperature=0.4):
                full += token
                yield f'data: {_json.dumps({"type": "text", "text": token})}\n\n'
            logger.info("agent_response_stream", iterations=iterations,
                        tools_called=len(tool_calls_log), chars=len(full))
            yield f'data: {_json.dumps({"type": "done", "tool_calls": tool_calls_log})}\n\n'
            return

        # Append assistant message (with tool call metadata) to context.
        messages.append(msg)

        for tc in msg.tool_calls:
            try:
                args = _json.loads(tc.function.arguments or "{}")
            except _json.JSONDecodeError:
                args = {}

            yield f'data: {_json.dumps({"type": "tool_start", "tool": tc.function.name, "args": args})}\n\n'

            result = _execute_tool(db, business_id, tc.function.name, args)
            tool_calls_log.append({"tool": tc.function.name, "args": args, "result": result})

            yield f'data: {_json.dumps({"type": "tool_result", "tool": tc.function.name, "result": result})}\n\n'

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": _json.dumps(result, default=str),
            })

    # Max iterations — stream a wrap-up answer.
    messages.append({"role": "user",
                     "content": "Please give me your final answer based on what you've found so far."})
    full = ""
    for token in stream_text(messages, temperature=0.4):
        full += token
        yield f'data: {_json.dumps({"type": "text", "text": token})}\n\n'
    logger.warning("agent_max_iterations_reached", iterations=iterations)
    yield f'data: {_json.dumps({"type": "done", "tool_calls": tool_calls_log})}\n\n'
