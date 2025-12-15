"""ensure production order code unique constraint

Revision ID: 007_ensure_code_unique
Revises: 006_add_mrp_tracking_to_sales_orders
Create Date: 2025-12-14

Ensures that production_orders.code has a unique constraint to prevent
duplicate production order codes from being generated during concurrent
requests. This is critical for the row-level locking strategy used in
PO code generation.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = '007_ensure_code_unique'
down_revision: Union[str, None] = '006_add_mrp_tracking_to_sales_orders'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# OPTIONAL: Automated Deduplication Helper
# ==========================================
# Uncomment and call this function if you want to automatically resolve duplicates
# by keeping the newest record (highest ID) for each duplicate code.
# WARNING: This will DELETE data. Review duplicates first before using.
#
# def deduplicate_production_order_codes(conn) -> int:
#     """
#     Automatically deduplicate production_orders.code by keeping the newest record.
#     
#     IMPORTANT WARNINGS:
#     1. TRANSACTION MANAGEMENT: This function does NOT call commit(). It relies on
#        Alembic's automatic transaction management. Do not add conn.commit() as it
#        will break Alembic's rollback capability.
#     
#     2. FOREIGN KEY CONSTRAINTS: Deleting production_orders rows may FAIL or CASCADE
#        depending on your database schema. Before running this function:
#        - Check if other tables reference production_orders.id (e.g., production_order_materials,
#          production_order_routing, inventory_transactions, etc.)
#        - Determine if FKs are set to CASCADE, RESTRICT, or SET NULL
#        - If CASCADE: Related rows will be automatically deleted (DATA LOSS!)
#        - If RESTRICT/NO ACTION: The DELETE will fail with FK constraint error
#        - RECOMMENDED: Manually merge related data before running this, or update
#          the query to only delete truly orphaned records
#     
#     3. DATA LOSS: This permanently deletes production_order records. Ensure you have:
#        - Database backup
#        - Reviewed which records will be deleted
#        - Confirmed that deleting older duplicates won't lose critical data
#     
#     Args:
#         conn: Database connection from Alembic (op.get_bind())
#     
#     Returns:
#         Number of duplicate records deleted
#     
#     Raises:
#         IntegrityError: If foreign key constraints prevent deletion
#     """
#     # Find duplicates and keep only the record with the highest ID (newest)
#     delete_query = sa.text("""
#         DELETE FROM production_orders
#         WHERE id IN (
#             SELECT id
#             FROM (
#                 SELECT id, code,
#                        ROW_NUMBER() OVER (PARTITION BY code ORDER BY id DESC) as row_num
#                 FROM production_orders
#                 WHERE code IS NOT NULL
#             ) ranked
#             WHERE row_num > 1
#         )
#     """)
#     
#     result = conn.execute(delete_query)
#     deleted_count = result.rowcount
#     # DO NOT call conn.commit() - Alembic manages transactions automatically
#     
#     print(f"Deleted {deleted_count} duplicate production_order record(s)")
#     print(f"Note: Transaction will be committed by Alembic if migration succeeds")
#     return deleted_count


def upgrade() -> None:
    """
    Ensure production_orders.code has a unique constraint.
    
    This migration is idempotent - it checks if the constraint already exists
    before attempting to create it.
    """
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Check if table exists
    if 'production_orders' not in inspector.get_table_names():
        print("Table production_orders does not exist, skipping constraint creation")
        return
    
    # Check if unique constraint or index already exists on 'code'
    constraint_exists = False
    
    # Check unique constraints
    try:
        unique_constraints = inspector.get_unique_constraints('production_orders')
        for constraint in unique_constraints:
            if 'code' in constraint.get('column_names', []):
                constraint_exists = True
                print(f"Unique constraint already exists: {constraint['name']}")
                break
    except Exception as e:
        print(f"Could not check unique constraints: {e}")
    
    # Check unique indexes if constraint not found
    if not constraint_exists:
        try:
            indexes = inspector.get_indexes('production_orders')
            for index in indexes:
                if 'code' in index.get('column_names', []) and index.get('unique', False):
                    constraint_exists = True
                    print(f"Unique index already exists: {index['name']}")
                    break
        except Exception as e:
            print(f"Could not check indexes: {e}")
    
    # Create unique constraint if it doesn't exist
    if not constraint_exists:
        print("Creating unique constraint on production_orders.code")
        
        # Pre-check: Detect any duplicate code values before attempting constraint creation
        print("Checking for duplicate production_orders.code values...")
        duplicate_check_query = sa.text("""
            SELECT code, COUNT(*) as count
            FROM production_orders
            WHERE code IS NOT NULL
            GROUP BY code
            HAVING COUNT(*) > 1
            ORDER BY count DESC, code
        """)
        
        duplicates = conn.execute(duplicate_check_query).fetchall()
        
        if duplicates:
            # Duplicates found - log details and raise actionable error
            duplicate_count = len(duplicates)
            total_duplicate_rows = sum(row[1] for row in duplicates)
            
            print(f"❌ ERROR: Found {duplicate_count} duplicate production order code(s) affecting {total_duplicate_rows} rows:")
            for code, count in duplicates:
                print(f"  - Code '{code}': {count} occurrences")
            
            # Provide detailed error with resolution steps
            error_msg = (
                f"Cannot create unique constraint on production_orders.code: "
                f"{duplicate_count} duplicate code value(s) found.\n\n"
                f"Duplicate codes detected:\n"
            )
            for code, count in duplicates:
                error_msg += f"  - '{code}': {count} occurrences\n"
            
            error_msg += (
                "\nRESOLUTION REQUIRED:\n"
                "Before running this migration, you must resolve the duplicate production order codes.\n\n"
                "Option 1 - Manual Resolution (Recommended):\n"
                "  1. Connect to your database\n"
                "  2. Run the duplicate detection query:\n"
                "     SELECT code, COUNT(*) as count, string_agg(id::text, ', ') as ids\n"
                "     FROM production_orders WHERE code IS NOT NULL\n"
                "     GROUP BY code HAVING COUNT(*) > 1;\n"
                "  3. Manually review and merge/delete duplicate records\n"
                "  4. Update any foreign key references if needed\n\n"
                "Option 2 - Automated Deduplication (Use with caution):\n"
                "  Uncomment the deduplication logic in this migration file to keep\n"
                "  the newest record per code and delete older duplicates.\n\n"
                "After resolving duplicates, re-run the migration."
            )
            
            raise ValueError(error_msg)
        else:
            print("✅ No duplicate production_orders.code values found")
        
        # Proceed with constraint creation
        try:
            op.create_unique_constraint(
                'uq_production_orders_code',
                'production_orders',
                ['code']
            )
            print("✅ Successfully created unique constraint on production_orders.code")
        except Exception as e:
            print(f"⚠️  Warning: Could not create unique constraint (it may already exist): {e}")
    else:
        print("✅ Unique constraint on production_orders.code already exists")


def downgrade() -> None:
    """
    Remove the unique constraint on production_orders.code.
    
    Warning: This will allow duplicate production order codes!
    Only downgrade if absolutely necessary.
    """
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Check if constraint exists before trying to drop it
    try:
        unique_constraints = inspector.get_unique_constraints('production_orders')
        for constraint in unique_constraints:
            if constraint['name'] == 'uq_production_orders_code':
                op.drop_constraint('uq_production_orders_code', 'production_orders', type_='unique')
                print("Dropped unique constraint uq_production_orders_code")
                return
    except Exception as e:
        print(f"Could not drop constraint: {e}")
    
    print("Constraint uq_production_orders_code not found or already removed")
