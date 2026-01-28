"""
Accounting Models (General Ledger)

Double-entry bookkeeping system with Schedule C mapping for sole proprietors.
These models support journal entries, chart of accounts, and fiscal period tracking.
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class GLAccount(Base):
    """Chart of Accounts with Schedule C mapping for tax reporting"""

    __tablename__ = "gl_accounts"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Account Identification
    account_code = Column(String(20), unique=True, nullable=False, index=True)  # "1000", "4000", "5100"
    name = Column(String(100), nullable=False)

    # Account Type
    # Values: asset, liability, equity, revenue, expense
    account_type = Column(String(20), nullable=False, index=True)

    # Schedule C Line Mapping (THE KILLER FEATURE)
    # Maps to IRS Schedule C lines: "1", "8", "22", "16a", etc.
    schedule_c_line = Column(String(10), nullable=True, index=True)

    # Hierarchical structure for sub-accounts
    parent_id = Column(Integer, ForeignKey("gl_accounts.id"), nullable=True)

    # System accounts can't be deleted (Cash, AR, AP, etc.)
    is_system = Column(Boolean, nullable=False, default=False)
    active = Column(Boolean, nullable=False, default=True, index=True)

    # Description for documentation
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    parent = relationship("GLAccount", remote_side=[id], backref="children")
    journal_lines = relationship("GLJournalEntryLine", back_populates="account")

    def __repr__(self):
        return f"<GLAccount {self.account_code}: {self.name}>"


class GLFiscalPeriod(Base):
    """Fiscal period tracking for month/year closing"""

    __tablename__ = "gl_fiscal_periods"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Period Identification
    year = Column(Integer, nullable=False, index=True)
    period = Column(Integer, nullable=False)  # 1-12 for months

    # Date Range
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Status
    # Values: open, closed
    status = Column(String(20), nullable=False, default="open", index=True)

    # Closing audit trail
    closed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    closed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    # Relationships
    closed_by_user = relationship("User", foreign_keys=[closed_by])
    journal_entries = relationship("GLJournalEntry", back_populates="fiscal_period")

    def __repr__(self):
        return f"<GLFiscalPeriod {self.year}-{self.period:02d} ({self.status})>"


class GLJournalEntry(Base):
    """Journal entry header with audit trail"""

    __tablename__ = "gl_journal_entries"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Entry Identification
    entry_number = Column(String(20), unique=True, nullable=False, index=True)  # "JE-2026-0001"
    entry_date = Column(Date, nullable=False, index=True)
    description = Column(String(255), nullable=False)

    # Source tracking (for auto-posted entries)
    # source_type: sales_order, purchase_order, payment, inventory, manual
    source_type = Column(String(50), nullable=True)
    source_id = Column(Integer, nullable=True)

    # Status workflow
    # Values: draft, posted, voided
    # draft: Can be edited, not included in reports
    # posted: Locked, included in reports
    # voided: Cancelled with reason, not included in reports
    status = Column(String(20), nullable=False, default="draft", index=True)

    # Period
    fiscal_period_id = Column(Integer, ForeignKey("gl_fiscal_periods.id"), nullable=True)

    # Audit trail - Creation
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    # Audit trail - Posting
    posted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    posted_at = Column(DateTime, nullable=True)

    # Audit trail - Voiding
    voided_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    voided_at = Column(DateTime, nullable=True)
    void_reason = Column(Text, nullable=True)

    # Relationships
    fiscal_period = relationship("GLFiscalPeriod", back_populates="journal_entries")
    lines = relationship(
        "GLJournalEntryLine",
        back_populates="journal_entry",
        cascade="all, delete-orphan",
        order_by="GLJournalEntryLine.line_order",
    )
    created_by_user = relationship("User", foreign_keys=[created_by])
    posted_by_user = relationship("User", foreign_keys=[posted_by])
    voided_by_user = relationship("User", foreign_keys=[voided_by])

    @property
    def is_balanced(self) -> bool:
        """Check if total debits equal total credits"""
        total_debits = sum(line.debit_amount or 0 for line in self.lines)
        total_credits = sum(line.credit_amount or 0 for line in self.lines)
        return total_debits == total_credits

    @property
    def total_debits(self) -> float:
        """Sum of all debit amounts"""
        return float(sum(line.debit_amount or 0 for line in self.lines))

    @property
    def total_credits(self) -> float:
        """Sum of all credit amounts"""
        return float(sum(line.credit_amount or 0 for line in self.lines))

    @property
    def is_editable(self) -> bool:
        """Check if entry can be edited (only drafts)"""
        return self.status == "draft"

    def __repr__(self):
        return f"<GLJournalEntry {self.entry_number} - {self.status}>"


class GLJournalEntryLine(Base):
    """Individual debit/credit line within a journal entry"""

    __tablename__ = "gl_journal_entry_lines"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    journal_entry_id = Column(
        Integer, ForeignKey("gl_journal_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id = Column(Integer, ForeignKey("gl_accounts.id"), nullable=False, index=True)

    # Amounts - Using Numeric(10, 2) to match existing codebase pattern
    # Either debit_amount OR credit_amount must be > 0, not both
    debit_amount = Column(Numeric(10, 2), nullable=False, default=0)
    credit_amount = Column(Numeric(10, 2), nullable=False, default=0)

    # Line details
    memo = Column(String(255), nullable=True)
    line_order = Column(Integer, nullable=False, default=0)

    # Relationships
    journal_entry = relationship("GLJournalEntry", back_populates="lines")
    account = relationship("GLAccount", back_populates="journal_lines")

    @property
    def is_debit(self) -> bool:
        """Check if this line is a debit entry"""
        return (self.debit_amount or 0) > 0

    @property
    def is_credit(self) -> bool:
        """Check if this line is a credit entry"""
        return (self.credit_amount or 0) > 0

    @property
    def amount(self) -> float:
        """Get the non-zero amount (debit or credit)"""
        if self.debit_amount and self.debit_amount > 0:
            return float(self.debit_amount)
        return float(self.credit_amount or 0)

    def __repr__(self):
        if self.is_debit:
            return f"<GLJournalEntryLine DR {self.account.account_code if self.account else '?'} ${self.debit_amount}>"
        return f"<GLJournalEntryLine CR {self.account.account_code if self.account else '?'} ${self.credit_amount}>"
