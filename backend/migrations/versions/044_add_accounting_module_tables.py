"""Add accounting module tables (GL)

This migration creates the double-entry bookkeeping tables for FilaOps:
- gl_accounts: Chart of Accounts
- gl_fiscal_periods: Period tracking for month/year
- gl_journal_entries: Journal entry headers with audit trail
- gl_journal_entry_lines: Debit/credit lines for each entry

Revision ID: 044_gl_tables
Revises: 042_add_catalog_system
Create Date: 2026-01-16
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "044_gl_tables"
down_revision = "042_add_catalog_system"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # 1. Create gl_accounts table (Chart of Accounts)
    # =========================================================================
    op.create_table(
        "gl_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("account_type", sa.String(20), nullable=False),  # asset, liability, equity, revenue, expense
        sa.Column("schedule_c_line", sa.String(10), nullable=True),  # "1", "8", "22", etc.
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["parent_id"], ["gl_accounts.id"], name="fk_gl_accounts_parent"),
        sa.UniqueConstraint("account_code", name="uq_gl_accounts_code"),
    )
    op.create_index("ix_gl_accounts_account_type", "gl_accounts", ["account_type"])
    op.create_index("ix_gl_accounts_schedule_c_line", "gl_accounts", ["schedule_c_line"])
    op.create_index("ix_gl_accounts_active", "gl_accounts", ["active"])

    # =========================================================================
    # 2. Create gl_fiscal_periods table
    # =========================================================================
    op.create_table(
        "gl_fiscal_periods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("period", sa.Integer(), nullable=False),  # 1-12 for months
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),  # open, closed
        sa.Column("closed_by", sa.Integer(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"], name="fk_gl_fiscal_periods_closed_by"),
        sa.UniqueConstraint("year", "period", name="uq_gl_fiscal_periods_year_period"),
        sa.CheckConstraint("period >= 1 AND period <= 12", name="chk_gl_fiscal_periods_period_range"),
    )
    op.create_index("ix_gl_fiscal_periods_year", "gl_fiscal_periods", ["year"])
    op.create_index("ix_gl_fiscal_periods_status", "gl_fiscal_periods", ["status"])

    # =========================================================================
    # 3. Create gl_journal_entries table
    # =========================================================================
    op.create_table(
        "gl_journal_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_number", sa.String(20), nullable=False),  # "JE-2026-0001"
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        # Source tracking (for auto-posted entries)
        sa.Column("source_type", sa.String(50), nullable=True),  # sales_order, purchase_order, payment, manual
        sa.Column("source_id", sa.Integer(), nullable=True),
        # Status workflow
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),  # draft, posted, voided
        # Period
        sa.Column("fiscal_period_id", sa.Integer(), nullable=True),
        # Audit trail
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("posted_by", sa.Integer(), nullable=True),
        sa.Column("posted_at", sa.DateTime(), nullable=True),
        sa.Column("voided_by", sa.Integer(), nullable=True),
        sa.Column("voided_at", sa.DateTime(), nullable=True),
        sa.Column("void_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["fiscal_period_id"], ["gl_fiscal_periods.id"], name="fk_gl_journal_entries_period"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_gl_journal_entries_created_by"),
        sa.ForeignKeyConstraint(["posted_by"], ["users.id"], name="fk_gl_journal_entries_posted_by"),
        sa.ForeignKeyConstraint(["voided_by"], ["users.id"], name="fk_gl_journal_entries_voided_by"),
        sa.UniqueConstraint("entry_number", name="uq_gl_journal_entries_entry_number"),
    )
    op.create_index("ix_gl_journal_entries_entry_date", "gl_journal_entries", ["entry_date"])
    op.create_index("ix_gl_journal_entries_source", "gl_journal_entries", ["source_type", "source_id"])
    op.create_index("ix_gl_journal_entries_status", "gl_journal_entries", ["status"])

    # =========================================================================
    # 4. Create gl_journal_entry_lines table
    # =========================================================================
    op.create_table(
        "gl_journal_entry_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("journal_entry_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        # Amounts as Numeric(10, 2) - matching existing codebase pattern
        sa.Column("debit_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("credit_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("memo", sa.String(255), nullable=True),
        sa.Column("line_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"], ["gl_journal_entries.id"], name="fk_gl_journal_entry_lines_entry", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["account_id"], ["gl_accounts.id"], name="fk_gl_journal_entry_lines_account"),
        # Either debit OR credit must be zero, not both
        sa.CheckConstraint(
            "(debit_amount = 0 AND credit_amount > 0) OR (debit_amount > 0 AND credit_amount = 0)",
            name="chk_gl_journal_entry_lines_debit_or_credit",
        ),
    )
    op.create_index("ix_gl_journal_entry_lines_entry_id", "gl_journal_entry_lines", ["journal_entry_id"])
    op.create_index("ix_gl_journal_entry_lines_account_id", "gl_journal_entry_lines", ["account_id"])


def downgrade() -> None:
    # Drop gl_journal_entry_lines
    op.drop_index("ix_gl_journal_entry_lines_account_id", table_name="gl_journal_entry_lines")
    op.drop_index("ix_gl_journal_entry_lines_entry_id", table_name="gl_journal_entry_lines")
    op.drop_table("gl_journal_entry_lines")

    # Drop gl_journal_entries
    op.drop_index("ix_gl_journal_entries_status", table_name="gl_journal_entries")
    op.drop_index("ix_gl_journal_entries_source", table_name="gl_journal_entries")
    op.drop_index("ix_gl_journal_entries_entry_date", table_name="gl_journal_entries")
    op.drop_table("gl_journal_entries")

    # Drop gl_fiscal_periods
    op.drop_index("ix_gl_fiscal_periods_status", table_name="gl_fiscal_periods")
    op.drop_index("ix_gl_fiscal_periods_year", table_name="gl_fiscal_periods")
    op.drop_table("gl_fiscal_periods")

    # Drop gl_accounts
    op.drop_index("ix_gl_accounts_active", table_name="gl_accounts")
    op.drop_index("ix_gl_accounts_schedule_c_line", table_name="gl_accounts")
    op.drop_index("ix_gl_accounts_account_type", table_name="gl_accounts")
    op.drop_table("gl_accounts")
