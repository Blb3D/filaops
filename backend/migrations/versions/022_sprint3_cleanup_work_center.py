"""Sprint 3-4: Remove duplicate active column from work_centers

Revision ID: 022_sprint3_cleanup_work_center
Revises: 905ef924f499
Create Date: 2025-12-23 (Sprint 3-4 - Data Model Cleanup)

WorkCenter model had both 'is_active' and 'active' columns tracking the same state.
This migration:
1. Syncs any mismatched data (active -> is_active)
2. Removes the duplicate 'active' column

NOTE: Uses defensive programming - skips if column doesn't exist.

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "022_sprint3_cleanup_work_center"
down_revision = "905ef924f499"
branch_labels = None
depends_on = None


def _column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    try:
        bind = op.get_bind()
        inspector = inspect(bind)
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def upgrade():
    # Check if the 'active' column exists before trying to drop it
    if not _column_exists("work_centers", "active"):
        print("  Column 'active' does not exist in work_centers, skipping...")
        return

    # First, sync any mismatched values: if active is False, set is_active to False
    try:
        op.execute("""
            UPDATE work_centers
            SET is_active = active
            WHERE is_active != active
        """)
    except Exception as e:
        print(f"  Sync update failed (may be expected): {e}")

    # Now drop the duplicate column
    try:
        op.drop_column("work_centers", "active")
    except Exception as e:
        print(f"  Could not drop 'active' column: {e}")


def downgrade():
    # Check if the 'active' column already exists
    if _column_exists("work_centers", "active"):
        print("  Column 'active' already exists in work_centers, skipping...")
        return

    # Re-add the active column with same default as is_active
    op.add_column("work_centers", sa.Column("active", sa.Boolean(), nullable=False, server_default="true"))

    # Sync values from is_active to active
    try:
        op.execute("""
            UPDATE work_centers
            SET active = is_active
        """)
    except Exception as e:
        print(f"  Sync update failed (may be expected): {e}")
