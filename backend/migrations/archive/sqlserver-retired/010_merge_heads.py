"""Merge printer and accounting migration heads

Revision ID: 010_merge_heads
Revises: 008_printer_brand_agnostic, 009_accounting_enhancements
Create Date: 2025-12-16

Merges the two feature branches:
- 008_printer_brand_agnostic: Printer brand management
- 009_accounting_enhancements: Tax and accounting fields
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "010_merge_heads"
down_revision: Union[str, Sequence[str], None] = ("008_printer_brand_agnostic", "009_accounting_enhancements")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge migration - no changes needed
    pass


def downgrade() -> None:
    # Merge migration - no changes needed
    pass
