"""Full reset + reseed for the Railway (or local) demo account.

Targets the souk_tripoli business (searches by name "tripoli" → "souk" → first).

Covers every demo feature:
  • 13 reorder alerts (5 CRITICAL stock=0, 8 LOW stock≤reorder)
  • Anomalies: Pepsi spike + Nutella drop  (triggers z-score alerts)
  • Drift alert: PSI > 0.20  (Pepsi/Nutella distort the 7-day distribution)
  • Pricing Advisor — all four velocity scenarios:
      fast  (≥5/day):   Pepsi, Water, Lays, Redbull
      medium(1-5/day):  Nescafe, Nutella, Lipton, Oreo, iPhone Charger, Hoodie, T-Shirt
      slow  (<1/day):   KitKat, Pringles, Earbuds, Power Bank, Mouse, Lego, Monopoly, Cap, Jacket
      unknown(no sales): USB-C Hub, Laptop Stand
  • Cost-trend scenarios (from invoice history):
      UP   (+10.5%): Pepsi
      DOWN (-10.7%): Water
      UP   (+6.9%):  Nutella
      FLAT:          everything else

Run on Railway:
    railway run python sample_data/reset_and_reseed.py

Run locally (Docker):
    docker-compose exec backend python sample_data/reset_and_reseed.py
"""
from __future__ import annotations

import sys
import random
from datetime import date, timedelta

from sqlalchemy import func, select

sys.stdout.reconfigure(encoding="utf-8")

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

# ─── Product catalogue ────────────────────────────────────────────────────────
# no_sales=True  → product is in inventory but has NO sales history
#                  → pricing advisor shows velocity="unknown"
# anomaly="spike" → 4× normal qty in last 7 days  (z > +2 alert)
# anomaly="drop"  → near-zero qty in last 7 days   (z < -2 alert)

PRODUCTS = {
    # ── BEVERAGES ──────────────────────────────────────────────────────────────
    # fast movers
    "Pepsi 330ml":            dict(cost=0.42,  sell=0.75,  reorder=20, stock=400, base=12.0, weekend=4.0, noise=2.0, anomaly="spike"),
    "Water 1.5L":             dict(cost=0.25,  sell=0.50,  reorder=15, stock=220, base=10.0, weekend=2.0, noise=2.0),
    "Redbull 250ml":          dict(cost=0.95,  sell=1.75,  reorder=15, stock=8,   base=6.0,  weekend=2.0, noise=1.0),  # LOW
    # medium movers
    "Nescafe Classic 200g":   dict(cost=4.20,  sell=7.00,  reorder=8,  stock=60,  base=2.5,  weekend=0.5, noise=0.5),
    "Nutella 400g":           dict(cost=3.10,  sell=5.50,  reorder=10, stock=6,   base=3.2,  weekend=1.0, noise=0.8, anomaly="drop"),  # LOW
    "Lipton Ice Tea 500ml":   dict(cost=0.65,  sell=1.20,  reorder=12, stock=0,   base=1.5,  weekend=1.0, noise=0.5),  # CRITICAL

    # ── SNACKS ─────────────────────────────────────────────────────────────────
    # fast
    "Lays Chips 45g":         dict(cost=0.80,  sell=1.25,  reorder=20, stock=180, base=8.0,  weekend=3.0, noise=1.5),
    # medium
    "Oreo Original 137g":     dict(cost=0.90,  sell=1.75,  reorder=15, stock=0,   base=1.2,  weekend=0.8, noise=0.4),  # CRITICAL
    # slow
    "KitKat 4-Finger":        dict(cost=0.55,  sell=1.00,  reorder=10, stock=0,   base=0.8,  weekend=0.5, noise=0.3),  # CRITICAL
    "Pringles Original 165g": dict(cost=1.20,  sell=2.25,  reorder=12, stock=5,   base=0.6,  weekend=0.5, noise=0.3),  # LOW

    # ── ELECTRONICS ────────────────────────────────────────────────────────────
    # medium
    "iPhone Charger":         dict(cost=4.00,  sell=9.00,  reorder=10, stock=55,  base=2.0,  weekend=0.5, noise=0.3),
    # slow
    "Bluetooth Earbuds":      dict(cost=18.00, sell=35.00, reorder=5,  stock=4,   base=0.8,  weekend=0.5, noise=0.3),  # LOW
    "Power Bank 10000mAh":    dict(cost=15.00, sell=28.00, reorder=10, stock=0,   base=0.7,  weekend=0.5, noise=0.3),  # CRITICAL
    "Wireless Mouse":         dict(cost=8.00,  sell=16.00, reorder=8,  stock=35,  base=0.3,  weekend=0.3, noise=0.2),
    # unknown movers (no sales history)
    "USB-C Hub 4-Port":       dict(cost=12.00, sell=22.00, reorder=8,  stock=7,   no_sales=True),  # LOW
    "Laptop Stand":           dict(cost=18.00, sell=35.00, reorder=5,  stock=0,   no_sales=True),  # CRITICAL

    # ── TOYS / GAMES ───────────────────────────────────────────────────────────
    "Monopoly Board Game":    dict(cost=8.50,  sell=15.00, reorder=10, stock=120, base=0.5,  weekend=1.5, noise=0.3),
    "Lego Classic Brick Set": dict(cost=22.00, sell=40.00, reorder=5,  stock=4,   base=0.8,  weekend=1.0, noise=0.3),  # LOW

    # ── APPAREL ────────────────────────────────────────────────────────────────
    "Black Hoodie":           dict(cost=12.00, sell=25.00, reorder=8,  stock=40,  base=1.5,  weekend=1.0, noise=0.5),
    "White T-Shirt":          dict(cost=5.50,  sell=12.00, reorder=8,  stock=35,  base=2.0,  weekend=1.5, noise=0.5),
    "Cap":                    dict(cost=4.00,  sell=10.00, reorder=8,  stock=3,   base=0.5,  weekend=0.8, noise=0.3),  # LOW
    "Jacket":                 dict(cost=25.00, sell=55.00, reorder=5,  stock=2,   base=0.3,  weekend=0.5, noise=0.2),  # LOW
}

