"""baseline - stamp existing database

Revision ID: baseline_001
Revises:
Create Date: 2025-12-09

This is a baseline migration that stamps the existing database state.
No actual changes are made - this just marks the database as being at
a known point in the migration history.

The actual schema was created via SQLAlchemy's create_all() and manual migrations.
Future migrations will track changes from this point forward.
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "baseline_001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Baseline migration - no changes.

    This migration exists to mark the existing database schema as the
    starting point for future Alembic-managed migrations.

    All existing tables were created via:
    - SQLAlchemy's Base.metadata.create_all()
    - Manual SQL scripts
    - Previous ad-hoc migrations
    """
    pass


def downgrade() -> None:
    """
    Cannot downgrade from baseline.

    This would require dropping all tables, which is destructive.
    If you need to reset, restore from backup or recreate the database.
    """
    pass
