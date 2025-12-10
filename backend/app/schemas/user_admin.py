"""
Admin User Management Schemas

For creating and managing admin/operator users (not customers).
Customers are managed separately via /admin/customers.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class AdminUserCreate(BaseModel):
    """Create a new admin or operator user"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Temporary password - user should change on first login")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    account_type: str = Field(..., pattern="^(admin|operator)$", description="User role: 'admin' or 'operator'")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "operator@example.com",
                "password": "TempPass123!",
                "first_name": "Jane",
                "last_name": "Smith",
                "account_type": "operator"
            }
        }


class AdminUserUpdate(BaseModel):
    """Update an admin or operator user"""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    account_type: Optional[str] = Field(None, pattern="^(admin|operator)$")
    status: Optional[str] = Field(None, pattern="^(active|inactive|suspended)$")
    
    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "account_type": "admin",
                "status": "active"
            }
        }


class AdminUserResetPassword(BaseModel):
    """Reset password for an admin/operator user"""
    new_password: str = Field(..., min_length=8)


class AdminUserResponse(BaseModel):
    """Response model for admin/operator user"""
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    account_type: str
    status: str
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    """Response model for user list"""
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    account_type: str
    status: str
    last_login_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
