"""add is_active to users

Revision ID: e2b3d7f9c1a4
Revises: b7f3f1c2d8e0
Create Date: 2026-02-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e2b3d7f9c1a4"
down_revision = "b7f3f1c2d8e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.alter_column("users", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "is_active")
