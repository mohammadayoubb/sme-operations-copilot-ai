"""Restock Jacket by 100 units.

Line item "Jacket" matches the seeded product exactly (score 100 >= 85),
so on upload it adds +100 to stock (2 -> 102), clearing the LOW alert.
Unit price $25.00 matches the seed cost, no price-increase alert.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

OUT = os.path.join(os.path.dirname(__file__), "test_invoices", "play")
os.makedirs(OUT, exist_ok=True)
W, H = A4

def line(c, y):
    c.line(2 * cm, y, W - 2 * cm, y)

path = os.path.join(OUT, "jacket_restock_100.pdf")
c = canvas.Canvas(path, pagesize=A4)

# Header
c.setFont("Helvetica-Bold", 18)
c.drawString(2 * cm, H - 2 * cm, "Cedar Wholesale Trading")
c.setFont("Helvetica", 9)
c.setFillColorRGB(0.4, 0.4, 0.4)
c.drawString(2 * cm, H - 2.6 * cm, "Dora Highway, Beirut, Lebanon  |  TIN: LB-2011-00219")
c.drawString(2 * cm, H - 3.0 * cm, "Tel: +961 1 255 880  |  orders@cedarwholesale.lb")
c.setFillColorRGB(0, 0, 0)
c.setFont("Helvetica-Bold", 24)
c.setFillColorRGB(0.13, 0.13, 0.13)
c.drawRightString(W - 2 * cm, H - 2 * cm, "INVOICE")
c.setFont("Helvetica", 10)
c.setFillColorRGB(0.4, 0.4, 0.4)
c.drawRightString(W - 2 * cm, H - 2.7 * cm, "Invoice #:  CWT-2026-0464")
c.drawRightString(W - 2 * cm, H - 3.1 * cm, "Date:         2026-06-17")
c.drawRightString(W - 2 * cm, H - 3.5 * cm, "Due Date:  2026-07-02")
c.setFillColorRGB(0, 0, 0)
line(c, H - 3.9 * cm)

# Bill to
y = H - 4.5 * cm
c.setFont("Helvetica-Bold", 9)
c.setFillColorRGB(0.4, 0.4, 0.4)
c.drawString(2 * cm, y, "BILL TO")
c.setFont("Helvetica-Bold", 11)
c.setFillColorRGB(0, 0, 0)
c.drawString(2 * cm, y - 0.5 * cm, "Souk Tripoli")
c.setFont("Helvetica", 10)
c.setFillColorRGB(0.3, 0.3, 0.3)
c.drawString(2 * cm, y - 1.0 * cm, "Mina Road, Tripoli, Lebanon")
c.setFillColorRGB(0, 0, 0)

# Table header
y = H - 6.5 * cm
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

# Single line item
y -= 0.6 * cm
qty, price = 100, 25.00
total = qty * price
c.setFillColorRGB(0.97, 0.97, 0.97)
c.rect(2 * cm, y - 0.45 * cm, W - 4 * cm, 0.5 * cm, fill=1, stroke=0)
c.setFont("Helvetica", 9)
c.setFillColorRGB(0.15, 0.15, 0.15)
c.drawString(2.3 * cm, y - 0.2 * cm, "Jacket")
c.drawString(10 * cm, y - 0.2 * cm, str(qty))
c.drawString(12.5 * cm, y - 0.2 * cm, "pcs")
c.drawString(14.5 * cm, y - 0.2 * cm, f"${price:.2f}")
c.drawRightString(W - 2.3 * cm, y - 0.2 * cm, f"${total:.2f}")
c.setFillColorRGB(0, 0, 0)

# Totals
y -= 0.9 * cm
line(c, y)
y -= 0.4 * cm
tax = total * 11 / 100
grand = total + tax
c.setFont("Helvetica", 10)
c.setFillColorRGB(0.3, 0.3, 0.3)
c.drawRightString(W - 5.5 * cm, y, "Subtotal:")
c.drawRightString(W - 2 * cm, y, f"USD {total:.2f}")
y -= 0.55 * cm
c.drawRightString(W - 5.5 * cm, y, "VAT (11%):")
c.drawRightString(W - 2 * cm, y, f"USD {tax:.2f}")
y -= 0.1 * cm
line(c, y)
y -= 0.55 * cm
c.setFont("Helvetica-Bold", 12)
c.setFillColorRGB(0, 0, 0)
c.drawRightString(W - 5.5 * cm, y, "TOTAL DUE:")
c.drawRightString(W - 2 * cm, y, f"USD {grand:.2f}")

# Footer
c.setFont("Helvetica-Oblique", 8)
c.setFillColorRGB(0.5, 0.5, 0.5)
c.drawCentredString(W / 2, 2 * cm, "Restock order. Payment via bank transfer to BLOM Bank.")
c.drawCentredString(W / 2, 1.5 * cm, "Thank you for your business!")
c.save()
print(f"Created: {path}")
