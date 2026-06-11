"""Add drift_signals table

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drift_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("psi_score", sa.Float(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("baseline_days", sa.Integer(), nullable=True),
        sa.Column("recent_days", sa.Integer(), nullable=True),
        sa.Column("feature_stats", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("drift_signals")
