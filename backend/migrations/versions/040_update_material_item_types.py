"""Update material item_types - Migrate supply filaments to material type

This migration updates existing filament products (supply with material_type_id)
to use the new 'material' item_type for proper UOM auto-configuration.

Conservative approach: Only updates products that clearly should be materials.

Revision ID: 040_update_material_item_types
Revises: 039_uom_cost_normalization
Create Date: 2026-01-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "040_update_material_item_types"
down_revision: Union[str, None] = "039_uom_cost_normalization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Update item_type to 'material' for products that are clearly materials.

    Criteria for update (conservative):
    1. Has material_type_id (legacy filament indicator)
    2. Currently item_type = 'supply'

    Also ensures proper UOM configuration for materials.
    """
    connection = op.get_bind()

    # =========================================================================
    # STEP 1: Update item_type for legacy filaments
    # =========================================================================
    # Products with material_type_id that are currently 'supply' become 'material'
    result = connection.execute(
        sa.text("""
        UPDATE products
        SET item_type = 'material'
        WHERE material_type_id IS NOT NULL
        AND item_type = 'supply'
        RETURNING id, sku
    """)
    )
    updated_rows = result.fetchall()
    updated_count = len(updated_rows)

    # =========================================================================
    # STEP 2: Ensure materials have proper UOM configuration
    # =========================================================================
    # For materials with G/KG but missing or wrong purchase_factor, fix it
    connection.execute(
        sa.text("""
        UPDATE products
        SET purchase_factor = 1000
        WHERE (item_type = 'material' OR material_type_id IS NOT NULL)
        AND unit = 'G'
        AND purchase_uom = 'KG'
        AND (purchase_factor IS NULL OR purchase_factor != 1000)
    """)
    )

    # Ensure is_raw_material = True for materials
    connection.execute(
        sa.text("""
        UPDATE products
        SET is_raw_material = TRUE
        WHERE (item_type = 'material' OR material_type_id IS NOT NULL)
        AND (is_raw_material IS NULL OR is_raw_material = FALSE)
    """)
    )

    print("=" * 70)
    print("MIGRATION 040 COMPLETE: Material Item Types Update")
    print("=" * 70)
    print(f"Updated {updated_count} products from 'supply' to 'material' item_type")
    if updated_count > 0:
        for row in updated_rows[:10]:  # Show first 10
            print(f"  - {row[1]} (id: {row[0]})")
        if updated_count > 10:
            print(f"  ... and {updated_count - 10} more")
    print("")
    print("Also ensured proper UOM config for all materials:")
    print("  - unit=G, purchase_uom=KG, purchase_factor=1000")
    print("  - is_raw_material=True")
    print("=" * 70)


def downgrade() -> None:
    """
    Revert material item_types back to supply.
    Note: This doesn't restore original state perfectly -
    manually verify if needed.
    """
    connection = op.get_bind()

    # Only revert products that have material_type_id (were legacy filaments)
    connection.execute(
        sa.text("""
        UPDATE products
        SET item_type = 'supply'
        WHERE material_type_id IS NOT NULL
        AND item_type = 'material'
    """)
    )
