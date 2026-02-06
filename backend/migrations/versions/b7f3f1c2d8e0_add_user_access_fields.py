"""add_user_access_fields

Revision ID: b7f3f1c2d8e0
Revises: 9343028b8902
Create Date: 2026-02-05 12:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7f3f1c2d8e0"
down_revision: Union[str, Sequence[str], None] = "9343028b8902"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
    )
    op.add_column(
        "users",
        sa.Column(
            "password_reset_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "must_reset_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "must_reset_password")
    op.drop_column("users", "password_reset_at")
    op.drop_column("users", "role")
