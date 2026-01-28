"""Add transaction_date column to inventory_transactions

Revision ID: 029_add_transaction_date
Revises: 028_add_company_timezone
Create Date: 2025-12-24

This column stores the user-entered date when a transaction actually occurred
(e.g., when goods were physically received), distinct from created_at which
is the system timestamp when the record was entered.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "029_add_transaction_date"
down_revision = "028_add_company_timezone"
branch_labels = None
depends_on = None


def upgrade():
    """Add transaction_date column and backfill from created_at."""
    # Add the column
    op.add_column("inventory_transactions", sa.Column("transaction_date", sa.Date(), nullable=True))

    # Add index for efficient date-based queries
    op.create_index("ix_inventory_transactions_transaction_date", "inventory_transactions", ["transaction_date"])

    # Backfill existing records from created_at
    op.execute("""
        UPDATE inventory_transactions
        SET transaction_date = DATE(created_at)
        WHERE transaction_date IS NULL
    """)


def downgrade():
    """Remove transaction_date column."""
    op.drop_index("ix_inventory_transactions_transaction_date", "inventory_transactions")
    op.drop_column("inventory_transactions", "transaction_date")
