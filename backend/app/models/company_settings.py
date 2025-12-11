"""
Company Settings Model

Stores company-wide settings including:
- Company name, address, contact info
- Logo image
- Tax configuration
- Quote/Invoice settings
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, LargeBinary, func

from app.db.base import Base


class CompanySettings(Base):
    """
    Company-wide settings (singleton table - only one row)
    """
    __tablename__ = "company_settings"

    id = Column(Integer, primary_key=True, default=1)

    # Company Info
    company_name = Column(String(255), nullable=True)
    company_address_line1 = Column(String(255), nullable=True)
    company_address_line2 = Column(String(255), nullable=True)
    company_city = Column(String(100), nullable=True)
    company_state = Column(String(50), nullable=True)
    company_zip = Column(String(20), nullable=True)
    company_country = Column(String(100), nullable=True, default="USA")
    company_phone = Column(String(30), nullable=True)
    company_email = Column(String(255), nullable=True)
    company_website = Column(String(255), nullable=True)

    # Logo (stored as binary, or file path)
    logo_data = Column(LargeBinary, nullable=True)  # PNG/JPG binary data
    logo_filename = Column(String(255), nullable=True)
    logo_mime_type = Column(String(100), nullable=True)

    # Tax Configuration
    tax_enabled = Column(Boolean, nullable=False, default=False)
    tax_rate = Column(Numeric(5, 4), nullable=True)  # e.g., 0.0825 for 8.25%
    tax_name = Column(String(50), nullable=True, default="Sales Tax")  # "Sales Tax", "VAT", etc.
    tax_registration_number = Column(String(100), nullable=True)  # Tax ID, VAT number, etc.

    # Quote Settings
    default_quote_validity_days = Column(Integer, nullable=False, default=30)
    quote_terms = Column(String(2000), nullable=True)  # Terms & conditions text
    quote_footer = Column(String(1000), nullable=True)  # Footer text for quotes

    # Invoice Settings (for future)
    invoice_prefix = Column(String(20), nullable=True, default="INV")
    invoice_terms = Column(String(2000), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())

    def __repr__(self):
        """
        Provide a concise string representation of the CompanySettings instance.
        
        Returns:
            str: A string in the format "<CompanySettings(company_name=...)>" showing the instance's company_name.
        """
        return f"<CompanySettings(company_name={self.company_name})>"