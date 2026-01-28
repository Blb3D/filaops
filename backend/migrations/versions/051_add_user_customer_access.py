"""Add user_customer_access table for multi-customer portal access

Revision ID: 051_add_user_customer_access
Revises: 047_add_entity_members
Create Date: 2026-01-19

This enables:
- One portal user to access multiple customer accounts
- Regional managers ordering for multiple locations
- Franchise owners managing multiple franchise locations
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "051_add_user_customer_access"
down_revision = "047_add_entity_members"
branch_labels = None
depends_on = None


def upgrade():
    # Create user_customer_access join table
    op.create_table(
        "user_customer_access",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("granted_by", sa.Integer(), nullable=True),
        # Primary key
        sa.PrimaryKeyConstraint("id"),
        # Foreign keys
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_by"], ["users.id"], ondelete="SET NULL"),
        # Unique constraint on user_id + customer_id
        sa.UniqueConstraint("user_id", "customer_id", name="uq_user_customer"),
    )

    # Create indexes for fast lookups
    op.create_index("ix_user_customer_access_user_id", "user_customer_access", ["user_id"])
    op.create_index("ix_user_customer_access_customer_id", "user_customer_access", ["customer_id"])

    # Backfill: Create access records for existing users with customer_id set
    # This preserves existing single-customer access
    op.execute("""
        INSERT INTO user_customer_access (user_id, customer_id, role, is_default, created_at)
        SELECT id, customer_id, 'admin', true, NOW()
        FROM users
        WHERE customer_id IS NOT NULL
          AND account_type = 'customer'
          AND NOT EXISTS (
              SELECT 1 FROM user_customer_access uca
              WHERE uca.user_id = users.id AND uca.customer_id = users.customer_id
          )
    """)


def downgrade():
    op.drop_index("ix_user_customer_access_customer_id", table_name="user_customer_access")
    op.drop_index("ix_user_customer_access_user_id", table_name="user_customer_access")
    op.drop_table("user_customer_access")
