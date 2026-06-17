"""Full reset + reseed for the Railway demo account.

Fixes negative/messy stock from testing, then reseeds with 60 days of
clean sales history, invoices, orders, report, and RAG index.

Run via Railway CLI:
    railway run python sample_data/reset_and_reseed.py
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.business import Business, Supplier
from app.models.document import Document
from app.models.invoice import Invoice, InvoiceItem
from app.models.order import Order, OrderItem
from app.models.product import InventoryMovement, Product
from app.models.report import Report
from app.models.sales import Sale

random.seed(42)

DAYS = 60

# anomaly="drop"  → near-zero sales in last 7 days  (triggers z < -2 alert)
# anomaly="spike" → 4x normal sales in last 7 days  (triggers z > +2 alert)
# Both also shift the 7-day distribution vs 60-day baseline → PSI > 0.20 (drift alert)
PRODUCTS = {
    "Monopoly Board Game":    dict(cost=8.50,  sell=15.00, reorder=10, stock=120, base=3.0,  weekend=1.5, noise=0.5),
    "Power Bank 10000mAh":    dict(cost=15.00, sell=28.00, reorder=10, stock=80,  base=2.5,  weekend=1.0, noise=0.5),
    "Pepsi 330ml":            dict(cost=0.42,  sell=0.75,  reorder=20, stock=360, base=12.0, weekend=4.0, noise=2.0, anomaly="spike"),
    "Lays Chips 45g":         dict(cost=0.80,  sell=1.25,  reorder=20, stock=150, base=8.0,  weekend=3.0, noise=1.5),
    "Water 1.5L":             dict(cost=0.25,  sell=0.50,  reorder=15, stock=198, base=10.0, weekend=2.0, noise=2.0),
    "Nutella 400g":           dict(cost=3.10,  sell=5.50,  reorder=10, stock=45,  base=3.2,  weekend=1.0, noise=0.8, anomaly="drop"),
    "Nescafe Classic 200g":   dict(cost=4.20,  sell=7.00,  reorder=8,  stock=60,  base=2.5,  weekend=0.5, noise=0.5),
    "Black Hoodie":           dict(cost=12.00, sell=25.00, reorder=8,  stock=40,  base=1.5,  weekend=1.0, noise=0.5),
    "White T-Shirt":          dict(cost=5.50,  sell=12.00, reorder=8,  stock=35,  base=2.0,  weekend=1.5, noise=0.5),
    "iPhone Charger":         dict(cost=4.00,  sell=9.00,  reorder=10, stock=55,  base=2.0,  weekend=0.5, noise=0.3),
    "Bluetooth Earbuds":      dict(cost=18.00, sell=35.00, reorder=5,  stock=30,  base=1.0,  weekend=0.5, noise=0.3),
    "Lego Classic Brick Set": dict(cost=22.00, sell=40.00, reorder=5,  stock=25,  base=0.8,  weekend=1.0, noise=0.3),
    "Printed Tote Bag":       dict(cost=3.00,  sell=8.00,  reorder=10, stock=60,  base=1.5,  weekend=1.0, noise=0.4),
    "Cap":                    dict(cost=4.00,  sell=10.00, reorder=8,  stock=40,  base=1.2,  weekend=0.8, noise=0.3),
    "Jacket":                 dict(cost=25.00, sell=55.00, reorder=5,  stock=20,  base=0.8,  weekend=0.5, noise=0.3),
}

ORDERS = [
    dict(
        source="whatsapp",
        raw_message="Salam, bddi 3 Monopoly Board Game, delivery to Hamra, cash on delivery",
        delivery_area="Hamra",
        payment_method="cash_on_delivery",
        status="pending",
        items=[dict(product_name="Monopoly Board Game", quantity=3)],
    ),
    dict(
        source="instagram",
        raw_message="Hi! Can I get 5x Pepsi 330ml and 2x Nutella 400g delivered to Achrafieh? Bank transfer ok",
        delivery_area="Achrafieh",
        payment_method="bank_transfer",
        status="confirmed",
        items=[
            dict(product_name="Pepsi 330ml",  quantity=5),
            dict(product_name="Nutella 400g", quantity=2),
        ],
    ),
]


_ANOMALY_START = date.today() - timedelta(days=7)


def _daily_qty(cfg, d: date) -> int:
    anomaly = cfg.get("anomaly")
    if anomaly and d >= _ANOMALY_START:
        if anomaly == "drop":
            # Near-zero sales — clear below-baseline signal
            return max(0, round(random.gauss(0.2, 0.2)))
        if anomaly == "spike":
            # 4× normal — clear above-baseline signal
            return max(0, round(cfg["base"] * 4 + random.gauss(0, cfg["noise"])))
    weekend = cfg["weekend"] if d.weekday() >= 5 else 0.0
    return max(0, round(cfg["base"] + weekend + random.gauss(0, cfg["noise"])))


def _upsert_supplier(db, business_id, name) -> Supplier:
    s = db.execute(
        select(Supplier).where(Supplier.business_id == business_id, Supplier.name == name)
    ).scalar_one_or_none()
    if s is None:
        s = Supplier(business_id=business_id, name=name)
        db.add(s)
        db.flush()
    return s


def main():
    db = SessionLocal()
    try:
        today = date.today()

        # Try to find souk tyre by name (case-insensitive); fall back to first business
        business = db.execute(
            select(Business).where(func.lower(Business.name).contains("tyre"))
        ).scalar_one_or_none()
        if business is None:
            business = db.execute(
                select(Business).where(func.lower(Business.name).contains("souk"))
            ).scalar_one_or_none()
        if business is None:
            business = db.execute(select(Business).limit(1)).scalar_one_or_none()
        if business is None:
            raise RuntimeError("No business found in DB — has the app been set up?")

        bid = business.id
        print(f"Business: '{business.name}' (id={bid})")

        # ── 1. Hard-reset ALL products to clean stock ─────────────────────────
        all_products = db.execute(select(Product).where(Product.business_id == bid)).scalars().all()
        for p in all_products:
            cfg = PRODUCTS.get(p.name)
            if cfg:
                p.current_stock = cfg["stock"]
                p.reorder_level = cfg["reorder"]
                p.cost_price    = cfg["cost"]
                p.selling_price = cfg["sell"]
            elif (p.current_stock or 0) < 0:
                p.current_stock = 0  # floor any unknown product at 0
        db.flush()
        print(f"[1] Reset stock on {len(all_products)} existing products")

        # ── 2. Upsert canonical product list ──────────────────────────────────
        products: dict[str, Product] = {}
        for name, cfg in PRODUCTS.items():
            p = db.execute(
                select(Product).where(Product.business_id == bid, Product.name == name)
            ).scalar_one_or_none()
            if p is None:
                p = Product(business_id=bid, name=name,
                            current_stock=cfg["stock"],
                            reorder_level=cfg["reorder"],
                            cost_price=cfg["cost"],
                            selling_price=cfg["sell"])
                db.add(p)
                db.flush()
            products[name] = p
        print(f"[2] {len(products)} products upserted")

        # ── 3. Wipe inventory movements (stale from testing) ──────────────────
        product_ids = [p.id for p in products.values()]
        db.query(InventoryMovement).filter(
            InventoryMovement.product_id.in_(product_ids)
        ).delete(synchronize_session=False)
        db.flush()
        print("[3] Inventory movements cleared")

        # ── 4. Rebuild 60-day sales history ───────────────────────────────────
        db.query(Sale).filter(
            Sale.product_id.in_(product_ids), Sale.source == "seed"
        ).delete(synchronize_session=False)
        start = today - timedelta(days=DAYS - 1)
        total_sales = 0
        for name, cfg in PRODUCTS.items():
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
        print(f"[4] {total_sales} sales rows rebuilt over {DAYS} days")

        # ── 5. Rebuild invoices ───────────────────────────────────────────────
        supplier = _upsert_supplier(db, bid, "Cedar Wholesale Trading")
        old_inv_ids = db.execute(
            select(Invoice.id).where(Invoice.business_id == bid, Invoice.supplier_id == supplier.id)
        ).scalars().all()
        if old_inv_ids:
            db.query(InvoiceItem).filter(InvoiceItem.invoice_id.in_(old_inv_ids)).delete(synchronize_session=False)
            db.query(Invoice).filter(Invoice.id.in_(old_inv_ids)).delete(synchronize_session=False)
            db.flush()

        inv_items = [
            ("Monopoly Board Game", 50, 8.50),
            ("Power Bank 10000mAh", 30, 15.00),
            ("Pepsi 330ml", 240, 0.38),
            ("Nutella 400g", 50, 2.90),
        ]
        inv_items_new = [
            ("Monopoly Board Game", 50, 8.50),
            ("Power Bank 10000mAh", 30, 15.00),
            ("Pepsi 330ml", 240, 0.42),   # +10.5% → alert
            ("Nutella 400g", 50, 3.10),   # +6.9%  → alert
        ]

        def _make_invoice(inv_date, items_cfg, prev_prices=None):
            total = sum(qty * price for _, qty, price in items_cfg)
            inv = Invoice(
                business_id=bid, supplier_id=supplier.id,
                invoice_date=inv_date, invoice_total=round(total, 2),
                currency="USD", raw_ocr_text="[seeded]",
                extracted_json={"seeded": True}, status="processed",
            )
            db.add(inv); db.flush()
            for pname, qty, unit_price in items_cfg:
                pct = None
                if prev_prices and pname in prev_prices:
                    old = prev_prices[pname]
                    pct = round((unit_price - old) / old * 100, 1) if old else None
                prod = products.get(pname)
                db.add(InvoiceItem(
                    invoice_id=inv.id, product_id=prod.id if prod else None,
                    product_name=pname, quantity=qty, unit_price=unit_price,
                    total=round(qty * unit_price, 2), price_change_pct=pct,
                ))
            db.flush()
            return inv

        inv1 = _make_invoice(today - timedelta(days=28), inv_items)
        prev = {pname: price for pname, _, price in inv_items}
        inv2 = _make_invoice(today - timedelta(days=3), inv_items_new, prev_prices=prev)
        print(f"[5] 2 invoices created (#{inv1.id} baseline, #{inv2.id} with price alerts)")

        # ── 6. Rebuild orders ─────────────────────────────────────────────────
        old_order_ids = db.execute(
            select(Order.id).where(
                Order.business_id == bid,
                Order.source.in_(["whatsapp", "instagram"]),
            )
        ).scalars().all()
        if old_order_ids:
            db.query(OrderItem).filter(OrderItem.order_id.in_(old_order_ids)).delete(synchronize_session=False)
            db.query(Order).filter(Order.id.in_(old_order_ids)).delete(synchronize_session=False)
            db.flush()

        for odata in ORDERS:
            extracted = {
                "intent": "new_order",
                "items": [{"product": it["product_name"], "quantity": it["quantity"], "color": None, "size": None} for it in odata["items"]],
                "delivery_area": odata["delivery_area"],
                "payment_method": odata["payment_method"],
                "notes": None,
            }
            order = Order(
                business_id=bid, source=odata["source"],
                raw_message=odata["raw_message"],
                extracted_json=extracted,
                delivery_area=odata["delivery_area"],
                payment_method=odata["payment_method"],
                status=odata["status"],
            )
            db.add(order); db.flush()
            for it in odata["items"]:
                prod = products.get(it["product_name"])
                db.add(OrderItem(
                    order_id=order.id,
                    product_id=prod.id if prod else None,
                    product_name=it["product_name"],
                    quantity=it["quantity"],
                ))
            db.flush()

        db.commit()
        print(f"[6] {len(ORDERS)} orders created")

        # ── 7. Wipe old reports + RAG docs ────────────────────────────────────
        db.query(Report).filter(Report.business_id == bid).delete(synchronize_session=False)
        db.query(Document).filter(Document.business_id == bid).delete(synchronize_session=False)
        db.commit()
        print("[7] Old reports and RAG documents cleared")

        # ── 8. Forecasting retrain ────────────────────────────────────────────
        try:
            from app.services import forecasting_service
            result = forecasting_service.train_and_save(db, bid)
            print(f"[8] Forecasting retrained: {result.get('best_model') or result.get('model_name', '?')}")
        except Exception as e:
            print(f"[8] Forecasting retrain skipped: {e}")

        # ── 9. Weekly report ──────────────────────────────────────────────────
        try:
            from app.services import report_service
            rep = report_service.generate(db, bid)
            db.commit()
            print(f"[9] Weekly report generated (id={rep.id})")
        except Exception as e:
            print(f"[9] Report generation skipped: {e}")

        # ── 10. RAG reindex ───────────────────────────────────────────────────
        try:
            from app.services import rag_service
            idx = rag_service.index_all(db, bid)
            db.commit()
            print(f"[10] RAG reindexed: {idx['documents_indexed']} docs, {idx['chunks_indexed']} chunks")
        except Exception as e:
            print(f"[10] RAG reindex skipped: {e}")

        # ── 11. Drift check ───────────────────────────────────────────────────
        try:
            from app.services import drift_service
            sig = drift_service.run_drift_check(db)
            db.commit()
            print(f"[11] Drift check: PSI={sig.psi_score:.4f} status={sig.status}")
        except Exception as e:
            print(f"[11] Drift check skipped: {e}")

        # ── Summary ───────────────────────────────────────────────────────────
        print("\nStock summary:")
        for name, p in products.items():
            status = "LOW" if (p.current_stock or 0) <= (p.reorder_level or 0) else "ok"
            print(f"  {name:<25} stock={p.current_stock:>4}  reorder={p.reorder_level:>3}  [{status}]")

    finally:
        db.close()


if __name__ == "__main__":
    main()
