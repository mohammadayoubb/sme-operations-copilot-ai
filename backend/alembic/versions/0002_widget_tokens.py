"""Add widget_tokens table

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "widget_tokens",
        sa.Column("token", sa.String(36), primary_key=True),
        sa.Column("business_id", sa.Integer, sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("label", sa.String(255), nullable=False, server_default="My Widget"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("widget_tokens")
