"""Generate 'play' supplier invoice PDFs for demoing the upload → OCR → extraction
pipeline WITHOUT disturbing the seeded reorder alerts.

Every line item below is a brand-new SKU that does NOT fuzzy-match (rapidfuzz
token_sort_ratio >= 85) any product in the souk_tripoli seed catalogue. On upload
each becomes a freshly-created product (stock starts at 0, no reorder_level, no
sales history), so it can never raise a reorder alert and never restocks an
existing CRITICAL/LOW item.

Output: test_invoices/play/*.pdf

Run:
    python generate_play_invoices.py
"""
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

OUT = os.path.join(os.path.dirname(__file__), "test_invoices", "play")
os.makedirs(OUT, exist_ok=True)

W, H = A4  # 595 x 842 pts


# ── Layout helpers (shared style with generate_test_invoices.py) ────────────────
def line(c, y):
    c.line(2 * cm, y, W - 2 * cm, y)


def header(c, supplier, address, phone, inv_no, inv_date, due_date):
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2 * cm, H - 2 * cm, supplier)
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(2 * cm, H - 2.6 * cm, address)
    c.drawString(2 * cm, H - 3.0 * cm, phone)
    c.setFillColorRGB(0, 0, 0)

    c.setFont("Helvetica-Bold", 24)
    c.setFillColorRGB(0.13, 0.13, 0.13)
    c.drawRightString(W - 2 * cm, H - 2 * cm, "INVOICE")
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawRightString(W - 2 * cm, H - 2.7 * cm, f"Invoice #:  {inv_no}")
    c.drawRightString(W - 2 * cm, H - 3.1 * cm, f"Date:         {inv_date}")
    c.drawRightString(W - 2 * cm, H - 3.5 * cm, f"Due Date:  {due_date}")
    c.setFillColorRGB(0, 0, 0)
    line(c, H - 3.9 * cm)


def bill_to(c, name, address):
    y = H - 4.5 * cm
    c.setFont("Helvetica-Bold", 9)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(2 * cm, y, "BILL TO")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(2 * cm, y - 0.5 * cm, name)
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawString(2 * cm, y - 1.0 * cm, address)
    c.setFillColorRGB(0, 0, 0)


def table_header(c, y, money):
    c.setFillColorRGB(0.13, 0.13, 0.13)
    c.rect(2 * cm, y - 0.5 * cm, W - 4 * cm, 0.55 * cm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColorRGB(1, 1, 1)
    c.drawString(2.3 * cm, y - 0.2 * cm, "DESCRIPTION")
    c.drawString(10 * cm, y - 0.2 * cm, "QTY")
    c.drawString(12.5 * cm, y - 0.2 * cm, "UNIT")
    c.drawString(14.5 * cm, y - 0.2 * cm, "UNIT PRICE")
    c.drawRightString(W - 2.3 * cm, y - 0.2 * cm, "TOTAL")
    c.setFillColorRGB(0, 0, 0)
    return y - 0.6 * cm


def table_row(c, y, desc, qty, unit, price, total, money, shade=False):
    if shade:
        c.setFillColorRGB(0.97, 0.97, 0.97)
        c.rect(2 * cm, y - 0.45 * cm, W - 4 * cm, 0.5 * cm, fill=1, stroke=0)
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.15, 0.15, 0.15)
    c.drawString(2.3 * cm, y - 0.2 * cm, desc)
    c.drawString(10 * cm, y - 0.2 * cm, str(qty))
    c.drawString(12.5 * cm, y - 0.2 * cm, unit)
    c.drawString(14.5 * cm, y - 0.2 * cm, money(price))
    c.drawRightString(W - 2.3 * cm, y - 0.2 * cm, money(total))
    c.setFillColorRGB(0, 0, 0)
    return y - 0.55 * cm


def totals(c, y, subtotal, tax_pct, currency, money):
    line(c, y)
    y -= 0.4 * cm
    tax = subtotal * tax_pct / 100
    grand = subtotal + tax
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawRightString(W - 5.5 * cm, y, "Subtotal:")
    c.drawRightString(W - 2 * cm, y, f"{currency} {money(subtotal, bare=True)}")
    y -= 0.55 * cm
    c.drawRightString(W - 5.5 * cm, y, f"VAT ({tax_pct}%):")
    c.drawRightString(W - 2 * cm, y, f"{currency} {money(tax, bare=True)}")
    y -= 0.1 * cm
    line(c, y)
    y -= 0.55 * cm
    c.setFont("Helvetica-Bold", 12)
    c.setFillColorRGB(0, 0, 0)
    c.drawRightString(W - 5.5 * cm, y, "TOTAL DUE:")
    c.drawRightString(W - 2 * cm, y, f"{currency} {money(grand, bare=True)}")
    return grand


def footer(c, note=""):
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    if note:
        c.drawCentredString(W / 2, 2 * cm, note)
    c.drawCentredString(W / 2, 1.5 * cm, "Thank you for your business!")


def usd(v, bare=False):
    return f"{v:,.2f}" if bare else f"${v:,.2f}"


def lbp(v, bare=False):
    return f"{v:,.0f}" if bare else f"LBP {v:,.0f}"


