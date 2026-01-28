"""
Migration: Increase decimal precision for cost columns

Products with per-gram pricing (e.g., $0.01575/g) need more than 2 decimal places.
This migration increases precision from NUMERIC(10,2) to NUMERIC(12,6).
"""


def upgrade():
    """
    Run this SQL in your database:

    ALTER TABLE products ALTER COLUMN standard_cost TYPE NUMERIC(12, 6);
    ALTER TABLE products ALTER COLUMN average_cost TYPE NUMERIC(12, 6);
    ALTER TABLE products ALTER COLUMN last_cost TYPE NUMERIC(12, 6);

    -- Also update related tables that store per-unit costs
    ALTER TABLE inventory_transactions ALTER COLUMN cost_per_unit TYPE NUMERIC(12, 6);
    ALTER TABLE material_lots ALTER COLUMN unit_cost TYPE NUMERIC(12, 6);
    ALTER TABLE purchase_order_lines ALTER COLUMN unit_cost TYPE NUMERIC(12, 6);
    """
    pass


def downgrade():
    """
    ALTER TABLE products ALTER COLUMN standard_cost TYPE NUMERIC(10, 2);
    ALTER TABLE products ALTER COLUMN average_cost TYPE NUMERIC(10, 2);
    ALTER TABLE products ALTER COLUMN last_cost TYPE NUMERIC(10, 2);

    ALTER TABLE inventory_transactions ALTER COLUMN cost_per_unit TYPE NUMERIC(10, 2);
    ALTER TABLE material_lots ALTER COLUMN unit_cost TYPE NUMERIC(10, 2);
    ALTER TABLE purchase_order_lines ALTER COLUMN unit_cost TYPE NUMERIC(10, 2);
    """
    pass
