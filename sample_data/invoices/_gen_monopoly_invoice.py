"""Generate a clean, OCR-friendly supplier invoice PDF for the demo restock.

The key line is "Monopoly game board" — it must fuzzy-match the existing product
so the invoice restocks it instead of creating a new one. Swap the other line
items for real products on the souk tyre account if you want them to match too.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas

OUT = "sample_data/invoices/powerbank_restock_1000.pdf"

SUPPLIER = "Cedar Wholesale Trading"
SUPPLIER_CONTACT = "sales@cedarwholesale.com  ·  +961 1 555 204"
INVOICE_NO = "CWT-2026-0488"
INVOICE_DATE = "2026-06-14"
CURRENCY = "USD"

# (description, qty, unit_price)
ITEMS = [
    ("Power Bank 10000mAh", 1000, 15.00),
]

c = canvas.Canvas(OUT, pagesize=A4)
W, H = A4

# ── Header ──────────────────────────────────────────────────────────────
c.setFillColor(colors.HexColor("#0f172a"))
c.setFont("Helvetica-Bold", 26)
c.drawString(20 * mm, H - 28 * mm, "INVOICE")

c.setFillColor(colors.HexColor("#334155"))
c.setFont("Helvetica-Bold", 13)
c.drawRightString(W - 20 * mm, H - 22 * mm, SUPPLIER)
c.setFont("Helvetica", 9)
c.drawRightString(W - 20 * mm, H - 27 * mm, SUPPLIER_CONTACT)

c.setFont("Helvetica", 10)
c.setFillColor(colors.HexColor("#475569"))
c.drawString(20 * mm, H - 40 * mm, f"Invoice No:   {INVOICE_NO}")
c.drawString(20 * mm, H - 46 * mm, f"Invoice Date: {INVOICE_DATE}")
c.drawString(20 * mm, H - 52 * mm, f"Currency:     {CURRENCY}")

c.drawString(20 * mm, H - 62 * mm, "Bill To:  Souk Tyre")

# ── Table header ────────────────────────────────────────────────────────
top = H - 75 * mm
c.setFillColor(colors.HexColor("#0f172a"))
c.rect(20 * mm, top, W - 40 * mm, 9 * mm, fill=1, stroke=0)
c.setFillColor(colors.white)
c.setFont("Helvetica-Bold", 10)
c.drawString(23 * mm, top + 2.8 * mm, "Description")
c.drawRightString(120 * mm, top + 2.8 * mm, "Qty")
c.drawRightString(150 * mm, top + 2.8 * mm, "Unit Price")
c.drawRightString(W - 23 * mm, top + 2.8 * mm, "Line Total")

# ── Rows ────────────────────────────────────────────────────────────────
y = top - 11 * mm
c.setFont("Helvetica", 10)
grand = 0.0
for i, (desc, qty, price) in enumerate(ITEMS):
    line_total = qty * price
    grand += line_total
    if i % 2 == 1:
        c.setFillColor(colors.HexColor("#f1f5f9"))
        c.rect(20 * mm, y - 2.5 * mm, W - 40 * mm, 9 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#1e293b"))
    c.drawString(23 * mm, y, desc)
    c.drawRightString(120 * mm, y, str(qty))
    c.drawRightString(150 * mm, y, f"${price:,.2f}")
    c.drawRightString(W - 23 * mm, y, f"${line_total:,.2f}")
    y -= 11 * mm

# ── Total ───────────────────────────────────────────────────────────────
c.setStrokeColor(colors.HexColor("#cbd5e1"))
c.line(110 * mm, y + 3 * mm, W - 20 * mm, y + 3 * mm)
c.setFont("Helvetica-Bold", 12)
c.setFillColor(colors.HexColor("#0f172a"))
c.drawRightString(150 * mm, y - 4 * mm, "TOTAL")
c.drawRightString(W - 23 * mm, y - 4 * mm, f"${grand:,.2f} {CURRENCY}")

c.setFont("Helvetica-Oblique", 8)
c.setFillColor(colors.HexColor("#94a3b8"))
c.drawString(20 * mm, 20 * mm, "Thank you for your business. Payment due within 30 days.")

c.showPage()
c.save()
print(f"Wrote {OUT}  (total ${grand:,.2f})")
