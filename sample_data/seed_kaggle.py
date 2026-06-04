"""
Kaggle Retail Inventory seed — replace synthetic data with real demand patterns.

Dataset: kaggle.com/datasets/anirudhchauhan/retail-store-inventory-forecasting-dataset
  20 products · 5 stores · 731 days (2022-01-01 → 2024-01-01)
  Columns: Date, Store ID, Product ID, Category, Region, Inventory Level,
           Units Sold, Units Ordered, Demand Forecast, Price, Discount,
           Weather Condition, Holiday/Promotion, Competitor Pricing, Seasonality

Drop retail_inventory.csv in sample_data/, then run inside the backend container:

    docker compose exec -T backend python - < sample_data/seed_kaggle.py

What it seeds:
  1.  Business + 2 suppliers
  2.  20 named products with computed cost/selling prices + live stock levels
  3.  ~13 000+ sales rows (731-day real-pattern history from store S001)
  4.  2 invoices from the same supplier — second has deliberate price hikes
  5.  3 orders (WhatsApp / Instagram / manual)
  6.  Forecasting retrain   (now trained on 731 days vs 60 synthetic days)
  7.  Weekly report
  8.  RAG reindex
"""
from __future__ import annotations

import csv
import os
import statistics
from datetime import date, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.business import Supplier
from app.models.invoice import Invoice, InvoiceItem
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.sales import Sale
from app.repositories.product_repo import get_or_create_default_business

# ── Locate CSV ────────────────────────────────────────────────────────

_SEARCH = [
    "/app/sample_data/retail_inventory.csv",
    os.path.join(os.getcwd(), "sample_data", "retail_inventory.csv"),
    os.path.join(os.getcwd(), "retail_inventory.csv"),
]
CSV_PATH = next((p for p in _SEARCH if os.path.exists(p)), _SEARCH[0])

STORE_ID   = "S001"
SOURCE_TAG = "seed_kaggle"

# ── Product name mapping ──────────────────────────────────────────────

PRODUCT_NAMES: dict[str, str] = {
    "P0001": "Nescafé Classic 200g",
    "P0002": "Lego Classic Bricks Set",
    "P0003": "Monopoly Board Game",
    "P0004": "1000-Piece Puzzle",
    "P0005": "USB-C Fast Charger",
    "P0006": "Candia Full Cream Milk 1L",
    "P0007": "Moleskine Notebook A5",
    "P0008": "Black Hoodie",
    "P0009": "Bluetooth Earbuds",
    "P0010": "Toy Car Collection",
    "P0011": "Insulated Water Bottle",
    "P0012": "White T-Shirt",
    "P0013": "Art & Craft Kit",
    "P0014": "Denim Jeans",
    "P0015": "Cargo Shorts",
    "P0016": "Power Bank 10000mAh",
    "P0017": "Play-Doh Set 10 Colors",
    "P0018": "Polo Shirt",
    "P0019": "Printed Tote Bag",
    "P0020": "UNO Card Game",
}

# Gross margin by category: cost_price = selling_price × (1 − margin)
MARGIN: dict[str, float] = {
    "Groceries":   0.40,
    "Electronics": 0.35,
    "Clothing":    0.50,
    "Toys":        0.40,
    "Furniture":   0.45,
}

# ── CSV helpers ───────────────────────────────────────────────────────

def _load_store(path: str, store: str) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["Store ID"] == store:
                rows.append(row)
    return rows


def _product_stats(rows: list[dict]) -> dict[str, dict]:
    """Per-product: category, median selling price, avg daily units, last inventory."""
    acc: dict[str, dict] = {}
    for row in rows:
        pid = row["Product ID"]
        if pid not in acc:
            acc[pid] = {
                "category": row["Category"],
                "prices":   [],
                "units":    [],
                "inv":      {},
            }
        acc[pid]["prices"].append(float(row["Price"]))
        acc[pid]["units"].append(int(row["Units Sold"]))
        acc[pid]["inv"][row["Date"]] = int(row["Inventory Level"])

    out = {}
    for pid, d in acc.items():
        last_date = max(d["inv"])
        out[pid] = {
            "category":    d["category"],
            "med_price":   round(statistics.median(d["prices"]), 2),
            "avg_units":   statistics.mean(d["units"]),
            "last_stock":  d["inv"][last_date],
        }
    return out