# ─── Demo orders ─────────────────────────────────────────────────────────────
ORDERS = [
    dict(
        source="whatsapp",
        raw_message="Salam, bddi 2 Pepsi 330ml w Pringles, delivery to Hamra, cash on delivery",
        delivery_area="Hamra",
        payment_method="cash_on_delivery",
        status="pending",
        items=[
            dict(product_name="Pepsi 330ml",          quantity=2),
            dict(product_name="Pringles Original 165g", quantity=1),
        ],
    ),
    dict(
        source="instagram",
        raw_message="Hi! Can I get 3x Redbull and 1x Bluetooth Earbuds delivered to Achrafieh? Bank transfer",
        delivery_area="Achrafieh",
        payment_method="bank_transfer",
        status="confirmed",
        items=[
            dict(product_name="Redbull 250ml",    quantity=3),
            dict(product_name="Bluetooth Earbuds", quantity=1),
        ],
    ),
    dict(
        source="whatsapp",
        raw_message="Biddi Lego Classic w Monopoly for my son, cash, Verdun",
        delivery_area="Verdun",
        payment_method="cash_on_delivery",
        status="pending",
        items=[
            dict(product_name="Lego Classic Brick Set", quantity=1),
            dict(product_name="Monopoly Board Game",    quantity=1),
        ],
    ),
]