def build(filename, supplier, address, phone, inv_no, inv_date, due_date,
          billto_name, billto_addr, items, tax_pct, currency, money, note):
    path = os.path.join(OUT, filename)
    c = canvas.Canvas(path, pagesize=A4)
    header(c, supplier, address, phone, inv_no, inv_date, due_date)
    bill_to(c, billto_name, billto_addr)
    y = H - 6.5 * cm
    y = table_header(c, y, money)
    for i, (desc, qty, unit, price) in enumerate(items):
        y = table_row(c, y, desc, qty, unit, price, qty * price, money, shade=(i % 2 == 0))
    subtotal = sum(q * p for _, q, _, p in items)
    totals(c, y - 0.3 * cm, subtotal, tax_pct, currency, money)
    footer(c, note)
    c.save()
    print(f"Created: {path}")


# ── Invoice 1 — Café & Fresh (USD) ──────────────────────────────────────────────
build(
    "play_cafe_beqaa_fresh.pdf",
    "Beqaa Fresh Distributors", "Zahle Industrial Rd, Beqaa, Lebanon  |  TIN: LB-2019-05512",
    "Tel: +961 8 802 410  |  sales@beqaafresh.lb",
    "BF-2026-0142", "2026-06-12", "2026-06-27",
    "Souk Tripoli", "Mina Road, Tripoli, Lebanon",
    [
        ("Almaza Pilsner 330ml (case of 24)", 12, "case", 18.50),
        ("Ayran Yogurt Drink 250ml", 60, "cup", 0.55),
        ("Tropicana Orange Juice 1L", 40, "carton", 1.85),
        ("Halloum Cheese 500g", 30, "pack", 4.20),
        ("Arabic Coffee Cardamom 450g", 24, "bag", 6.75),
        ("San Pellegrino Sparkling 750ml", 36, "bottle", 1.40),
    ],
    11, "USD", usd,
    "Cold-chain delivery. Payment via OMT or bank transfer to Fransabank.",
)

# ── Invoice 2 — Office & Stationery (USD) ───────────────────────────────────────
build(
    "play_stationery_capital_office.pdf",
    "Capital Office Supplies", "Bechara El Khoury, Beirut, Lebanon  |  TIN: LB-2016-02288",
    "Tel: +961 1 615 740  |  orders@capitaloffice.lb",
    "CO-88401", "2026-06-13", "2026-06-28",
    "Souk Tripoli", "Azmi Street, Tripoli, Lebanon",
    [
        ("A4 Copy Paper 80gsm (ream of 500)", 40, "ream", 3.90),
        ("Bic Cristal Ballpoint Blue (box of 50)", 20, "box", 6.40),
        ("Stabilo Boss Highlighter (pack of 4)", 30, "pack", 2.75),
        ("Sticky Notes 76x76mm (pack of 12)", 25, "pack", 3.10),
        ("Heavy-Duty Stapler", 15, "pcs", 5.50),
        ("Whiteboard Marker Black (box of 10)", 18, "box", 4.20),
        ("Spiral Notebook A5 (pack of 5)", 24, "pack", 4.80),
    ],
    11, "USD", usd,
    "Net 15 days. Free delivery on orders above $250 within Tripoli.",
)

# ── Invoice 3 — Household & Cleaning (USD) ───────────────────────────────────────
build(
    "play_household_sannine.pdf",
    "Sannine Household Supplies", "Jounieh Highway, Keserwan, Lebanon  |  TIN: LB-2013-01190",
    "Tel: +961 9 640 905  |  info@sannine-supplies.com",
    "SHS-3320", "2026-06-14", "2026-06-29",
    "Souk Tripoli", "Tall Square, Tripoli, Lebanon",
    [
        ("Clorox Bleach 2L", 36, "bottle", 1.95),
        ("Comfort Fabric Softener 1.5L", 24, "bottle", 3.30),
        ("Scotch-Brite Scour Sponge (pack of 6)", 30, "pack", 2.10),
        ("Windex Glass Cleaner 500ml", 24, "bottle", 2.65),
        ("Air Freshener Lavender 300ml", 20, "can", 2.40),
        ("Pine Floor Cleaner 1L", 28, "bottle", 1.80),
    ],
    11, "USD", usd,
    "Bulk discounts available. Delivery driver: Abu Sami +961 71 884 220.",
)

# ── Invoice 4 — Confectionery (LBP, multi-currency demo) ─────────────────────────
build(
    "play_confectionery_zahle_lbp.pdf",
    "Zahle Confectionery Wholesale", "Boulevard, Zahle, Lebanon  |  TIN: LB-2014-04405",
    "Tel: +961 8 813 277  |  wholesale@zahlesweets.lb",
    "ZCW-7715", "2026-06-15", "2026-06-30",
    "Souk Tripoli", "Mina Road, Tripoli, Lebanon",
    [
        ("Galaxy Milk Chocolate 80g", 120, "bar", 82_000),
        ("Maltesers Pouch 135g", 80, "pouch", 165_000),
        ("Doritos Nacho Cheese 150g", 100, "bag", 110_000),
        ("Haribo Goldbears 100g", 90, "pack", 78_000),
        ("Twix Twin Bar 50g", 144, "bar", 61_000),
        ("Kinder Bueno White 39g", 96, "bar", 71_000),
    ],
    11, "LBP", lbp,
    "Prices in LBP. Cash on delivery. Restock weekly every Monday.",
)

print(f"\nAll play invoices saved to: {OUT}")
