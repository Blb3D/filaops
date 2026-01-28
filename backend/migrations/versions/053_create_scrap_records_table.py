"""Create scrap_records table

Tracks scrapped materials and parts with cost and audit trail.
Links to inventory transactions and journal entries for full auditability.

Revision ID: 053_scrap_records
Revises: 052_inv_accounts_je_link
Create Date: 2026-01-20
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "053_scrap_records"
down_revision = "052_inv_accounts_je_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scrap_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        # Source tracking
        sa.Column("production_order_id", sa.Integer(), nullable=True, index=True),
        sa.Column("production_operation_id", sa.Integer(), nullable=True, index=True),
        sa.Column("operation_sequence", sa.Integer(), nullable=True),
        # What was scrapped
        sa.Column("product_id", sa.Integer(), nullable=False, index=True),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        # Cost capture (at time of scrap)
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_cost", sa.Numeric(18, 4), nullable=False),
        # Reason
        sa.Column("scrap_reason_id", sa.Integer(), nullable=True),
        sa.Column("scrap_reason_code", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        # Transaction links (for audit trail)
        sa.Column("inventory_transaction_id", sa.Integer(), nullable=True),
        sa.Column("journal_entry_id", sa.Integer(), nullable=True),
        # Audit
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        # Foreign key constraints
        sa.ForeignKeyConstraint(
            ["production_order_id"], ["production_orders.id"], name="fk_scrap_records_production_order"
        ),
        sa.ForeignKeyConstraint(
            ["production_operation_id"],
            ["production_order_operations.id"],
            name="fk_scrap_records_production_operation",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_scrap_records_product"),
        sa.ForeignKeyConstraint(["scrap_reason_id"], ["scrap_reasons.id"], name="fk_scrap_records_scrap_reason"),
        sa.ForeignKeyConstraint(
            ["inventory_transaction_id"], ["inventory_transactions.id"], name="fk_scrap_records_inventory_transaction"
        ),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["gl_journal_entries.id"], name="fk_scrap_records_journal_entry"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_scrap_records_created_by"),
    )

    # Index for scrap reporting queries (date range, product analysis)
    op.create_index("ix_scrap_records_created_at", "scrap_records", ["created_at"])
    op.create_index("ix_scrap_records_scrap_reason_id", "scrap_records", ["scrap_reason_id"])


def downgrade() -> None:
    op.drop_index("ix_scrap_records_scrap_reason_id", table_name="scrap_records")
    op.drop_index("ix_scrap_records_created_at", table_name="scrap_records")
    op.drop_table("scrap_records")
