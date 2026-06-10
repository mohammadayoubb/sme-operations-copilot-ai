"""Business logic for superadmin tenant management."""
from typing import Any, Dict, List

from fastapi import HTTPException, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.business import Business
from app.models.order import Order
from app.models.product import Product
from app.models.user import User


def list_tenants(db: Session) -> List[Dict[str, Any]]:
    businesses = db.query(Business).order_by(Business.created_at.desc()).all()
    result = []
    for biz in businesses:
        owner = (
            db.query(User)
            .filter(User.business_id == biz.id, User.role == "owner")
            .first()
        )
        user_count = db.query(func.count(User.id)).filter(User.business_id == biz.id).scalar() or 0
        product_count = db.query(func.count(Product.id)).filter(Product.business_id == biz.id).scalar() or 0
        order_count = db.query(func.count(Order.id)).filter(Order.business_id == biz.id).scalar() or 0
        result.append({
            "id": biz.id,
            "name": biz.name,
            "created_at": biz.created_at,
            "owner_username": owner.username if owner else None,
            "user_count": user_count,
            "product_count": product_count,
            "order_count": order_count,
        })
    return result


def create_tenant(db: Session, business_name: str, username: str, password: str) -> Dict[str, Any]:
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    business = Business(name=business_name)
    db.add(business)
    db.flush()

    user = User(
        business_id=business.id,
        username=username,
        hashed_password=hash_password(password),
        role="owner",
    )
    db.add(user)
    db.commit()
    return {"id": business.id, "name": business.name, "owner_username": username}


def delete_tenant(db: Session, business_id: int) -> None:
    if not db.query(Business).filter(Business.id == business_id).first():
        raise HTTPException(status_code=404, detail="Tenant not found")

    bid = {"bid": business_id}
    # Delete leaf tables first (FK chain), then direct business_id tables, then the business
    db.execute(text("DELETE FROM inventory_movements WHERE product_id IN (SELECT id FROM products WHERE business_id = :bid)"), bid)
    db.execute(text("DELETE FROM invoice_items WHERE invoice_id IN (SELECT id FROM invoices WHERE business_id = :bid)"), bid)
    db.execute(text("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE business_id = :bid)"), bid)
    db.execute(text("DELETE FROM sales WHERE business_id = :bid"), bid)
    db.execute(text("DELETE FROM alerts WHERE business_id = :bid"), bid)
    db.execute(text("DELETE FROM ai_insights WHERE business_id = :bid"), bid)
    db.execute(text("DELETE FROM documents WHERE business_id = :bid"), bid)
    db.execute(text("DELETE FROM reports WHERE business_id = :bid"), bid)
    db.execute(text("DELETE FROM widget_tokens WHERE business_id = :bid"), bid)
    db.execute(text("DELETE FROM invoices WHERE business_id = :bid"), bid)
    db.execute(text("DELETE FROM orders WHERE business_id = :bid"), bid)
    db.execute(text("DELETE FROM products WHERE business_id = :bid"), bid)
    db.execute(text("DELETE FROM suppliers WHERE business_id = :bid"), bid)
    db.execute(text("DELETE FROM users WHERE business_id = :bid"), bid)
    db.execute(text("DELETE FROM businesses WHERE id = :bid"), bid)
    db.commit()
