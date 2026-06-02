"""Seed 60 days of realistic sales history for the forecasting models.

Run inside the backend container (it has DB access + the app package):

    docker compose exec -T backend python - < sample_data/seed_sales.py

It is idempotent: it upserts the four demo grocery products, wipes any existing
seeded sales, and regenerates a fresh 60-day history with weekly seasonality +
noise, then sets stock levels so a few products clearly need reordering.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.product import Product
from app.models.sales import Sale
from app.repositories.product_repo import get_or_create_default_business

random.seed(42)

DAYS = 60

# name -> (cost, sell, reorder_level, final_stock, base/day, weekend_bump, noise_sd)
PRODUCTS = {
    "Pepsi 330ml":     dict(cost=0.42, sell=0.75, reorder=20, stock=120, base=12.0, weekend=4.0, noise=2.0),
    "Lays Chips 45g":  dict(cost=0.80, sell=1.25, reorder=20, stock=30,  base=8.0,  weekend=3.0, noise=1.5),
    "Water 1.5L":      dict(cost=0.25, sell=0.50, reorder=15, stock=18,  base=10.0, weekend=2.0, noise=2.0),
    "Nutella 400g":    dict(cost=3.10, sell=5.50, reorder=10, stock=8,   base=3.2,  weekend=1.0, noise=0.8),
}


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
    weekend = cfg["weekend"] if day.weekday() >= 5 else 0.0   # Sat/Sun bump
    qty = cfg["base"] + weekend + random.gauss(0, cfg["noise"])
    return max(0, round(qty))


def main() -> None:
    db = SessionLocal()
    try:
        business = get_or_create_default_business(db)
        today = date.today()
        start = today - timedelta(days=DAYS - 1)

        products = {name: _upsert_product(db, business.id, name, cfg) for name, cfg in PRODUCTS.items()}
        db.flush()

        # Wipe previously seeded sales so re-running stays clean.
        seeded_ids = [p.id for p in products.values()]
        db.query(Sale).filter(Sale.product_id.in_(seeded_ids), Sale.source == "seed").delete(
            synchronize_session=False
        )

        total_rows = 0
        for name, cfg in PRODUCTS.items():
            product = products[name]
            for i in range(DAYS):
                d = start + timedelta(days=i)
                qty = _daily_qty(cfg, d)
                if qty == 0:
                    continue
                price = cfg["sell"]
                db.add(Sale(
                    business_id=business.id,
                    product_id=product.id,
                    quantity=qty,
                    unit_price=price,
                    total=round(qty * price, 2),
                    sale_date=d,
                    source="seed",
                ))
                total_rows += 1

        db.commit()
        print(f"Seeded {total_rows} sales rows across {len(PRODUCTS)} products over {DAYS} days.")
        for name, p in products.items():
            print(f"  - {name}: stock={p.current_stock}, reorder_level={p.reorder_level}, sell=${p.selling_price}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
