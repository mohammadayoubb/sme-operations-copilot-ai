"""Report HTML export (print-to-PDF).

Generates a self-contained, print-optimised HTML page from a Report object.
No third-party packages — uses only Python's standard library.

The page includes:
  - A <script> that fires window.print() on load so the browser's native
    "Save as PDF" dialog opens immediately.
  - @media print CSS that hides the "Print / Save as PDF" button and sets
    correct page margins.
  - All data from the already-persisted Report — no new DB queries, no LLM.

Returns UTF-8 HTML bytes ready to stream as text/html.
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

from app.models.report import Report


def _pct_badge(pct: Any) -> str:
    if pct is None:
        return '<span class="muted">—</span>'
    val = float(pct)
    cls = "up" if val >= 0 else "down"
    sign = "+" if val >= 0 else ""
    return f'<span class="{cls}">{sign}{val:.1f}%</span>'


def _row(*cells: str, shade: bool = False) -> str:
    cls = ' class="shade"' if shade else ""
    tds = "".join(f"<td>{c}</td>" for c in cells)
    return f"<tr{cls}>{tds}</tr>"


def build_report_pdf(report: Report) -> bytes:
    """Build a print-ready HTML page. Returns UTF-8 bytes."""
    data: dict = report.data_json or {}
    period = data.get("period", {})
    start  = escape(str(period.get("start", report.period_start or "")))
    end    = escape(str(period.get("end",   report.period_end   or "")))
    ts     = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    sales  = data.get("sales",  {})
    profit = data.get("profit", {})
    most   = data.get("most_profitable")
    least  = data.get("least_profitable")
    top_products: list[dict]    = data.get("top_products", [])
    risks:        list[dict]    = data.get("low_stock_risks", [])
    price_changes: list[dict]   = data.get("supplier_price_changes", [])
    summary = escape(report.summary_text or "")

    # ── Top-products table rows ──────────────────────────────────────────
    top_rows = "".join(
        _row(
            escape(p.get("name", "—")),
            f"${float(p.get('revenue', 0)):,.2f}",
            str(p.get("units", "—")),
            shade=(i % 2 == 1),
        )
        for i, p in enumerate(top_products)
    ) or "<tr><td colspan='3' class='muted'>No sales this week.</td></tr>"

    # ── Reorder risks rows ───────────────────────────────────────────────
    risk_rows = "".join(
        _row(
            escape(r.get("name", "—")),
            str(r.get("current_stock", "—")),
            f"{float(r['days_until_stockout']):.1f}" if r.get("days_until_stockout") is not None else "—",
            shade=(i % 2 == 1),
        )
        for i, r in enumerate(risks)
    ) or "<tr><td colspan='3' class='muted'>No reorder risks. 🎉</td></tr>"

    # ── Price-change rows ────────────────────────────────────────────────
    price_rows = "".join(
        _row(
            escape(c.get("supplier", "—")),
            escape(c.get("product", "—")),
            _pct_badge(c.get("change_pct")),
            shade=(i % 2 == 1),
        )
        for i, c in enumerate(price_changes)
    )

    # ── Margin helpers ───────────────────────────────────────────────────
    most_html  = f"{escape(most['name'])} — {most['margin_pct']}% margin"  if most  and most.get("margin_pct")  is not None else "—"
    least_html = f"{escape(least['name'])} — {least['margin_pct']}% margin" if least and least.get("margin_pct") is not None else "—"

    price_section = f"""
    <section>
      <h2>Supplier Price Changes</h2>
      <table>
        <thead><tr><th>Supplier</th><th>Product</th><th>Change</th></tr></thead>
        <tbody>{price_rows}</tbody>
      </table>
    </section>""" if price_changes else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>SoukPilot AI — Weekly Report {start}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 13px;
    color: #1a1a2e;
    background: #fff;
    padding: 36px 48px;
    max-width: 860px;
    margin: 0 auto;
  }}

  /* ── Header ── */
  .report-header {{
    border-top: 5px solid #6c63ff;
    padding-top: 18px;
    margin-bottom: 28px;
  }}
  .brand {{ font-size: 22px; font-weight: 700; color: #6c63ff; }}
  .period {{ font-size: 12px; color: #888; margin-top: 4px; }}

  /* ── Print button (hidden when printing) ── */
  .print-btn {{
    float: right;
    margin-top: -44px;
    background: #6c63ff;
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
  }}
  @media print {{ .print-btn {{ display: none; }} }}

  /* ── Sections ── */
  section {{ margin-bottom: 28px; }}
  h2 {{
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: #6c63ff;
    border-bottom: 1px solid #e0e0f0;
    padding-bottom: 5px;
    margin-bottom: 12px;
  }}

  /* ── Narrative ── */
  .narrative {{
    font-size: 13.5px;
    line-height: 1.7;
    color: #2a2a3e;
    background: #f9f9ff;
    border-left: 3px solid #6c63ff;
    padding: 12px 16px;
    border-radius: 4px;
  }}

  /* ── Metrics grid ── */
  .metrics {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 8px;
  }}
  .metric {{
    border: 1px solid #e0e0f0;
    border-top: 3px solid #6c63ff;
    border-radius: 6px;
    padding: 12px 14px;
  }}
  .metric-label {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: #888; margin-bottom: 4px; }}
  .metric-value {{ font-size: 20px; font-weight: 700; color: #6c63ff; }}
  .metric-badge {{ font-size: 11px; margin-top: 3px; }}

  .margin-row {{ font-size: 12px; color: #555; margin-top: 8px; }}
  .margin-row span {{ font-weight: 600; color: #1a1a2e; }}

  /* ── Tables ── */
  table {{ width: 100%; border-collapse: collapse; }}
  thead tr {{ background: #f4f4fb; }}
  th {{
    text-align: left;
    padding: 7px 10px;
    font-size: 10.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #888;
  }}
  td {{ padding: 7px 10px; font-size: 12.5px; border-top: 1px solid #f0f0f8; }}
  tr.shade td {{ background: #f9f9ff; }}

  /* ── Change badges ── */
  .up   {{ color: #16a34a; font-weight: 600; }}
  .down {{ color: #dc2626; font-weight: 600; }}
  .muted {{ color: #aaa; }}

  /* ── Footer ── */
  .report-footer {{
    margin-top: 36px;
    padding-top: 10px;
    border-top: 1px solid #e0e0f0;
    font-size: 10.5px;
    color: #aaa;
    text-align: center;
  }}

  /* ── Page breaks ── */
  @media print {{
    body {{ padding: 0; }}
    section {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>

<div class="report-header">
  <button class="print-btn" onclick="window.print()">⬇ Save as PDF</button>
  <div class="brand">SoukPilot AI</div>
  <div class="period">Weekly Business Report &nbsp;·&nbsp; {start} → {end}</div>
</div>

<!-- Narrative -->
<section>
  <h2>Business Summary</h2>
  <div class="narrative">{summary or '<span class="muted">No narrative available.</span>'}</div>
</section>

<!-- Key Metrics -->
<section>
  <h2>Key Metrics</h2>
  <div class="metrics">
    <div class="metric">
      <div class="metric-label">Revenue (this week)</div>
      <div class="metric-value">${float(sales.get('this_week', 0)):,.2f}</div>
      <div class="metric-badge">{_pct_badge(sales.get('change_pct'))}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Gross Profit</div>
      <div class="metric-value">${float(profit.get('this_week', 0)):,.2f}</div>
      <div class="metric-badge">{_pct_badge(profit.get('change_pct'))}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Revenue (last week)</div>
      <div class="metric-value" style="color:#1a1a2e">${float(sales.get('last_week', 0)):,.2f}</div>
      <div class="metric-badge">&nbsp;</div>
    </div>
    <div class="metric">
      <div class="metric-label">Profit (last week)</div>
      <div class="metric-value" style="color:#1a1a2e">${float(profit.get('last_week', 0)):,.2f}</div>
      <div class="metric-badge">&nbsp;</div>
    </div>
  </div>
  <div class="margin-row">Most profitable: <span>{most_html}</span></div>
  <div class="margin-row">Least profitable: <span>{least_html}</span></div>
</section>

<!-- Top Products -->
<section>
  <h2>Top Products by Revenue</h2>
  <table>
    <thead><tr><th>Product</th><th>Revenue</th><th>Units Sold</th></tr></thead>
    <tbody>{top_rows}</tbody>
  </table>
</section>

<!-- Reorder Risks -->
<section>
  <h2>Reorder Risks</h2>
  <table>
    <thead><tr><th>Product</th><th>Stock Left</th><th>Days Until Stockout</th></tr></thead>
    <tbody>{risk_rows}</tbody>
  </table>
</section>

{price_section}

<div class="report-footer">
  Generated by SoukPilot AI &nbsp;·&nbsp; {ts}
</div>

<script>
  // Auto-open print dialog when opened in a new tab
  window.addEventListener('load', function() {{
    // Small delay so the page renders first
    setTimeout(function() {{ window.print(); }}, 400);
  }});
</script>

</body>
</html>"""

    return html.encode("utf-8")
