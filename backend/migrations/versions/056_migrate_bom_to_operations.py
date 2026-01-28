"""
Migrate BOM lines to routing operation materials.

This migration consolidates the legacy bom_lines table data into the
routing_operation_materials table, which is the new unified approach.

Migration Strategy:
- consume_stage='production' -> First production operation (or sequence 1)
- consume_stage='shipping' -> Shipping/pack operation (if found), else last operation

After this migration, the bom_lines table data is preserved (not deleted)
but should no longer be used. The UI will be updated to hide the BOM tab.

Revision ID: 056_migrate_bom
Revises: 055_add_product_image_url
Create Date: 2025-01-21
"""

from alembic import op
from sqlalchemy import text

# revision identifiers
revision = "056_migrate_bom"
down_revision = "055_add_product_image_url"
branch_labels = None
depends_on = None


def upgrade():
    """
    Migrate bom_lines to routing_operation_materials.

    For each product with a BOM:
    1. Find the active routing for that product
    2. Map production-stage materials to first operation
    3. Map shipping-stage materials to shipping operation (or last)
    4. Create routing_operation_materials entries
    """
    connection = op.get_bind()

    # Get all active BOMs with their lines
    boms_query = text("""
        SELECT
            b.id as bom_id,
            b.product_id,
            bl.id as line_id,
            bl.component_id,
            bl.sequence,
            bl.quantity,
            bl.unit,
            bl.consume_stage,
            bl.is_cost_only,
            bl.scrap_factor,
            bl.notes
        FROM boms b
        JOIN bom_lines bl ON bl.bom_id = b.id
        WHERE b.active = true
        ORDER BY b.product_id, bl.sequence
    """)

    bom_lines = connection.execute(boms_query).fetchall()

    if not bom_lines:
        print("No active BOM lines to migrate")
        return

    print(f"Found {len(bom_lines)} BOM lines to migrate")

    # Group by product
    products_lines = {}
    for row in bom_lines:
        pid = row.product_id
        if pid not in products_lines:
            products_lines[pid] = []
        products_lines[pid].append(row)

    migrated_count = 0
    skipped_count = 0

    for product_id, lines in products_lines.items():
        # Find active routing for this product
        routing_query = text("""
            SELECT id FROM routings
            WHERE product_id = :product_id
            AND is_active = true
            ORDER BY version DESC
            LIMIT 1
        """)
        routing_result = connection.execute(routing_query, {"product_id": product_id}).fetchone()

        if not routing_result:
            print(f"  Product {product_id}: No active routing found, skipping {len(lines)} lines")
            skipped_count += len(lines)
            continue

        routing_id = routing_result[0]

        # Get operations for this routing
        ops_query = text("""
            SELECT
                id,
                sequence,
                operation_code,
                operation_name
            FROM routing_operations
            WHERE routing_id = :routing_id
            ORDER BY sequence
        """)
        operations = connection.execute(ops_query, {"routing_id": routing_id}).fetchall()

        if not operations:
            print(f"  Product {product_id}: Routing {routing_id} has no operations, skipping")
            skipped_count += len(lines)
            continue

        # Find production operation (first one)
        production_op = operations[0]

        # Find shipping operation (look for 'ship' or 'pack' in name, else use last)
        shipping_op = None
        for routing_op in operations:
            op_name = (routing_op.operation_name or "").lower()
            op_code = (routing_op.operation_code or "").lower()
            if "ship" in op_name or "ship" in op_code or "pack" in op_name or "pack" in op_code:
                shipping_op = routing_op
                break
        if not shipping_op:
            shipping_op = operations[-1]  # Use last operation

        # Migrate each line
        for line in lines:
            # Determine target operation
            if line.consume_stage == "shipping":
                target_op = shipping_op
            else:
                target_op = production_op  # Default: production stage

            # Check if material already exists for this operation+component
            existing_query = text("""
                SELECT id FROM routing_operation_materials
                WHERE routing_operation_id = :op_id
                AND component_id = :comp_id
            """)
            existing = connection.execute(
                existing_query, {"op_id": target_op.id, "comp_id": line.component_id}
            ).fetchone()

            if existing:
                print(
                    f"  Product {product_id}: Material {line.component_id} already exists at op {target_op.id}, skipping"
                )
                skipped_count += 1
                continue

            # Insert new routing_operation_material
            insert_query = text("""
                INSERT INTO routing_operation_materials (
                    routing_operation_id,
                    component_id,
                    quantity,
                    quantity_per,
                    unit,
                    scrap_factor,
                    is_cost_only,
                    is_optional,
                    notes,
                    created_at,
                    updated_at
                ) VALUES (
                    :op_id,
                    :comp_id,
                    :qty,
                    'unit',
                    :unit,
                    :scrap,
                    :cost_only,
                    false,
                    :notes,
                    NOW(),
                    NOW()
                )
            """)

            connection.execute(
                insert_query,
                {
                    "op_id": target_op.id,
                    "comp_id": line.component_id,
                    "qty": float(line.quantity) if line.quantity else 1.0,
                    "unit": line.unit or "EA",
                    "scrap": float(line.scrap_factor) if line.scrap_factor else 0,
                    "cost_only": line.is_cost_only or False,
                    "notes": f"[Migrated from BOM] {line.notes or ''}".strip(),
                },
            )

            migrated_count += 1

    print(f"Migration complete: {migrated_count} lines migrated, {skipped_count} skipped")


def downgrade():
    """
    Remove migrated entries.

    We identify migrated entries by the '[Migrated from BOM]' prefix in notes.
    """
    connection = op.get_bind()

    delete_query = text("""
        DELETE FROM routing_operation_materials
        WHERE notes LIKE '[Migrated from BOM]%'
    """)

    result = connection.execute(delete_query)
    print(f"Removed {result.rowcount} migrated routing operation materials")
