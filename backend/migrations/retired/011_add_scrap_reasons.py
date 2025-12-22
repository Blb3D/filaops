"""Add scrap_reasons table for configurable failure modes

Revision ID: 011_add_scrap_reasons
Revises: 010_merge_heads
Create Date: 2025-12-16

Adds:
- scrap_reasons table: Configurable reasons for scrapping production orders
- Default seed data for common 3D printing failure modes
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '011_add_scrap_reasons'
down_revision: Union[str, Sequence[str], None] = '010_merge_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect

    connection = op.get_bind()
    inspector = inspect(connection)
    existing_tables = inspector.get_table_names()

    if 'scrap_reasons' not in existing_tables:
        op.create_table(
            'scrap_reasons',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(50), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('sequence', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('GETUTCDATE()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('GETUTCDATE()')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_scrap_reasons_code', 'scrap_reasons', ['code'], unique=True)
        op.create_index('ix_scrap_reasons_active', 'scrap_reasons', ['active'], unique=False)

        # Seed default scrap reasons for 3D printing
        connection.execute(sa.text("""
            INSERT INTO scrap_reasons (code, name, description, sequence) VALUES
            ('adhesion', 'Bed Adhesion Failure', 'Print failed to adhere to build plate', 1),
            ('layer_shift', 'Layer Shift', 'Layers shifted mid-print due to belt slip or collision', 2),
            ('spaghetti', 'Spaghetti (Detachment)', 'Print detached from bed and became tangled filament', 3),
            ('warping', 'Warping', 'Print corners lifted due to thermal contraction', 4),
            ('stringing', 'Excessive Stringing', 'Too many thin strings between parts, unusable quality', 5),
            ('nozzle_clog', 'Nozzle Clog', 'Nozzle clogged mid-print causing under-extrusion or failure', 6),
            ('under_extrusion', 'Under-Extrusion', 'Not enough filament extruded, weak or missing layers', 7),
            ('over_extrusion', 'Over-Extrusion', 'Too much filament extruded, blobby or inaccurate print', 8),
            ('blob', 'Blob on Print', 'Molten blob formed on nozzle or print surface', 9),
            ('power_failure', 'Power Failure', 'Print failed due to power outage', 10),
            ('material_runout', 'Material Ran Out', 'Filament ran out before print completed', 11),
            ('z_offset', 'Z-Offset Issue', 'First layer too high or too low', 12),
            ('support_failure', 'Support Failure', 'Support structures failed causing print defects', 13),
            ('other', 'Other', 'Other reason not listed (specify in notes)', 99)
        """))


def downgrade() -> None:
    op.drop_index('ix_scrap_reasons_active', 'scrap_reasons')
    op.drop_index('ix_scrap_reasons_code', 'scrap_reasons')
    op.drop_table('scrap_reasons')
