"""add money flow status to purchase offer results

Revision ID: d3a9f2c7b8e1
Revises: 6f2d9b1a4c33
Create Date: 2026-03-04 00:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d3a9f2c7b8e1"
down_revision: Union[str, Sequence[str], None] = "6f2d9b1a4c33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "purchase_offer_results",
        sa.Column("money_flow_status", sa.String(length=50), nullable=True),
    )
    op.execute(
        "UPDATE purchase_offer_results "
        "SET money_flow_status = 'in_system' "
        "WHERE status = 'success' "
        "AND EXISTS ("
        "    SELECT 1 FROM user_payments up "
        "    WHERE up.purchase_id = purchase_offer_results.purchase_id "
        "      AND up.status = 'succeeded'"
        ")"
    )
    op.execute(
        "UPDATE purchase_offer_results "
        "SET money_flow_status = 'at_user' "
        "WHERE money_flow_status IS NULL"
    )
    op.alter_column(
        "purchase_offer_results",
        "money_flow_status",
        existing_type=sa.String(length=50),
        nullable=False,
        server_default="at_user",
    )
    op.create_check_constraint(
        "ck_purchase_offer_result_money_flow_status_valid",
        "purchase_offer_results",
        "money_flow_status IN ('at_user', 'in_system', 'at_seller')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_purchase_offer_result_money_flow_status_valid",
        "purchase_offer_results",
        type_="check",
    )
    op.drop_column("purchase_offer_results", "money_flow_status")