# ── DB helpers ────────────────────────────────────────────────────────

def _upsert_supplier(db, business_id: int, name: str, contact: str = "") -> Supplier:
    s = db.execute(
        select(Supplier).where(Supplier.business_id == business_id, Supplier.name == name)
    ).scalar_one_or_none()
    if s is None:
        s = Supplier(business_id=business_id, name=name, contact=contact)
        db.add(s)
        db.flush()
    return s


def _upsert_product(db, business_id: int, name: str,
                    sell: float, cost: float, stock: int, reorder: int) -> Product:
    p = db.execute(
        select(Product).where(Product.business_id == business_id, Product.name == name)
    ).scalar_one_or_none()
    if p is None:
        p = Product(business_id=business_id, name=name, current_stock=0)
        db.add(p)
        db.flush()
    p.selling_price = round(sell, 2)
    p.cost_price    = round(cost, 2)
    p.current_stock = stock
    p.reorder_level = reorder
    return p

# ── Main ──────────────────────────────────────────────────────────────

def main() -> None:
    db = SessionLocal()
    try:
        today = date.today()

        # ── 1. Business ──────────────────────────────────────────────
        business = get_or_create_default_business(db)
        bid = business.id
        print(f"[1/8] Business: '{business.name}'  (id={bid})")

        # ── 2. Suppliers ─────────────────────────────────────────────
        supplier = _upsert_supplier(db, bid, "Al-Manar Trading Co.", "almanar@example.com")
        _upsert_supplier(db, bid, "Beirut Wholesale Supplies", "bws@example.com")
        db.flush()
        print(f"[2/8] Suppliers upserted  (Al-Manar id={supplier.id})")

        # ── 3. Products ───────────────────────────────────────────────
        print(f"[3/8] Reading {CSV_PATH} …")
        if not os.path.exists(CSV_PATH):
            raise FileNotFoundError(
                f"CSV not found at {CSV_PATH}. "
                "Drop retail_inventory.csv in sample_data/ and try again."
            )

        rows  = _load_store(CSV_PATH, STORE_ID)
        stats = _product_stats(rows)

        product_objs: dict[str, Product] = {}
        for pid, s in sorted(stats.items()):
            name    = PRODUCT_NAMES.get(pid, pid)
            sell    = s["med_price"]
            cost    = round(sell * (1.0 - MARGIN.get(s["category"], 0.40)), 2)
            stock   = s["last_stock"]
            reorder = max(10, round(s["avg_units"] * 1.5))
            product_objs[pid] = _upsert_product(db, bid, name, sell, cost, stock, reorder)

        db.flush()
        print(f"      {len(product_objs)} products upserted")

        # ── 4. Sales — 731 days ───────────────────────────────────────
        seeded_ids = [p.id for p in product_objs.values()]
        db.query(Sale).filter(
            Sale.product_id.in_(seeded_ids), Sale.source == SOURCE_TAG
        ).delete(synchronize_session=False)
        db.flush()

        n_sales = 0
        for row in rows:
            qty = int(row["Units Sold"])
            if qty == 0:
                continue
            prod = product_objs.get(row["Product ID"])
            if prod is None:
                continue
            price    = float(row["Price"])
            disc_pct = float(row["Discount"]) / 100.0
            eff      = round(price * (1.0 - disc_pct), 4)
            db.add(Sale(
                business_id=bid,
                product_id=prod.id,
                quantity=float(qty),
                unit_price=eff,
                total=round(qty * eff, 2),
                sale_date=date.fromisoformat(row["Date"]),
                source=SOURCE_TAG,
            ))
            n_sales += 1

        db.flush()
        print(f"[4/8] {n_sales:,} sales rows inserted  (731 days · store {STORE_ID})")

        # ── 5. Invoices — price hike on second ───────────────────────
        # Use first 2 Groceries + first 2 Electronics for supplier invoice realism
        grocery_pids = [p for p, s in stats.items() if s["category"] == "Groceries"][:2]
        elec_pids    = [p for p, s in stats.items() if s["category"] == "Electronics"][:2]
        inv_pids     = (grocery_pids + elec_pids)[:4]

        # Wipe existing invoices from this supplier
        old_ids = db.execute(
            select(Invoice.id).where(
                Invoice.business_id == bid, Invoice.supplier_id == supplier.id
            )
        ).scalars().all()
        if old_ids:
            db.query(InvoiceItem).filter(InvoiceItem.invoice_id.in_(old_ids)).delete(
                synchronize_session=False
            )
            db.query(Invoice).filter(Invoice.id.in_(old_ids)).delete(
                synchronize_session=False
            )
            db.flush()

        # Each item gets a different price-hike percentage:
        # +10.5%, +6.9%, +13.6%, 0% — mirrors the original demo drama
        HIKE = [0.105, 0.069, 0.136, 0.0]

        def _inv_lines(hike_applied: bool):
            lines = []
            for i, pid in enumerate(inv_pids):
                name      = PRODUCT_NAMES.get(pid, pid)
                base_cost = float(product_objs[pid].cost_price)
                h         = HIKE[i] if i < len(HIKE) else 0.0
                if hike_applied:
                    price = round(base_cost, 2)
                else:
                    price = round(base_cost / (1.0 + h), 2) if h > 0 else round(base_cost, 2)
                lines.append((name, 50, price))
            return lines

        def _make_invoice(inv_date, lines, prev=None):
            total = sum(qty * up for _, qty, up in lines)
            inv = Invoice(
                business_id=bid,
                supplier_id=supplier.id,
                invoice_date=inv_date,
                invoice_total=round(total, 2),
                currency="USD",
                raw_ocr_text="[seeded]",
                extracted_json={"seeded": True},
                status="processed",
            )
            db.add(inv)
            db.flush()
            for pname, qty, up in lines:
                pct = None
                if prev and pname in prev and prev[pname]:
                    old = prev[pname]
                    pct = round((up - old) / old * 100, 1)
                po = next((p for p in product_objs.values() if p.name == pname), None)
                db.add(InvoiceItem(
                    invoice_id=inv.id,
                    product_id=po.id if po else None,
                    product_name=pname,
                    quantity=qty,
                    unit_price=up,
                    total=round(qty * up, 2),
                    price_change_pct=pct,
                ))
            db.flush()
            return inv

        old_lines  = _inv_lines(hike_applied=False)
        new_lines  = _inv_lines(hike_applied=True)
        inv1 = _make_invoice(today - timedelta(days=28), old_lines)
        inv2 = _make_invoice(
            today - timedelta(days=3), new_lines,
            prev={name: up for name, _, up in old_lines},
        )
        db.flush()
        print(f"[5/8] 2 invoices  (#{inv1.id} baseline · #{inv2.id} with price hikes)")

        # ── 6. Orders ─────────────────────────────────────────────────
        clothing_names = [PRODUCT_NAMES[p] for p in stats if stats[p]["category"] == "Clothing"]
        elec_names     = [PRODUCT_NAMES[p] for p in stats if stats[p]["category"] == "Electronics"]

        c1 = clothing_names[0] if len(clothing_names) > 0 else "Black Hoodie"
        c2 = clothing_names[1] if len(clothing_names) > 1 else "White T-Shirt"
        c3 = clothing_names[4] if len(clothing_names) > 4 else clothing_names[-1]
        e1 = elec_names[0]     if len(elec_names)     > 0 else "USB-C Fast Charger"
        e2 = elec_names[1]     if len(elec_names)     > 1 else "Bluetooth Earbuds"

        ORDERS = [
            dict(
                source="whatsapp",
                raw_message=(
                    f"Salam, bddi 3 {c1} size L w 2 {c2} size M, "
                    "delivery to Hamra, cash on delivery"
                ),
                delivery_area="Hamra",
                payment_method="cash_on_delivery",
                status="pending",
                items=[
                    dict(product_name=c1, quantity=3, color="black", size="L"),
                    dict(product_name=c2, quantity=2, color="white", size="M"),
                ],
            ),
            dict(
                source="instagram",
                raw_message=(
                    f"Hi! Can I get 2 {e1} and 1 {e2} "
                    "delivered to Achrafieh? Bank transfer ok"
                ),
                delivery_area="Achrafieh",
                payment_method="bank_transfer",
                status="confirmed",
                items=[
                    dict(product_name=e1, quantity=2, color=None, size=None),
                    dict(product_name=e2, quantity=1, color=None, size=None),
                ],
            ),
            dict(
                source="whatsapp",
                raw_message=(
                    f"3andi order: 4 {c3} size S w 1 {c1} size XL, "
                    "deliver Dbayeh, cash"
                ),
                delivery_area="Dbayeh",
                payment_method="cash_on_delivery",
                status="fulfilled",
                items=[
                    dict(product_name=c3, quantity=4, color=None, size="S"),
                    dict(product_name=c1, quantity=1, color="black", size="XL"),
                ],
            ),
        ]

        # Wipe old WhatsApp/Instagram orders
        old_order_ids = db.execute(
            select(Order.id).where(
                Order.business_id == bid,
                Order.source.in_(["whatsapp", "instagram"]),
            )
        ).scalars().all()
        if old_order_ids:
            db.query(OrderItem).filter(
                OrderItem.order_id.in_(old_order_ids)
            ).delete(synchronize_session=False)
            db.query(Order).filter(
                Order.id.in_(old_order_ids)
            ).delete(synchronize_session=False)
        db.flush()

        for odata in ORDERS:
            extracted = {
                "intent": "new_order",
                "items": [
                    {
                        "product":  it["product_name"],
                        "quantity": it["quantity"],
                        "color":    it.get("color"),
                        "size":     it.get("size"),
                    }
                    for it in odata["items"]
                ],
                "delivery_area":  odata["delivery_area"],
                "payment_method": odata["payment_method"],
                "notes": None,
            }
            order = Order(
                business_id=bid,
                source=odata["source"],
                raw_message=odata["raw_message"],
                extracted_json=extracted,
                delivery_area=odata["delivery_area"],
                payment_method=odata["payment_method"],
                status=odata["status"],
            )
            db.add(order)
            db.flush()
            for it in odata["items"]:
                po = next(
                    (p for p in product_objs.values() if p.name == it["product_name"]), None
                )
                db.add(OrderItem(
                    order_id=order.id,
                    product_id=po.id if po else None,
                    product_name=it["product_name"],
                    quantity=it["quantity"],
                    color=it.get("color"),
                    size=it.get("size"),
                ))
            db.flush()

        db.commit()
        print(f"[6/8] {len(ORDERS)} orders created")

        # ── 7. Forecasting retrain ────────────────────────────────────
        try:
            from app.services import forecasting_service
            result = forecasting_service.train_and_save(db)
            print(f"[7/8] Forecasting retrained  best_model={result.get('best_model', '?')}")
        except Exception as exc:
            print(f"[7/8] Forecasting retrain skipped: {exc}")

        # ── 8. Weekly report + RAG reindex ───────────────────────────
        try:
            from app.services import report_service
            rep = report_service.generate(db)
            db.commit()
            print(f"      Weekly report generated  (id={rep.id})")
        except Exception as exc:
            print(f"      Report skipped: {exc}")

        try:
            from app.services import rag_service
            idx = rag_service.index_all(db)
            db.commit()
            print(
                f"      RAG reindexed: {idx['documents_indexed']} docs, "
                f"{idx['chunks_indexed']} chunks"
            )
        except Exception as exc:
            print(f"      RAG reindex skipped: {exc}")

        # ── Summary ───────────────────────────────────────────────────
        print("\nKaggle seed complete — products:\n")
        print(f"  {'Name':<28} {'Sell':>7}  {'Cost':>7}  {'Stock':>5}  {'Reorder':>7}  Status")
        print(f"  {'-'*28} {'-'*7}  {'-'*7}  {'-'*5}  {'-'*7}  ------")
        for pid, p in sorted(product_objs.items()):
            flag = "LOW" if p.current_stock <= p.reorder_level else "ok"
            print(
                f"  {p.name:<28} "
                f"${float(p.selling_price):>6.2f}  "
                f"${float(p.cost_price):>6.2f}  "
                f"{int(p.current_stock):>5}  "
                f"{int(p.reorder_level):>7}  "
                f"[{flag}]"
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()
