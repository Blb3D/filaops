"""Add units_of_measure table with seed data

Revision ID: 005_units_of_measure
Revises: 004_production_order_split
Create Date: 2025-12-13

Adds:
- units_of_measure table for standardized unit conversions
- Seed data for common units (EA, KG, G, LB, OZ, M, CM, MM, FT, IN, HR, MIN)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005_units_of_measure"
down_revision: Union[str, Sequence[str], None] = "004_production_order_split"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect

    # Get connection and inspector
    connection = op.get_bind()
    inspector = inspect(connection)

    # Check if units_of_measure table exists
    existing_tables = inspector.get_table_names()
    if "units_of_measure" not in existing_tables:
        op.create_table(
            "units_of_measure",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(length=10), nullable=False),
            sa.Column("name", sa.String(length=50), nullable=False),
            sa.Column("symbol", sa.String(length=10), nullable=True),
            sa.Column("uom_class", sa.String(length=20), nullable=False),
            sa.Column("base_unit_id", sa.Integer(), nullable=True),
            sa.Column("to_base_factor", sa.Numeric(precision=18, scale=8), nullable=False, server_default="1"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["base_unit_id"], ["units_of_measure.id"], name="fk_uom_base_unit"),
        )
        op.create_index("ix_units_of_measure_code", "units_of_measure", ["code"], unique=True)

    # Seed UOM data if table is empty
    count = connection.execute(sa.text("SELECT COUNT(*) FROM units_of_measure")).scalar()
    if count == 0:
        # Seed base units first (no base_unit_id)
        base_units = [
            # (code, name, symbol, uom_class, to_base_factor)
            ("EA", "Each", "ea", "quantity", 1),
            ("KG", "Kilogram", "kg", "weight", 1),
            ("M", "Meter", "m", "length", 1),
            ("HR", "Hour", "hr", "time", 1),
        ]

        for code, name, symbol, uom_class, factor in base_units:
            connection.execute(
                sa.text("""
                    INSERT INTO units_of_measure (code, name, symbol, uom_class, base_unit_id, to_base_factor, active)
                    VALUES (:code, :name, :symbol, :uom_class, NULL, :factor, 1)
                """),
                {"code": code, "name": name, "symbol": symbol, "uom_class": uom_class, "factor": factor},
            )

        # Get base unit IDs for non-base units
        kg_id = connection.execute(sa.text("SELECT id FROM units_of_measure WHERE code = 'KG'")).scalar()
        m_id = connection.execute(sa.text("SELECT id FROM units_of_measure WHERE code = 'M'")).scalar()
        hr_id = connection.execute(sa.text("SELECT id FROM units_of_measure WHERE code = 'HR'")).scalar()

        # Seed derived units
        derived_units = [
            # Weight (base: KG)
            ("G", "Gram", "g", "weight", kg_id, 0.001),
            ("LB", "Pound", "lb", "weight", kg_id, 0.453592),
            ("OZ", "Ounce", "oz", "weight", kg_id, 0.0283495),
            # Length (base: M)
            ("CM", "Centimeter", "cm", "length", m_id, 0.01),
            ("MM", "Millimeter", "mm", "length", m_id, 0.001),
            ("FT", "Foot", "ft", "length", m_id, 0.3048),
            ("IN", "Inch", "in", "length", m_id, 0.0254),
            # Time (base: HR)
            ("MIN", "Minute", "min", "time", hr_id, 0.01666667),
        ]

        for code, name, symbol, uom_class, base_id, factor in derived_units:
            connection.execute(
                sa.text("""
                    INSERT INTO units_of_measure (code, name, symbol, uom_class, base_unit_id, to_base_factor, active)
                    VALUES (:code, :name, :symbol, :uom_class, :base_id, :factor, 1)
                """),
                {
                    "code": code,
                    "name": name,
                    "symbol": symbol,
                    "uom_class": uom_class,
                    "base_id": base_id,
                    "factor": factor,
                },
            )


def downgrade() -> None:
    """
    Downgrade with safety check to prevent loss of user-added UOMs.

    This will only drop the table if it contains ONLY the original seed data.
    If any custom UOMs have been added, the downgrade will abort with an error.
    """
    connection = op.get_bind()

    # Define the original seed UOM codes
    seed_codes = {"EA", "KG", "M", "HR", "G", "LB", "OZ", "CM", "MM", "FT", "IN", "MIN"}

    # Check for any UOMs that are not part of the seed data
    result = connection.execute(sa.text("SELECT code FROM units_of_measure"))
    existing_codes = {row[0] for row in result}

    # Find any custom (non-seed) UOMs
    custom_codes = existing_codes - seed_codes

    if custom_codes:
        raise RuntimeError(
            f"Cannot downgrade: units_of_measure table contains user-added UOMs that are not part "
            f"of the original seed data: {sorted(custom_codes)}. "
            f"To proceed, you must manually delete or migrate these custom UOMs first. "
            f"This safety check prevents accidental data loss in production."
        )

    # Safe to drop - only seed data present
    op.drop_index("ix_units_of_measure_code", table_name="units_of_measure")
    op.drop_table("units_of_measure")
