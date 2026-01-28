"""
Purchase Order Document model for multi-file storage
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class PurchaseOrderDocument(Base):
    """Document attached to a Purchase Order"""

    __tablename__ = "purchase_order_documents"

    id = Column(Integer, primary_key=True, index=True)

    # Parent PO
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)

    # Document metadata
    document_type = Column(String(50), nullable=False)  # invoice, packing_slip, receipt, quote, other
    file_name = Column(String(255), nullable=False)
    original_file_name = Column(String(255), nullable=True)

    # Storage location (supports multiple backends)
    file_url = Column(String(1000), nullable=True)  # External URL (Google Drive, etc.)
    file_path = Column(String(500), nullable=True)  # Local file path
    storage_type = Column(String(50), nullable=False, default="local")  # local, google_drive, s3

    # File info
    file_size = Column(Integer, nullable=True)  # Size in bytes
    mime_type = Column(String(100), nullable=True)

    # Google Drive specific
    google_drive_id = Column(String(100), nullable=True)

    # Additional info
    notes = Column(Text, nullable=True)
    uploaded_by = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship
    purchase_order = relationship("PurchaseOrder", back_populates="documents")

    # Document type choices
    DOCUMENT_TYPES = [
        ("invoice", "Invoice"),
        ("packing_slip", "Packing Slip"),
        ("receipt", "Receipt"),
        ("quote", "Quote"),
        ("shipping_label", "Shipping Label"),
        ("other", "Other"),
    ]

    def __repr__(self):
        return f"<PurchaseOrderDocument {self.id}: {self.document_type} - {self.file_name}>"

    @property
    def download_url(self):
        """Get the appropriate download URL based on storage type"""
        if self.storage_type == "google_drive" and self.google_drive_id:
            return f"https://drive.google.com/uc?id={self.google_drive_id}&export=download"
        elif self.file_url:
            return self.file_url
        elif self.file_path:
            # Local files served through API
            return f"/api/v1/purchase-orders/{self.purchase_order_id}/documents/{self.id}/download"
        return None

    @property
    def preview_url(self):
        """Get preview URL (for Google Drive)"""
        if self.storage_type == "google_drive" and self.google_drive_id:
            return f"https://drive.google.com/file/d/{self.google_drive_id}/preview"
        return self.download_url


class VendorItem(Base):
    """Vendor-specific item mapping for SKU memory"""

    __tablename__ = "vendor_items"

    id = Column(Integer, primary_key=True, index=True)

    # Vendor reference
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False)

    # Vendor's item info
    vendor_sku = Column(String(100), nullable=False)
    vendor_description = Column(String(500), nullable=True)

    # Mapping to our product (NULL = unmapped)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)

    # Default values for quick PO creation
    default_unit_cost = Column(String(20), nullable=True)  # Stored as string to preserve precision
    default_purchase_unit = Column(String(20), nullable=True)

    # Usage tracking
    last_seen_at = Column(DateTime, nullable=True)
    times_ordered = Column(Integer, default=0)

    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    vendor = relationship("Vendor", backref="vendor_items")
    product = relationship("Product", backref="vendor_items")

    def __repr__(self):
        return f"<VendorItem {self.vendor_id}:{self.vendor_sku}>"
