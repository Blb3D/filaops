"""
Accounting Pydantic Schemas

Request/response schemas for the GL accounting module.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime, date
from decimal import Decimal


# ============================================================================
# GL Account Schemas (Chart of Accounts)
# ============================================================================


class GLAccountBase(BaseModel):
    """Base fields for GL Account"""

    account_code: str = Field(..., max_length=20, description="Account code (e.g., 1000, 4000)")
    name: str = Field(..., max_length=100, description="Account name")
    account_type: Literal["asset", "liability", "equity", "revenue", "expense"] = Field(..., description="Account type")
    schedule_c_line: Optional[str] = Field(
        None, max_length=10, description="IRS Schedule C line mapping (e.g., 1, 8, 22)"
    )
    parent_id: Optional[int] = Field(None, description="Parent account ID for sub-accounts")
    description: Optional[str] = Field(None, description="Account description")


class GLAccountCreate(GLAccountBase):
    """Create a new GL Account"""

    is_system: bool = Field(default=False, description="System accounts cannot be deleted")
    active: bool = Field(default=True)


class GLAccountUpdate(BaseModel):
    """Update an existing GL Account"""

    account_code: Optional[str] = Field(None, max_length=20)
    name: Optional[str] = Field(None, max_length=100)
    account_type: Optional[Literal["asset", "liability", "equity", "revenue", "expense"]] = None
    schedule_c_line: Optional[str] = Field(None, max_length=10)
    parent_id: Optional[int] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class GLAccountResponse(GLAccountBase):
    """GL Account response"""

    id: int
    is_system: bool
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GLAccountListResponse(BaseModel):
    """GL Account list item"""

    id: int
    account_code: str
    name: str
    account_type: str
    schedule_c_line: Optional[str]
    is_system: bool
    active: bool

    model_config = {"from_attributes": True}


# ============================================================================
# GL Fiscal Period Schemas
# ============================================================================


class GLFiscalPeriodBase(BaseModel):
    """Base fields for Fiscal Period"""

    year: int = Field(..., ge=2000, le=2100, description="Fiscal year")
    period: int = Field(..., ge=1, le=12, description="Period (1-12 for months)")
    start_date: date = Field(..., description="Period start date")
    end_date: date = Field(..., description="Period end date")


class GLFiscalPeriodCreate(GLFiscalPeriodBase):
    """Create a new Fiscal Period"""

    pass


class GLFiscalPeriodResponse(GLFiscalPeriodBase):
    """Fiscal Period response"""

    id: int
    status: str
    closed_by: Optional[int]
    closed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class GLFiscalPeriodClose(BaseModel):
    """Request to close a fiscal period"""

    confirm: bool = Field(..., description="Must be true to confirm closing the period")


# ============================================================================
# GL Journal Entry Line Schemas
# ============================================================================


class GLJournalEntryLineBase(BaseModel):
    """Base fields for Journal Entry Line"""

    account_id: int = Field(..., description="GL Account ID")
    debit_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), description="Debit amount")
    credit_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), description="Credit amount")
    memo: Optional[str] = Field(None, max_length=255, description="Line memo")

    @field_validator("debit_amount", "credit_amount", mode="before")
    @classmethod
    def convert_to_decimal(cls, v):
        """Convert float/int to Decimal"""
        if v is None:
            return Decimal("0")
        return Decimal(str(v))


class GLJournalEntryLineCreate(GLJournalEntryLineBase):
    """Create a journal entry line"""

    line_order: int = Field(default=0, description="Line order for display")


class GLJournalEntryLineResponse(BaseModel):
    """Journal Entry Line response"""

    id: int
    account_id: int
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    debit_amount: Decimal
    credit_amount: Decimal
    memo: Optional[str]
    line_order: int

    model_config = {"from_attributes": True}


# ============================================================================
# GL Journal Entry Schemas
# ============================================================================


class GLJournalEntryBase(BaseModel):
    """Base fields for Journal Entry"""

    entry_date: date = Field(..., description="Entry date")
    description: str = Field(..., max_length=255, description="Entry description")
    source_type: Optional[str] = Field(
        None, max_length=50, description="Source type (sales_order, purchase_order, payment, manual)"
    )
    source_id: Optional[int] = Field(None, description="Source record ID")
    fiscal_period_id: Optional[int] = Field(None, description="Fiscal period ID")


class GLJournalEntryCreate(GLJournalEntryBase):
    """Create a new Journal Entry"""

    lines: List[GLJournalEntryLineCreate] = Field(..., min_length=2, description="Journal entry lines (minimum 2)")


class GLJournalEntryUpdate(BaseModel):
    """Update a draft Journal Entry"""

    entry_date: Optional[date] = None
    description: Optional[str] = Field(None, max_length=255)
    fiscal_period_id: Optional[int] = None
    lines: Optional[List[GLJournalEntryLineCreate]] = None


class GLJournalEntryResponse(GLJournalEntryBase):
    """Journal Entry response"""

    id: int
    entry_number: str
    status: str
    created_by: Optional[int]
    created_at: datetime
    posted_by: Optional[int]
    posted_at: Optional[datetime]
    voided_by: Optional[int]
    voided_at: Optional[datetime]
    void_reason: Optional[str]

    # Nested lines
    lines: List[GLJournalEntryLineResponse] = []

    # Computed totals
    total_debits: Decimal = Decimal("0")
    total_credits: Decimal = Decimal("0")
    is_balanced: bool = True

    model_config = {"from_attributes": True}


class GLJournalEntryListResponse(BaseModel):
    """Journal Entry list item"""

    id: int
    entry_number: str
    entry_date: date
    description: str
    source_type: Optional[str]
    status: str
    total_debits: Decimal
    total_credits: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class GLJournalEntryPost(BaseModel):
    """Request to post a journal entry"""

    confirm: bool = Field(..., description="Must be true to confirm posting")


class GLJournalEntryVoid(BaseModel):
    """Request to void a journal entry"""

    void_reason: str = Field(..., min_length=5, max_length=500, description="Reason for voiding the entry")


# ============================================================================
# Report Schemas
# ============================================================================


class TrialBalanceLineResponse(BaseModel):
    """Single line in trial balance report"""

    account_id: int
    account_code: str
    account_name: str
    account_type: str
    debit_balance: Decimal
    credit_balance: Decimal


class TrialBalanceResponse(BaseModel):
    """Trial balance report response"""

    start_date: date
    end_date: date
    lines: List[TrialBalanceLineResponse]
    total_debits: Decimal
    total_credits: Decimal
    is_balanced: bool


class ProfitLossLineResponse(BaseModel):
    """Single line in P&L report"""

    account_id: int
    account_code: str
    account_name: str
    amount: Decimal


class ProfitLossResponse(BaseModel):
    """Profit & Loss report response"""

    start_date: date
    end_date: date
    revenue_lines: List[ProfitLossLineResponse]
    expense_lines: List[ProfitLossLineResponse]
    total_revenue: Decimal
    total_expenses: Decimal
    net_income: Decimal


class ScheduleCLineResponse(BaseModel):
    """Single line in Schedule C report"""

    line_number: str
    line_description: str
    amount: Decimal
    accounts: List[str]  # Account codes that contribute to this line


class ScheduleCResponse(BaseModel):
    """Schedule C report response - THE KILLER FEATURE"""

    year: int
    lines: List[ScheduleCLineResponse]
    gross_receipts: Decimal  # Line 1
    total_expenses: Decimal
    net_profit: Decimal  # Line 31
