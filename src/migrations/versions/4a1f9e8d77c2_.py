"""add product search vector

Revision ID: 4a1f9e8d77c2
Revises: e7b4a91c2d5f
Create Date: 2026-03-12 05:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "4a1f9e8d77c2"
down_revision: Union[str, Sequence[str], None] = "e7b4a91c2d5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "products",
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
    )
    op.create_index(
        "ix_products_search_vector",
        "products",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_products_search_vector", table_name="products")
    op.drop_column("products", "search_vector")
