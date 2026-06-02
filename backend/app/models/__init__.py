"""Import all ORM models so SQLAlchemy registers them on Base.metadata."""
from app.models.business import Business, Supplier
from app.models.product import Product, InventoryMovement
from app.models.invoice import Invoice, InvoiceItem
from app.models.insight import Alert, AIInsight

__all__ = [
    "Business",
    "Supplier",
    "Product",
    "InventoryMovement",
    "Invoice",
    "InvoiceItem",
    "Alert",
    "AIInsight",
]