# ─── Invoice data ─────────────────────────────────────────────────────────────
# Two invoices from Cedar Wholesale Trading.
# Invoice 1 (baseline, 28 days ago) — older costs.
# Invoice 2 (recent, 3 days ago)    — shows price changes for Pepsi (+10.5%),
#                                     Water (-10.7%), Nutella (+6.9%).
INV_BASELINE = [
    ("Pepsi 330ml",            240, 0.38),
    ("Water 1.5L",             200, 0.28),
    ("Nutella 400g",            50, 2.90),
    ("Nescafe Classic 200g",    30, 4.20),
    ("Lays Chips 45g",         100, 0.80),
    ("Redbull 250ml",           60, 0.95),
    ("iPhone Charger",          20, 4.00),
    ("Power Bank 10000mAh",     15, 14.00),
    ("Bluetooth Earbuds",       10, 17.00),
    ("USB-C Hub 4-Port",        20, 11.00),
]
INV_RECENT = [
    ("Pepsi 330ml",            240, 0.42),   # +10.5% → cost UP
    ("Water 1.5L",             200, 0.25),   # -10.7% → cost DOWN
    ("Nutella 400g",            50, 3.10),   # +6.9%  → cost UP
    ("Nescafe Classic 200g",    30, 4.20),   # flat
    ("Lays Chips 45g",         100, 0.80),   # flat
    ("Redbull 250ml",           60, 0.95),   # flat
    ("iPhone Charger",          20, 4.00),   # flat
    ("Power Bank 10000mAh",     15, 14.00),  # flat
    ("Bluetooth Earbuds",       10, 17.00),  # flat
    ("USB-C Hub 4-Port",        20, 12.00),  # +9.1% → cost UP (shows with unknown velocity)
    ("Laptop Stand",            10, 18.00),  # first invoice — no prior cost → trend=None
]


# ─── Sales generation helpers ─────────────────────────────────────────────────

_ANOMALY_START = date.today() - timedelta(days=7)


def _daily_qty(cfg: dict, d: date) -> int:
    anomaly = cfg.get("anomaly")
    if anomaly and d >= _ANOMALY_START:
        if anomaly == "drop":
            return max(0, round(random.gauss(0.15, 0.15)))   # near-zero → z < -2
        if anomaly == "spike":
            # 7× normal across the recent window. Big enough that every recent
            # day's *total* volume sits above the baseline median, which (with
            # the 2-bin PSI on an 8-day window) pushes global drift into "alert"
            # (PSI > 0.20) even with other tenants' baseline sales in the mix.
            return max(0, round(cfg["base"] * 7 + random.gauss(0, cfg["noise"])))  # 7× → z > +2
    weekend = cfg.get("weekend", 0.0) if d.weekday() >= 5 else 0.0
    return max(0, round(cfg["base"] + weekend + random.gauss(0, cfg["noise"])))


def _upsert_supplier(db, business_id: int, name: str) -> Supplier:
    s = db.execute(
        select(Supplier).where(Supplier.business_id == business_id, Supplier.name == name)
    ).scalar_one_or_none()
    if s is None:
        s = Supplier(business_id=business_id, name=name)
        db.add(s)
        db.flush()
    return s


