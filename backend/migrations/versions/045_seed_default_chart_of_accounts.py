"""Seed default chart of accounts

This data migration populates the gl_accounts table with a Schedule C-ready
chart of accounts for sole proprietors. All accounts map to IRS Schedule C
lines where applicable.

Revision ID: 045_seed_coa
Revises: 044_gl_tables
Create Date: 2026-01-16
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "045_seed_coa"
down_revision = "044_gl_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Insert default chart of accounts
    # Based on DEFAULT_ACCOUNTS from ACCOUNTING_MODULE.md
    op.execute("""
        INSERT INTO gl_accounts (account_code, name, account_type, schedule_c_line, is_system, active, description)
        VALUES
            -- Assets (1xxx)
            ('1000', 'Cash', 'asset', NULL, true, true, 'Cash on hand and in bank accounts'),
            ('1100', 'Accounts Receivable', 'asset', NULL, true, true, 'Amounts owed by customers'),
            ('1200', 'Inventory', 'asset', NULL, true, true, 'Raw materials and finished goods'),
            ('1300', 'Prepaid Expenses', 'asset', NULL, false, true, 'Expenses paid in advance'),
            ('1500', 'Equipment', 'asset', NULL, false, true, 'Machinery, printers, tools'),
            ('1510', 'Accumulated Depreciation', 'asset', NULL, false, true, 'Contra account for equipment depreciation'),

            -- Liabilities (2xxx)
            ('2000', 'Accounts Payable', 'liability', NULL, true, true, 'Amounts owed to vendors'),
            ('2100', 'Sales Tax Payable', 'liability', NULL, false, true, 'Collected sales tax owed to government'),
            ('2200', 'Credit Card Payable', 'liability', NULL, false, true, 'Credit card balances'),

            -- Equity (3xxx)
            ('3000', 'Owner''s Equity', 'equity', NULL, true, true, 'Owner''s investment in the business'),
            ('3100', 'Owner''s Draw', 'equity', NULL, false, true, 'Withdrawals by owner'),
            ('3200', 'Retained Earnings', 'equity', NULL, false, true, 'Accumulated profits'),

            -- Revenue (4xxx) - Schedule C Line 1-2
            ('4000', 'Sales Revenue', 'revenue', '1', true, true, 'Gross receipts from sales'),
            ('4100', 'Service Revenue', 'revenue', '1', false, true, 'Revenue from services'),
            ('4200', 'Shipping Revenue', 'revenue', '1', false, true, 'Shipping charges collected'),
            ('4900', 'Returns and Allowances', 'revenue', '2', false, true, 'Customer returns and discounts'),

            -- Cost of Goods Sold (5xxx) - Schedule C Lines 36-38
            ('5000', 'COGS - Materials', 'expense', '36', true, true, 'Cost of materials used in production'),
            ('5100', 'COGS - Direct Labor', 'expense', '37', false, true, 'Direct labor costs for production'),
            ('5200', 'COGS - Other', 'expense', '38', false, true, 'Other production costs'),

            -- Operating Expenses (6xxx-8xxx) - Schedule C Lines 8-27
            ('6000', 'Advertising', 'expense', '8', false, true, 'Advertising and marketing expenses'),
            ('6100', 'Car and Truck Expenses', 'expense', '9', false, true, 'Vehicle expenses for business use'),
            ('6200', 'Commissions and Fees', 'expense', '10', false, true, 'Sales commissions and platform fees'),
            ('6300', 'Contract Labor', 'expense', '11', false, true, 'Payments to independent contractors'),
            ('6400', 'Depreciation', 'expense', '13', false, true, 'Depreciation of business assets'),
            ('6500', 'Insurance', 'expense', '15', false, true, 'Business insurance premiums'),
            ('6600', 'Interest - Mortgage', 'expense', '16a', false, true, 'Interest on business property mortgage'),
            ('6610', 'Interest - Other', 'expense', '16b', false, true, 'Other business interest expenses'),
            ('6700', 'Legal and Professional', 'expense', '17', false, true, 'Legal, accounting, consulting fees'),
            ('6800', 'Office Expense', 'expense', '18', false, true, 'Office supplies and expenses'),
            ('6900', 'Pension/Profit Sharing', 'expense', '19', false, true, 'Retirement plan contributions'),
            ('7000', 'Rent - Vehicles/Equipment', 'expense', '20a', false, true, 'Rental of vehicles and equipment'),
            ('7010', 'Rent - Other Business Property', 'expense', '20b', false, true, 'Rental of business space'),
            ('7100', 'Repairs and Maintenance', 'expense', '21', false, true, 'Repair and maintenance costs'),
            ('7200', 'Supplies', 'expense', '22', false, true, 'Office and operating supplies'),
            ('7300', 'Taxes and Licenses', 'expense', '23', false, true, 'Business taxes and license fees'),
            ('7400', 'Travel', 'expense', '24a', false, true, 'Business travel expenses'),
            ('7410', 'Meals (50%)', 'expense', '24b', false, true, 'Business meals (50% deductible)'),
            ('7500', 'Utilities', 'expense', '25', false, true, 'Electric, gas, water, internet'),
            ('7600', 'Wages', 'expense', '26', false, true, 'Employee wages and salaries'),
            ('7900', 'Other Expenses', 'expense', '27a', false, true, 'Miscellaneous business expenses'),

            -- Bank/Payment Processing (8xxx)
            ('8000', 'Bank Fees', 'expense', '27a', false, true, 'Bank service charges and fees'),
            ('8100', 'Payment Processing Fees', 'expense', '10', false, true, 'Credit card and payment processor fees')
    """)


def downgrade() -> None:
    # Remove all seeded accounts
    op.execute("""
        DELETE FROM gl_accounts
        WHERE account_code IN (
            '1000', '1100', '1200', '1300', '1500', '1510',
            '2000', '2100', '2200',
            '3000', '3100', '3200',
            '4000', '4100', '4200', '4900',
            '5000', '5100', '5200',
            '6000', '6100', '6200', '6300', '6400', '6500', '6600', '6610',
            '6700', '6800', '6900', '7000', '7010', '7100', '7200', '7300',
            '7400', '7410', '7500', '7600', '7900',
            '8000', '8100'
        )
    """)
