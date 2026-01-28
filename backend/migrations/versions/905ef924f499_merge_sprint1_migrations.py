"""merge_sprint1_migrations

Revision ID: 905ef924f499
Revises: 021_add_performance_indexes, 65be66a7c00f
Create Date: 2025-12-23 22:24:14.759204

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "905ef924f499"
down_revision: Union[str, Sequence[str], None] = ("021_add_performance_indexes", "65be66a7c00f")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
