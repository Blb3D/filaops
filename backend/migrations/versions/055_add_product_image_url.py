"""Add image_url column to products

Revision ID: 055
Revises: 054
Create Date: 2026-01-20

Adds image_url column to products table for product images.
Used by Portal for product display and future Shopify sync.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "055_add_product_image_url"
down_revision = "054_add_printer_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("image_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "image_url")
