"""Business logic for superadmin tenant management."""
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.business import Business
from app.models.document import Document
from app.models.insight import AIInsight
from app.models.invoice import Invoice
from app.models.order import Order
from app.models.product import Product
from app.models.sales import Sale
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


def get_tenant_stats(db: Session, business_id: int) -> Dict[str, Any]:
    if not db.query(Business).filter(Business.id == business_id).first():
        raise HTTPException(status_code=404, detail="Tenant not found")

    bid = business_id

    # Orders by status
    order_rows = (
        db.query(Order.status, func.count(Order.id))
        .filter(Order.business_id == bid)
        .group_by(Order.status)
        .all()
    )
    order_by_status = {row[0]: row[1] for row in order_rows}
    order_total = sum(order_by_status.values())
    last_order = db.query(func.max(Order.created_at)).filter(Order.business_id == bid).scalar()

    # Invoices by status
    inv_rows = (
        db.query(Invoice.status, func.count(Invoice.id))
        .filter(Invoice.business_id == bid)
        .group_by(Invoice.status)
        .all()
    )
    inv_by_status = {row[0]: row[1] for row in inv_rows}
    inv_total = sum(inv_by_status.values())
    last_invoice = db.query(func.max(Invoice.created_at)).filter(Invoice.business_id == bid).scalar()

    # Products + low stock
    product_total = db.query(func.count(Product.id)).filter(Product.business_id == bid).scalar() or 0
    low_stock = (
        db.query(func.count(Product.id))
        .filter(Product.business_id == bid, Product.current_stock <= Product.reorder_level)
        .scalar() or 0
    )

    # Revenue
    revenue_total = db.query(func.coalesce(func.sum(Sale.total), 0)).filter(Sale.business_id == bid).scalar() or 0

    # AI usage
    insights_count = db.query(func.count(AIInsight.id)).filter(AIInsight.business_id == bid).scalar() or 0
    docs_count = db.query(func.count(Document.id)).filter(Document.business_id == bid).scalar() or 0

    # Users
    user_rows = (
        db.query(User.role, func.count(User.id))
        .filter(User.business_id == bid)
        .group_by(User.role)
        .all()
    )
    user_by_role = {row[0]: row[1] for row in user_rows}
    user_total = sum(user_by_role.values())

    # Last activity across orders and invoices
    last_activity: Optional[Any] = None
    if last_order and last_invoice:
        last_activity = max(last_order, last_invoice)
    else:
        last_activity = last_order or last_invoice

    return {
        "orders": {
            "total": order_total,
            "by_status": order_by_status,
            "last_at": last_order,
        },
        "invoices": {
            "total": inv_total,
            "by_status": inv_by_status,
            "last_at": last_invoice,
        },
        "products": {
            "total": product_total,
            "low_stock": low_stock,
        },
        "revenue_total": float(revenue_total),
        "ai": {
            "insights_generated": insights_count,
            "documents_indexed": docs_count,
        },
        "users": {
            "total": user_total,
            "by_role": user_by_role,
        },
        "last_activity_at": last_activity,
    }


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
