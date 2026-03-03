"""add fulfilled_at to purchase offers

Revision ID: e7b4a91c2d5f
Revises: d3a9f2c7b8e1
Create Date: 2026-03-04 01:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e7b4a91c2d5f"
down_revision: Union[str, Sequence[str], None] = "d3a9f2c7b8e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "purchase_offers",
        sa.Column("fulfilled_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("purchase_offers", "fulfilled_at")
