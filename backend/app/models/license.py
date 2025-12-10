"""
License model for Pro/Enterprise tier management
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class License(Base):
    """
    License model for storing user licenses
    
    Tracks Pro/Enterprise license keys and their status
    """
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    
    # User reference
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # License details
    license_key_hash = Column(String(255), nullable=False, index=True)  # Hashed license key
    tier = Column(String(20), nullable=False)  # 'pro' or 'enterprise'
    
    # Status
    status = Column(String(20), default='active', nullable=False)  # active, expired, revoked
    activated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="licenses")
    
    def __repr__(self):
        return f"<License(user_id={self.user_id}, tier={self.tier}, status={self.status})>"
    
    @property
    def is_active(self) -> bool:
        """Check if license is currently active"""
        if self.status != 'active':
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True

