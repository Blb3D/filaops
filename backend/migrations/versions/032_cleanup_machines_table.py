"""
032: Cleanup machines table and consolidate to resources

This migration:
1. Adds printer_class column to resources table
2. Updates FK on production_order_operations to point to resources
3. Cleans up seed work centers (WC-PRINT, WC-ASSY)
4. Drops the machines table (was seeded test data only)

Date: 2024-12-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers
revision = "032_cleanup_machines_table"
down_revision = "031_add_stocking_policy"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # =========================================================================
    # Step 1: Add printer_class to resources table
    # =========================================================================
    print("Adding printer_class column to resources...")
    op.add_column("resources", sa.Column("printer_class", sa.String(20), nullable=True, server_default="open"))

    # =========================================================================
    # Step 2: Set Leonardo (BAM-001) to enclosed, others to open
    # =========================================================================
    print("Setting printer classes...")
    conn.execute(text("UPDATE resources SET printer_class = 'open' WHERE printer_class IS NULL"))
    conn.execute(text("UPDATE resources SET printer_class = 'enclosed' WHERE code = 'BAM-001'"))

    # =========================================================================
    # Step 3: Check if any operations reference the machines we're about to delete
    # =========================================================================
    result = conn.execute(
        text("""
        SELECT poo.id, poo.resource_id, m.code as machine_code
        FROM production_order_operations poo
        JOIN machines m ON poo.resource_id = m.id
        WHERE poo.resource_id IS NOT NULL
    """)
    ).fetchall()

    if result:
        print(f"WARNING: {len(result)} operations reference machines table:")
        for row in result:
            print(f"  - Operation {row[0]} references machine {row[2]} (id={row[1]})")
        print("Setting these resource_id values to NULL")
        conn.execute(
            text(
                "UPDATE production_order_operations SET resource_id = NULL WHERE resource_id IN (SELECT id FROM machines)"
            )
        )

    # =========================================================================
    # Step 4: Drop the FK constraint pointing to machines
    # =========================================================================
    print("Updating FK constraint...")

    # Get the actual constraint name
    result = conn.execute(
        text("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'production_order_operations' 
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE '%resource%'
    """)
    ).fetchone()

    if result:
        constraint_name = result[0]
        print(f"  Dropping constraint: {constraint_name}")
        op.drop_constraint(constraint_name, "production_order_operations", type_="foreignkey")

    # Create new FK pointing to resources
    print("  Creating new FK to resources table...")
    op.create_foreign_key(
        "fk_poo_resource_id", "production_order_operations", "resources", ["resource_id"], ["id"], ondelete="SET NULL"
    )

    # =========================================================================
    # Step 5: Delete seed work centers and their dependent data
    # =========================================================================
    print("Cleaning up seed data...")

    # First delete machines (FK constraint to work_centers)
    conn.execute(text("DELETE FROM machines"))
    print("  Deleted all machines")

    # Get IDs of seed work centers
    seed_wc_ids = conn.execute(
        text("""
        SELECT id FROM work_centers 
        WHERE code IN ('WC-PRINT', 'WC-ASSY')
    """)
    ).fetchall()
    seed_wc_ids = [row[0] for row in seed_wc_ids]

    if seed_wc_ids:
        print(f"  Found seed work center IDs: {seed_wc_ids}")

        # Get routing_operation IDs that will be deleted
        routing_op_ids = conn.execute(
            text("""
            SELECT id FROM routing_operations 
            WHERE work_center_id = ANY(:ids)
        """),
            {"ids": seed_wc_ids},
        ).fetchall()
        routing_op_ids = [row[0] for row in routing_op_ids]
        print(f"  Found {len(routing_op_ids)} routing_operations to delete: {routing_op_ids}")

        # NULL out the routing_operation_id reference on any production_order_operations
        # This breaks the FK link so we can delete the routing_operations
        if routing_op_ids:
            result = conn.execute(
                text("""
                UPDATE production_order_operations 
                SET routing_operation_id = NULL
                WHERE routing_operation_id = ANY(:ids)
                RETURNING id
            """),
                {"ids": routing_op_ids},
            ).fetchall()
            print(f"  Nulled routing_operation_id on {len(result)} production_order_operations")

        # Delete production_order_operations that have work_center_id in seed list
        result = conn.execute(
            text("""
            DELETE FROM production_order_operations 
            WHERE work_center_id = ANY(:ids)
            RETURNING id
        """),
            {"ids": seed_wc_ids},
        ).fetchall()
        print(f"  Deleted {len(result)} production_order_operations by work_center_id")

        # Now delete routing_operations
        result = conn.execute(
            text("""
            DELETE FROM routing_operations 
            WHERE work_center_id = ANY(:ids)
            RETURNING id
        """),
            {"ids": seed_wc_ids},
        ).fetchall()
        print(f"  Deleted {len(result)} routing_operations")

        # Now delete the work centers
        result = conn.execute(
            text("""
            DELETE FROM work_centers 
            WHERE code IN ('WC-PRINT', 'WC-ASSY')
            RETURNING code
        """)
        ).fetchall()

        for row in result:
            print(f"  Deleted seed work center: {row[0]}")

    # =========================================================================
    # Step 6: Drop machines table
    # =========================================================================
    print("Dropping machines table...")
    op.drop_table("machines")

    print("Migration complete!")


def downgrade():
    conn = op.get_bind()

    # =========================================================================
    # Recreate machines table
    # =========================================================================
    print("Recreating machines table...")
    op.create_table(
        "machines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("work_center_id", sa.Integer(), sa.ForeignKey("work_centers.id"), nullable=False),
        sa.Column("machine_type", sa.String(100), nullable=True),
        sa.Column("compatible_materials", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), server_default="available", nullable=False, index=True),
        sa.Column("bed_size_x", sa.Numeric(10, 2), nullable=True),
        sa.Column("bed_size_y", sa.Numeric(10, 2), nullable=True),
        sa.Column("bed_size_z", sa.Numeric(10, 2), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("bambu_serial", sa.String(100), nullable=True),
        sa.Column("bambu_access_code", sa.String(20), nullable=True),
        sa.Column("bambu_ip_address", sa.String(45), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # =========================================================================
    # Revert FK to machines
    # =========================================================================
    print("Reverting FK constraint...")
    op.drop_constraint("fk_poo_resource_id", "production_order_operations", type_="foreignkey")

    op.create_foreign_key(
        "production_order_operations_resource_id_fkey",
        "production_order_operations",
        "machines",
        ["resource_id"],
        ["id"],
    )

    # =========================================================================
    # Drop printer_class from resources
    # =========================================================================
    print("Dropping printer_class column...")
    op.drop_column("resources", "printer_class")

    print("Downgrade complete. Note: Seed data not restored.")
