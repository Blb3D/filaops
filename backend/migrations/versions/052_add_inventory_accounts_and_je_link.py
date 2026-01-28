"""Add inventory sub-accounts and journal_entry_id link

This migration:
1. Adds specific inventory sub-accounts required by TransactionService
2. Adds journal_entry_id foreign key to inventory_transactions for audit trail

Revision ID: 052_inv_accounts_je_link
Revises: 9056086f1897
Create Date: 2026-01-20
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "052_inv_accounts_je_link"
down_revision = "9056086f1897"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # 1. Add missing inventory sub-accounts to gl_accounts
    # These accounts support the TransactionService double-entry bookkeeping
    # =========================================================================
    op.execute("""
        INSERT INTO gl_accounts (account_code, name, account_type, schedule_c_line, is_system, active, description)
        VALUES
            -- Inventory sub-accounts (children of 1200 Inventory)
            ('1210', 'WIP Inventory', 'asset', NULL, true, true, 'Work-in-progress: Parts currently in production'),
            ('1220', 'Finished Goods Inventory', 'asset', NULL, true, true, 'Completed parts on shelf, ready to ship'),
            ('1230', 'Packaging Inventory', 'asset', NULL, true, true, 'Boxes, labels, tape for shipping'),

            -- Expense accounts for inventory movements
            ('5010', 'Shipping Supplies Expense', 'expense', '22', false, true, 'Packaging consumed when shipping'),
            ('5020', 'Scrap Expense', 'expense', '27a', false, true, 'Failed parts written off as scrap'),
            ('5030', 'Inventory Adjustment', 'expense', '27a', false, true, 'Cycle count variances and adjustments')
        ON CONFLICT (account_code) DO NOTHING
    """)

    # Update 1200 to be "Raw Materials Inventory" for clarity
    op.execute("""
        UPDATE gl_accounts
        SET name = 'Raw Materials Inventory',
            description = 'Filament, hardware, and other raw materials on hand'
        WHERE account_code = '1200' AND name = 'Inventory'
    """)

    # =========================================================================
    # 2. Add journal_entry_id to inventory_transactions
    # Links each inventory movement to its accounting entry for full audit trail
    # =========================================================================
    op.add_column("inventory_transactions", sa.Column("journal_entry_id", sa.Integer(), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_inventory_transactions_journal_entry",
        "inventory_transactions",
        "gl_journal_entries",
        ["journal_entry_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add index for efficient lookups
    op.create_index("ix_inventory_transactions_journal_entry_id", "inventory_transactions", ["journal_entry_id"])


def downgrade() -> None:
    # Remove journal_entry_id from inventory_transactions
    op.drop_index("ix_inventory_transactions_journal_entry_id", table_name="inventory_transactions")
    op.drop_constraint("fk_inventory_transactions_journal_entry", "inventory_transactions", type_="foreignkey")
    op.drop_column("inventory_transactions", "journal_entry_id")

    # Remove added accounts (leave 1200 name change - minor cosmetic)
    op.execute("""
        DELETE FROM gl_accounts
        WHERE account_code IN ('1210', '1220', '1230', '5010', '5020', '5030')
    """)
