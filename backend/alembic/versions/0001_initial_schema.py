"""Initial schema — all core tables

Revision ID: 0001
Revises:
Create Date: 2026-06-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "businesses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("business_id", sa.Integer, sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contact", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("business_id", sa.Integer, sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sku", sa.String(100)),
        sa.Column("current_stock", sa.Float, server_default="0"),
        sa.Column("reorder_level", sa.Float, server_default="10"),
        sa.Column("unit", sa.String(50)),
        sa.Column("cost_price", sa.Numeric(10, 2)),
        sa.Column("selling_price", sa.Numeric(10, 2)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("business_id", sa.Integer, sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("supplier_id", sa.Integer, sa.ForeignKey("suppliers.id")),
        sa.Column("invoice_date", sa.Date),
        sa.Column("invoice_total", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(10), server_default="USD"),
        sa.Column("raw_ocr_text", sa.Text),
        sa.Column("extracted_json", JSONB),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("file_path", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("invoice_id", sa.Integer, sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id")),
        sa.Column("product_name", sa.String(255)),
        sa.Column("quantity", sa.Float),
        sa.Column("unit_price", sa.Numeric(10, 4)),
        sa.Column("total", sa.Numeric(12, 2)),
        sa.Column("price_change_pct", sa.Float),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("business_id", sa.Integer, sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("source", sa.String(50)),
        sa.Column("raw_message", sa.Text),
        sa.Column("extracted_json", JSONB),
        sa.Column("delivery_area", sa.String(255)),
        sa.Column("payment_method", sa.String(100)),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id")),
        sa.Column("product_name", sa.String(255)),
        sa.Column("quantity", sa.Float),
        sa.Column("color", sa.String(100)),
        sa.Column("size", sa.String(50)),
        sa.Column("notes", sa.Text),
    )

    op.create_table(
        "sales",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("business_id", sa.Integer, sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id")),
        sa.Column("quantity", sa.Float),
        sa.Column("unit_price", sa.Numeric(10, 4)),
        sa.Column("total", sa.Numeric(12, 2)),
        sa.Column("sale_date", sa.Date, server_default=sa.func.current_date()),
        sa.Column("source", sa.String(50)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id"), nullable=False),
        sa.Column("delta", sa.Float, nullable=False),
        sa.Column("reason", sa.String(100)),
        sa.Column("reference_id", sa.Integer),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("business_id", sa.Integer, sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("type", sa.String(100)),
        sa.Column("message", sa.Text),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id")),
        sa.Column("is_read", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "ai_insights",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("business_id", sa.Integer, sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("type", sa.String(100)),
        sa.Column("reference_id", sa.Integer),
        sa.Column("insight_text", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("business_id", sa.Integer, sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("period_start", sa.Date),
        sa.Column("period_end", sa.Date),
        sa.Column("report_type", sa.String(50), server_default="weekly"),
        sa.Column("summary_text", sa.Text),
        sa.Column("data_json", JSONB),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("business_id", sa.Integer, sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("source_type", sa.String(100)),
        sa.Column("source_id", sa.Integer),
        sa.Column("content", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    # Indexes for common query patterns
    op.create_index("ix_sales_product_date", "sales", ["product_id", "sale_date"])
    op.create_index("ix_invoices_business", "invoices", ["business_id"])
    op.create_index("ix_orders_business_status", "orders", ["business_id", "status"])
    op.create_index("ix_alerts_business_unread", "alerts", ["business_id", "is_read"])


def downgrade() -> None:
    op.drop_table("documents")
    op.drop_table("reports")
    op.drop_table("ai_insights")
    op.drop_table("alerts")
    op.drop_table("inventory_movements")
    op.drop_table("sales")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("invoice_items")
    op.drop_table("invoices")
    op.drop_table("products")
    op.drop_table("suppliers")
    op.drop_table("businesses")
