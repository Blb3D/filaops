"""Add accounting-related fields for tax tracking and reporting

Revision ID: 009_accounting_enhancements
Revises: 007_ensure_code_unique
Create Date: 2025-12-15

Adds:
- sales_orders.tax_rate: The tax rate applied to the order (stored as decimal, e.g., 0.0825)
- sales_orders.is_taxable: Whether tax applies to this order
- company_settings.fiscal_year_start_month: For accounting period alignment (1-12)
- company_settings.accounting_method: cash vs accrual basis
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "009_accounting_enhancements"
down_revision: Union[str, Sequence[str], None] = "007_ensure_code_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect

    connection = op.get_bind()
    inspector = inspect(connection)

    # ========================================
    # Sales Orders: Add tax tracking fields
    # ========================================
    existing_tables = inspector.get_table_names()

    if "sales_orders" in existing_tables:
        existing_columns = [col["name"] for col in inspector.get_columns("sales_orders")]

        # Add tax_rate to store the rate at time of order (for audit trail)
        if "tax_rate" not in existing_columns:
            op.add_column("sales_orders", sa.Column("tax_rate", sa.Numeric(5, 4), nullable=True))

        # Add is_taxable flag
        if "is_taxable" not in existing_columns:
            op.add_column(
                "sales_orders",
                sa.Column(
                    "is_taxable",
                    sa.Boolean(),
                    nullable=True,
                    server_default=sa.text("1"),  # Default to taxable (SQL Server uses 1/0)
                ),
            )
            # Update existing orders: if tax_amount > 0, they were taxable
            connection.execute(
                sa.text("""
                UPDATE sales_orders
                SET is_taxable = CASE WHEN tax_amount > 0 THEN 1 ELSE 0 END
                WHERE is_taxable IS NULL
            """)
            )

    # ========================================
    # Company Settings: Add accounting fields
    # ========================================
    if "company_settings" in existing_tables:
        existing_columns = [col["name"] for col in inspector.get_columns("company_settings")]

        # Fiscal year start month (1=January, 12=December)
        if "fiscal_year_start_month" not in existing_columns:
            op.add_column(
                "company_settings",
                sa.Column(
                    "fiscal_year_start_month",
                    sa.Integer(),
                    nullable=True,
                    server_default=sa.text("1"),  # Default to January
                ),
            )

        # Accounting method: cash or accrual
        # Default to 'accrual' per GAAP (revenue at shipment, not payment)
        if "accounting_method" not in existing_columns:
            op.add_column(
                "company_settings",
                sa.Column("accounting_method", sa.String(20), nullable=True, server_default=sa.text("'accrual'")),
            )

        # Currency code (for export formatting and financial statements)
        if "currency_code" not in existing_columns:
            op.add_column(
                "company_settings",
                sa.Column("currency_code", sa.String(10), nullable=True, server_default=sa.text("'USD'")),
            )


def downgrade() -> None:
    from sqlalchemy import inspect

    connection = op.get_bind()
    inspector = inspect(connection)
    existing_tables = inspector.get_table_names()

    # Drop sales_orders columns
    if "sales_orders" in existing_tables:
        existing_columns = [col["name"] for col in inspector.get_columns("sales_orders")]
        if "is_taxable" in existing_columns:
            op.drop_column("sales_orders", "is_taxable")
        if "tax_rate" in existing_columns:
            op.drop_column("sales_orders", "tax_rate")

    # Drop company_settings columns
    if "company_settings" in existing_tables:
        existing_columns = [col["name"] for col in inspector.get_columns("company_settings")]
        if "currency_code" in existing_columns:
            op.drop_column("company_settings", "currency_code")
        if "accounting_method" in existing_columns:
            op.drop_column("company_settings", "accounting_method")
        if "fiscal_year_start_month" in existing_columns:
            op.drop_column("company_settings", "fiscal_year_start_month")
