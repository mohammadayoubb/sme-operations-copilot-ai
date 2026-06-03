"""Full demo seed — run this once before the demo dry-run.

Idempotent: safe to re-run. Wipes previously seeded data and rebuilds cleanly.

Run inside the backend container:

    docker compose exec -T backend python - < sample_data/seed_demo.py

What it seeds:
  1. Business + 2 suppliers
  2. 7 products (groceries + apparel) with realistic stock levels
  3. 60 days of sales history with weekly seasonality
  4. 2 invoices from the same supplier — second one has price increases (demo alert)
  5. 3 orders (WhatsApp / Instagram / manual)
  6. Weekly report (AI-generated narrative)
  7. Forecasting model retrain
  8. RAG document reindex
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.business import Business, Supplier
from app.models.invoice import Invoice, InvoiceItem
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.sales import Sale
from app.repositories.product_repo import get_or_create_default_business

random.seed(42)

# ── Config ────────────────────────────────────────────────────────────

DAYS = 60

# name → (cost, sell, reorder_level, final_stock, base/day, weekend_bump, noise_sd)
GROCERY_PRODUCTS = {
    "Pepsi 330ml":    dict(cost=0.42, sell=0.75, reorder=20, stock=120, base=12.0, weekend=4.0, noise=2.0),
    "Lays Chips 45g": dict(cost=0.80, sell=1.25, reorder=20, stock=30,  base=8.0,  weekend=3.0, noise=1.5),
    "Water 1.5L":     dict(cost=0.25, sell=0.50, reorder=15, stock=18,  base=10.0, weekend=2.0, noise=2.0),
    "Nutella 400g":   dict(cost=3.10, sell=5.50, reorder=10, stock=8,   base=3.2,  weekend=1.0, noise=0.8),
    "Nescafé 200g":   dict(cost=4.20, sell=7.00, reorder=8,  stock=45,  base=2.5,  weekend=0.5, noise=0.5),
}

APPAREL_PRODUCTS = {
    "Black Hoodie":   dict(cost=12.00, sell=25.00, reorder=5, stock=14, base=1.5, weekend=1.0, noise=0.5),
    "White T-Shirt":  dict(cost=5.50,  sell=12.00, reorder=8, stock=6,  base=2.0, weekend=1.5, noise=0.5),
}

ALL_PRODUCTS = {**GROCERY_PRODUCTS, **APPAREL_PRODUCTS}

# Invoices: two from ABC Foods, showing a price hike on the second one.
# old_price → new_price (used to compute price_change_pct)
INVOICE_ITEMS_OLD = [
    # (product_name, qty, old_unit_price)
    ("Pepsi 330ml",    240, 0.38),
    ("Nutella 400g",    50, 2.90),
    ("Water 1.5L",     300, 0.22),
    ("Nescafé 200g",    40, 3.80),
]

INVOICE_ITEMS_NEW = [
    # (product_name, qty, new_unit_price)
    ("Pepsi 330ml",    240, 0.42),   # +10.5% → triggers alert
    ("Nutella 400g",    50, 3.10),   # +6.9%  → triggers alert
    ("Water 1.5L",     300, 0.25),   # +13.6% → triggers alert
    ("Nescafé 200g",    40, 3.80),   # 0%     → no alert
]

ORDERS = [
    dict(
        source="whatsapp",
        raw_message="Salam, bddi 3 black hoodies size L w 2 white ones size M, delivery to Hamra, cash on delivery",
        delivery_area="Hamra",
        payment_method="cash_on_delivery",
        status="pending",
        items=[
            dict(product_name="Black Hoodie", quantity=3, color="black", size="L"),
            dict(product_name="Black Hoodie", quantity=2, color="white", size="M"),
        ],
    ),
    dict(
        source="instagram",
        raw_message="Hi! Can I get 5x Pepsi 330ml and 2x Nutella 400g delivered to Achrafieh? Bank transfer ok",
        delivery_area="Achrafieh",
        payment_method="bank_transfer",
        status="confirmed",
        items=[
            dict(product_name="Pepsi 330ml",  quantity=5, color=None, size=None),
            dict(product_name="Nutella 400g", quantity=2, color=None, size=None),
        ],
    ),
    dict(
        source="whatsapp",
        raw_message="3andi order: 4 white t-shirts size S w 1 black hoodie size XL, deliver Dbayeh, cash",
        delivery_area="Dbayeh",
        payment_method="cash_on_delivery",
        status="fulfilled",
        items=[
            dict(product_name="White T-Shirt", quantity=4, color="white", size="S"),
            dict(product_name="Black Hoodie",  quantity=1, color="black", size="XL"),
        ],
    ),
]


# ── Helpers ───────────────────────────────────────────────────────────

def _upsert_product(db, business_id, name, cfg) -> Product:
    product = db.execute(
        select(Product).where(Product.business_id == business_id, Product.name == name)
    ).scalar_one_or_none()
    if product is None:
        product = Product(business_id=business_id, name=name, current_stock=0)
        db.add(product)
        db.flush()
    product.cost_price = cfg["cost"]
    product.selling_price = cfg["sell"]
    product.reorder_level = cfg["reorder"]
    product.current_stock = cfg["stock"]
    return product


def _daily_qty(cfg, day: date) -> int:
    weekend = cfg["weekend"] if day.weekday() >= 5 else 0.0
    qty = cfg["base"] + weekend + random.gauss(0, cfg["noise"])
    return max(0, round(qty))


def _upsert_supplier(db, business_id, name, contact="") -> Supplier:
    s = db.execute(
        select(Supplier).where(Supplier.business_id == business_id, Supplier.name == name)
    ).scalar_one_or_none()
    if s is None:
        s = Supplier(business_id=business_id, name=name, contact=contact)
        db.add(s)
        db.flush()
    return s


# ── Main ──────────────────────────────────────────────────────────────

def main() -> None:
    db = SessionLocal()
    try:
        today = date.today()

        # 1. Business
        business = get_or_create_default_business(db)
        bid = business.id
        print(f"[1/8] Business: '{business.name}' (id={bid})")

        # 2. Suppliers
        supplier_abc = _upsert_supplier(db, bid, "ABC Foods Trading", "abc@example.com")
        _upsert_supplier(db, bid, "Fresh Market Distributors", "fresh@example.com")
        db.flush()
        print(f"[2/8] Suppliers upserted (ABC Foods id={supplier_abc.id})")

        # 3. Products
        products: dict[str, Product] = {}
        for name, cfg in ALL_PRODUCTS.items():
            products[name] = _upsert_product(db, bid, name, cfg)
        db.flush()
        print(f"[3/8] {len(products)} products upserted")

        # 4. Sales history (60 days)
        seeded_ids = [p.id for p in products.values()]
        db.query(Sale).filter(
            Sale.product_id.in_(seeded_ids), Sale.source == "seed"
        ).delete(synchronize_session=False)

        start = today - timedelta(days=DAYS - 1)
        total_sales = 0
        for name, cfg in ALL_PRODUCTS.items():
            product = products[name]
            for i in range(DAYS):
                d = start + timedelta(days=i)
                qty = _daily_qty(cfg, d)
                if qty == 0:
                    continue
                db.add(Sale(
                    business_id=bid,
                    product_id=product.id,
                    quantity=qty,
                    unit_price=cfg["sell"],
                    total=round(qty * cfg["sell"], 2),
                    sale_date=d,
                    source="seed",
                ))
                total_sales += 1
        db.flush()
        print(f"[4/8] {total_sales} sales rows over {DAYS} days")

        # 5. Invoices (delete old seeded ones first)
        old_inv_ids = db.execute(
            select(Invoice.id).where(
                Invoice.business_id == bid,
                Invoice.supplier_id == supplier_abc.id,
            )
        ).scalars().all()
        if old_inv_ids:
            db.query(InvoiceItem).filter(InvoiceItem.invoice_id.in_(old_inv_ids)).delete(
                synchronize_session=False
            )
            db.query(Invoice).filter(Invoice.id.in_(old_inv_ids)).delete(
                synchronize_session=False
            )
            db.flush()

        def _make_invoice(inv_date, items_cfg, prev_prices=None):
            total = sum(qty * price for _, qty, price in items_cfg)
            inv = Invoice(
                business_id=bid,
                supplier_id=supplier_abc.id,
                invoice_date=inv_date,
                invoice_total=round(total, 2),
                currency="USD",
                raw_ocr_text="[seeded]",
                extracted_json={"seeded": True},
                status="processed",
            )
            db.add(inv)
            db.flush()
            for pname, qty, unit_price in items_cfg:
                pct = None
                if prev_prices and pname in prev_prices:
                    old = prev_prices[pname]
                    pct = round((unit_price - old) / old * 100, 1) if old else None
                prod = products.get(pname)
                db.add(InvoiceItem(
                    invoice_id=inv.id,
                    product_id=prod.id if prod else None,
                    product_name=pname,
                    quantity=qty,
                    unit_price=unit_price,
                    total=round(qty * unit_price, 2),
                    price_change_pct=pct,
                ))
            db.flush()
            return inv

        inv1_date = today - timedelta(days=28)
        inv1 = _make_invoice(inv1_date, INVOICE_ITEMS_OLD)

        prev = {pname: price for pname, _, price in INVOICE_ITEMS_OLD}
        inv2_date = today - timedelta(days=3)
        inv2 = _make_invoice(inv2_date, INVOICE_ITEMS_NEW, prev_prices=prev)

        db.flush()
        print(f"[5/8] 2 invoices created (#{inv1.id} baseline, #{inv2.id} with price increases)")

        # 6. Orders — delete items before orders (FK constraint)
        old_order_ids = db.execute(
            select(Order.id).where(
                Order.business_id == bid,
                Order.source.in_(["whatsapp", "instagram"]),
            )
        ).scalars().all()
        if old_order_ids:
            db.query(OrderItem).filter(OrderItem.order_id.in_(old_order_ids)).delete(
                synchronize_session=False
            )
            db.query(Order).filter(Order.id.in_(old_order_ids)).delete(
                synchronize_session=False
            )
        db.flush()

        for odata in ORDERS:
            extracted = {
                "intent": "new_order",
                "items": [
                    {"product": it["product_name"], "quantity": it["quantity"],
                     "color": it.get("color"), "size": it.get("size")}
                    for it in odata["items"]
                ],
                "delivery_area": odata["delivery_area"],
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
                prod = products.get(it["product_name"])
                db.add(OrderItem(
                    order_id=order.id,
                    product_id=prod.id if prod else None,
                    product_name=it["product_name"],
                    quantity=it["quantity"],
                    color=it.get("color"),
                    size=it.get("size"),
                ))
            db.flush()

        db.commit()
        print(f"[6/8] {len(ORDERS)} orders created")

        # 7. Forecasting retrain
        try:
            from app.services import forecasting_service
            result = forecasting_service.train_and_save(db)
            print(f"[7/8] Forecasting retrained: {result.get('best_model', '?')}")
        except Exception as e:
            print(f"[7/8] Forecasting retrain skipped: {e}")

        # 8. Weekly report
        try:
            from app.services import report_service
            rep = report_service.generate(db)
            db.commit()
            print(f"[8/8] Weekly report generated (id={rep.id})")
        except Exception as e:
            print(f"[8/8] Report generation skipped: {e}")

        # 9. RAG reindex
        try:
            from app.services import rag_service
            idx = rag_service.index_all(db)
            db.commit()
            print(f"      RAG reindexed: {idx['documents_indexed']} docs, {idx['chunks_indexed']} chunks")
        except Exception as e:
            print(f"      RAG reindex skipped: {e}")

        print("\nDemo seed complete. Summary:")
        for name, p in products.items():
            status = "LOW" if p.current_stock <= p.reorder_level else "ok"
            print(f"  {name:<22} stock={p.current_stock:>4}  reorder={p.reorder_level:>3}  [{status}]")

    finally:
        db.close()


if __name__ == "__main__":
    main()
