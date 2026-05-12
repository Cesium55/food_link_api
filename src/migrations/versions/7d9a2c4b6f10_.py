"""add unique pending purchase per user

Revision ID: 7d9a2c4b6f10
Revises: 4a1f9e8d77c2
Create Date: 2026-05-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7d9a2c4b6f10"
down_revision: Union[str, Sequence[str], None] = "4a1f9e8d77c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "uq_user_pending_purchase",
        "purchases",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_user_pending_purchase",
        table_name="purchases",
        postgresql_where=sa.text("status = 'pending'"),
    )
