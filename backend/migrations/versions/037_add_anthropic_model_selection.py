"""add_anthropic_model_selection

Revision ID: 037_add_anthropic_model
Revises: 2940c6a93ea7
Create Date: 2026-01-05

Adds anthropic model selection to company_settings for configurable
Claude model (Haiku, Sonnet, Opus) with cost implications.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "037_add_anthropic_model"
down_revision: Union[str, Sequence[str], None] = "2940c6a93ea7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add anthropic model column to company_settings."""
    # Check if column already exists (defensive - handles inconsistent migration states)
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'company_settings' AND column_name = 'ai_anthropic_model'
    """)
    )
    if result.fetchone() is None:
        op.add_column(
            "company_settings",
            sa.Column(
                "ai_anthropic_model", sa.String(length=100), nullable=True, server_default="claude-sonnet-4-20250514"
            ),
        )


def downgrade() -> None:
    """Remove anthropic model column from company_settings."""
    op.drop_column("company_settings", "ai_anthropic_model")
