"""update purchase_offer_results status check with refunded

Revision ID: c4b8f1d2e6aa
Revises: 9ed8c0bbb470
Create Date: 2026-03-03 02:20:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c4b8f1d2e6aa"
down_revision: Union[str, Sequence[str], None] = "9ed8c0bbb470"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TABLE purchase_offer_results "
        "DROP CONSTRAINT IF EXISTS ck_purchase_offer_result_status_valid"
    )
    op.create_check_constraint(
        "ck_purchase_offer_result_status_valid",
        "purchase_offer_results",
        "status IN ('success', 'not_found', 'insufficient_quantity', 'expired', 'refunded')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TABLE purchase_offer_results "
        "DROP CONSTRAINT IF EXISTS ck_purchase_offer_result_status_valid"
    )
    op.create_check_constraint(
        "ck_purchase_offer_result_status_valid",
        "purchase_offer_results",
        "status IN ('success', 'not_found', 'insufficient_quantity', 'expired')",
    )
