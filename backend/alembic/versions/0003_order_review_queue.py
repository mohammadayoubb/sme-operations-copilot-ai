"""Add confidence_score and review_status to orders

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("confidence_score", sa.Float(), server_default="1.0", nullable=True))
    op.add_column("orders", sa.Column("review_status", sa.String(50), server_default="auto_approved", nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "review_status")
    op.drop_column("orders", "confidence_score")
