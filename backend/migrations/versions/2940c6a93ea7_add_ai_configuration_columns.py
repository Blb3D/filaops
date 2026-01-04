"""add_ai_configuration_columns

Revision ID: 2940c6a93ea7
Revises: 036_add_po_documents
Create Date: 2026-01-04 17:36:51.626209

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2940c6a93ea7'
down_revision: Union[str, Sequence[str], None] = '036_add_po_documents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add AI configuration columns to company_settings."""
    op.add_column('company_settings', sa.Column('ai_provider', sa.String(length=20), nullable=True))
    op.add_column('company_settings', sa.Column('ai_api_key', sa.String(length=500), nullable=True))
    op.add_column('company_settings', sa.Column('ai_ollama_url', sa.String(length=255), nullable=True, server_default='http://localhost:11434'))
    op.add_column('company_settings', sa.Column('ai_ollama_model', sa.String(length=100), nullable=True, server_default='llama3.2'))
    op.add_column('company_settings', sa.Column('external_ai_blocked', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Remove AI configuration columns from company_settings."""
    op.drop_column('company_settings', 'external_ai_blocked')
    op.drop_column('company_settings', 'ai_ollama_model')
    op.drop_column('company_settings', 'ai_ollama_url')
    op.drop_column('company_settings', 'ai_api_key')
    op.drop_column('company_settings', 'ai_provider')
