"""Add superadmin role — make users.business_id nullable and seed superadmin account

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the NOT NULL constraint on users.business_id so superadmin can have NULL
    op.alter_column("users", "business_id", existing_type=sa.Integer(), nullable=True)

    # Seed the superadmin account (idempotent — skip if already exists)
    from passlib.context import CryptContext
    _ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = _ctx.hash("superadmin2024")

    op.execute(
        sa.text(
            "INSERT INTO users (business_id, username, hashed_password, role) "
            "VALUES (NULL, 'superadmin', :pw, 'superadmin') "
            "ON CONFLICT (username) DO NOTHING"
        ).bindparams(pw=hashed)
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM users WHERE username = 'superadmin'"))
    op.alter_column("users", "business_id", existing_type=sa.Integer(), nullable=False)
