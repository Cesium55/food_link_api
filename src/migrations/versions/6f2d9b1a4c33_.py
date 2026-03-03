"""add refunded quantity to purchase offer results

Revision ID: 6f2d9b1a4c33
Revises: c4b8f1d2e6aa
Create Date: 2026-03-03 02:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f2d9b1a4c33"
down_revision: Union[str, Sequence[str], None] = "c4b8f1d2e6aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TABLE purchase_offer_results "
        "ADD COLUMN IF NOT EXISTS refunded_quantity INTEGER"
    )
    op.execute(
        "UPDATE purchase_offer_results "
        "SET refunded_quantity = COALESCE(processed_quantity, requested_quantity) "
        "WHERE status = 'refunded' AND (refunded_quantity IS NULL OR refunded_quantity = 0)"
    )
    op.execute(
        "UPDATE purchase_offer_results "
        "SET refunded_quantity = 0 "
        "WHERE refunded_quantity IS NULL"
    )
    op.alter_column(
        "purchase_offer_results",
        "refunded_quantity",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="0",
    )

    op.execute(
        "ALTER TABLE purchase_offer_results "
        "DROP CONSTRAINT IF EXISTS ck_purchase_offer_result_refunded_quantity_non_negative"
    )
    op.create_check_constraint(
        "ck_purchase_offer_result_refunded_quantity_non_negative",
        "purchase_offer_results",
        "refunded_quantity >= 0",
    )

    op.execute(
        "ALTER TABLE purchase_offer_results "
        "DROP CONSTRAINT IF EXISTS ck_purchase_offer_result_refunded_quantity_not_exceed_total"
    )
    op.create_check_constraint(
        "ck_purchase_offer_result_refunded_quantity_not_exceed_total",
        "purchase_offer_results",
        "refunded_quantity <= COALESCE(processed_quantity, requested_quantity)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_purchase_offer_result_refunded_quantity_not_exceed_total",
        "purchase_offer_results",
        type_="check",
    )
    op.drop_constraint(
        "ck_purchase_offer_result_refunded_quantity_non_negative",
        "purchase_offer_results",
        type_="check",
    )
    op.drop_column("purchase_offer_results", "refunded_quantity")
