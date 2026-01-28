"""Add entity_members table for LLC/Partnership member tracking

Revision ID: 047_add_entity_members
Revises: 045_seed_coa
Create Date: 2026-01-16

Stores LLC members/partners for K-1 allocation:
- Ownership percentages
- Capital account tracking
- Member status (active/inactive/withdrawn)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "047_add_entity_members"
down_revision = "045_seed_coa"
branch_labels = None
depends_on = None


def upgrade():
    """Create entity_members table."""
    op.create_table(
        "entity_members",
        sa.Column("id", sa.Integer(), nullable=False),
        # Member identification
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("member_type", sa.String(20), nullable=False, server_default="individual"),
        sa.Column("tax_id_last4", sa.String(4), nullable=True),
        # Address
        sa.Column("address_line1", sa.String(255), nullable=True),
        sa.Column("address_line2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(50), nullable=True),
        sa.Column("zip", sa.String(20), nullable=True),
        # Ownership details
        sa.Column("ownership_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("capital_account", sa.Numeric(18, 4), nullable=False, server_default="0"),
        # Status
        sa.Column("is_managing_member", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        # Audit
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        # Primary key
        sa.PrimaryKeyConstraint("id"),
    )

    # Index on status for filtering active members
    op.create_index("ix_entity_members_status", "entity_members", ["status"])


def downgrade():
    """Drop entity_members table."""
    op.drop_index("ix_entity_members_status", table_name="entity_members")
    op.drop_table("entity_members")
