"""Add email to users + password_reset_tokens table

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(255), nullable=True))

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_password_reset_tokens_token", "password_reset_tokens", ["token"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_token", "password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_column("users", "email")