def _make_invoice(db, products_map, bid, supplier_id, inv_date, items_cfg, prev_prices=None):
    total = sum(qty * price for _, qty, price in items_cfg)
    inv = Invoice(
        business_id=bid, supplier_id=supplier_id,
        invoice_date=inv_date, invoice_total=round(total, 2),
        currency="USD", raw_ocr_text="[seeded]",
        extracted_json={"seeded": True}, status="processed",
    )
    db.add(inv)
    db.flush()
    for pname, qty, unit_price in items_cfg:
        pct = None
        if prev_prices and pname in prev_prices:
            old = prev_prices[pname]
            pct = round((unit_price - old) / old * 100, 1) if old else None
        prod = products_map.get(pname)
        db.add(InvoiceItem(
            invoice_id=inv.id,
            product_id=prod.id if prod else None,
            product_name=pname, quantity=qty,
            unit_price=unit_price, total=round(qty * unit_price, 2),
            price_change_pct=pct,
        ))
    db.flush()
    return inv


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    db = SessionLocal()
    try:
        today = date.today()

        # Target the souk_tripoli account.
        # NOTE: the login username is "souk_tripoli" but the business display
        # name is "minimarket", so we resolve via the owner user, then fall back
        # to a name search on "tripoli".
        from app.models.user import User
        owner = db.execute(
            select(User).where(func.lower(User.username) == "souk_tripoli")
        ).scalar_one_or_none()
        business = db.get(Business, owner.business_id) if owner and owner.business_id else None
        if business is None:
            business = db.execute(
                select(Business).where(func.lower(Business.name).contains("tripoli"))
            ).scalar_one_or_none()
        if business is None:
            raise RuntimeError("souk_tripoli business not found — check the username/business name.")

        bid = business.id
        print(f"Business: '{business.name}' (id={bid})")

        # ── 1. Hard-reset ALL existing products to canonical stock/prices ─────
        all_existing = db.execute(
            select(Product).where(Product.business_id == bid)
        ).scalars().all()
        for p in all_existing:
            cfg = PRODUCTS.get(p.name)
            if cfg:
                p.current_stock = cfg["stock"]
                p.reorder_level = cfg["reorder"]
                p.cost_price    = cfg["cost"]
                p.selling_price = cfg["sell"]
            elif (p.current_stock or 0) < 0:
                p.current_stock = 0   # floor any leftover unknown product
        db.flush()
        print(f"[1] Reset {len(all_existing)} existing products")

        # ── 2. Upsert canonical product list ──────────────────────────────────
        products: dict[str, Product] = {}
        for name, cfg in PRODUCTS.items():
            p = db.execute(
                select(Product).where(Product.business_id == bid, Product.name == name)
            ).scalar_one_or_none()
            if p is None:
                p = Product(
                    business_id=bid, name=name,
                    current_stock=cfg["stock"],
                    reorder_level=cfg["reorder"],
                    cost_price=cfg["cost"],
                    selling_price=cfg["sell"],
                )
                db.add(p)
                db.flush()
            products[name] = p
        print(f"[2] {len(products)} products upserted")

        # ── 3. Wipe inventory movements ───────────────────────────────────────
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
            if cfg.get("no_sales"):
                continue   # unknown mover — intentionally no sales history
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
            select(Invoice.id).where(
                Invoice.business_id == bid, Invoice.supplier_id == supplier.id
            )
        ).scalars().all()
        if old_inv_ids:
            db.query(InvoiceItem).filter(
                InvoiceItem.invoice_id.in_(old_inv_ids)
            ).delete(synchronize_session=False)
            db.query(Invoice).filter(
                Invoice.id.in_(old_inv_ids)
            ).delete(synchronize_session=False)
            db.flush()

        inv1 = _make_invoice(
            db, products, bid, supplier.id,
            today - timedelta(days=28), INV_BASELINE,
        )
        prev_prices = {pname: price for pname, _, price in INV_BASELINE}
        inv2 = _make_invoice(
            db, products, bid, supplier.id,
            today - timedelta(days=3), INV_RECENT,
            prev_prices=prev_prices,
        )
        print(f"[5] 2 invoices created (#{inv1.id} baseline, #{inv2.id} with price alerts)")

        # ── 6. Rebuild orders ─────────────────────────────────────────────────
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
                    {"product": it["product_name"], "quantity": it["quantity"], "color": None, "size": None}
                    for it in odata["items"]
                ],
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
            db.add(order)
            db.flush()
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
        critical_count = 0
        low_count = 0
        ok_count = 0
        print("\n── Inventory summary ──────────────────────────────────────────────")
        for name, p in products.items():
            stk = p.current_stock or 0
            rl  = p.reorder_level or 0
            if stk <= 0:
                tag = "CRITICAL"; critical_count += 1
            elif stk <= rl:
                tag = "LOW";      low_count += 1
            else:
                tag = "ok";       ok_count += 1
            cfg = PRODUCTS[name]
            velocity = "unknown" if cfg.get("no_sales") else (
                "fast" if cfg.get("base", 0) >= 5 else
                "medium" if cfg.get("base", 0) >= 1 else "slow"
            )
            anomaly_tag = f"  [{cfg['anomaly'].upper()}]" if cfg.get("anomaly") else ""
            print(f"  {name:<26} stock={stk:>4}  reorder={rl:>3}  [{tag:<8}]  {velocity}{anomaly_tag}")

        print(f"\nReorder alerts: {critical_count} CRITICAL + {low_count} LOW = {critical_count+low_count} total  ({ok_count} OK)")

    finally:
        db.close()


if __name__ == "__main__":
    main()
