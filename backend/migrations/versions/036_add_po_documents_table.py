"""Add purchase_order_documents table for multi-file storage

This migration adds support for multiple documents per purchase order:
- Invoices, packing slips, receipts, quotes, etc.
- File metadata (name, size, type)
- Integration with Google Drive and local storage

Also creates vendor_items table for SKU mapping memory.

Revision ID: 036
Revises: 035
Create Date: 2025-01-03

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "036_add_po_documents"
down_revision: Union[str, None] = "035_add_purchase_uom"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add purchase_order_documents and vendor_items tables."""

    # 1. Create purchase_order_documents table
    op.create_table(
        "purchase_order_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_order_id", sa.Integer(), nullable=False),
        sa.Column(
            "document_type",
            sa.String(length=50),
            nullable=False,
            comment="Type: invoice, packing_slip, receipt, quote, other",
        ),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column(
            "original_file_name", sa.String(length=255), nullable=True, comment="Original filename before any renaming"
        ),
        sa.Column(
            "file_url", sa.String(length=1000), nullable=True, comment="URL for Google Drive or external storage"
        ),
        sa.Column("file_path", sa.String(length=500), nullable=True, comment="Local file path if stored locally"),
        sa.Column(
            "storage_type",
            sa.String(length=50),
            nullable=False,
            server_default="local",
            comment="Storage backend: local, google_drive, s3",
        ),
        sa.Column("file_size", sa.Integer(), nullable=True, comment="File size in bytes"),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column(
            "google_drive_id", sa.String(length=100), nullable=True, comment="Google Drive file ID for direct access"
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.String(length=100), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Index for quick lookups by PO
    op.create_index("ix_po_documents_po_id", "purchase_order_documents", ["purchase_order_id"])
    op.create_index("ix_po_documents_type", "purchase_order_documents", ["document_type"])

    # NOTE: preferred_vendor_id and vendor_sku columns already exist in initial schema
    # (b1815de543ea_001_initial_postgres_schema.py), so we don't add them here

    # 2. Create vendor_items table for SKU mapping memory (from handoff doc)
    op.create_table(
        "vendor_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("vendor_sku", sa.String(length=100), nullable=False, comment="SKU used by the vendor"),
        sa.Column(
            "vendor_description",
            sa.String(length=500),
            nullable=True,
            comment="Description as shown on vendor invoices",
        ),
        sa.Column("product_id", sa.Integer(), nullable=True, comment="Mapped FilaOps product (NULL = unmapped)"),
        sa.Column("default_unit_cost", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("default_purchase_unit", sa.String(length=20), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True, comment="Last time this item appeared on an invoice"),
        sa.Column(
            "times_ordered", sa.Integer(), server_default="0", comment="Number of times this item has been ordered"
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vendor_id", "vendor_sku", name="uq_vendor_items_vendor_sku"),
    )

    op.create_index("ix_vendor_items_vendor_id", "vendor_items", ["vendor_id"])
    op.create_index("ix_vendor_items_product_id", "vendor_items", ["product_id"])


def downgrade() -> None:
    """Remove tables created by this migration."""
    # Drop vendor_items table and its indexes
    op.drop_index("ix_vendor_items_product_id", "vendor_items")
    op.drop_index("ix_vendor_items_vendor_id", "vendor_items")
    op.drop_table("vendor_items")

    # Drop purchase_order_documents table and its indexes
    op.drop_index("ix_po_documents_type", "purchase_order_documents")
    op.drop_index("ix_po_documents_po_id", "purchase_order_documents")
    op.drop_table("purchase_order_documents")

    # NOTE: preferred_vendor_id and vendor_sku are NOT dropped here
    # because they exist in the initial schema, not added by this migration
