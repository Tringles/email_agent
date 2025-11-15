"""Email account model for connected email accounts."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.session import Base


class EmailProviderType(str, enum.Enum):
    """Email provider types."""
    GMAIL = "gmail"
    NAVER = "naver"
    OUTLOOK = "outlook"
    # Add more as needed


class EmailAccount(Base):
    """
    Email account model for connected email accounts.
    
    Each user can have multiple email accounts (Gmail, Naver, etc.)
    Each account has its own credentials and collection settings.
    """
    
    __tablename__ = "email_accounts"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to User
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Email Account Information
    email_address = Column(String(255), nullable=False, index=True)  # Email address
    provider_type = Column(Enum(EmailProviderType), nullable=False, index=True)  # Provider type
    display_name = Column(String(255), nullable=True)  # Display name for this account
    
    # Provider-specific Credentials (encrypted in production)
    # For Gmail: OAuth tokens
    # For Naver/IMAP: username, password
    credentials = Column(JSON, nullable=False)  # Encrypted credentials dict
    
    # Collection Settings
    is_active = Column(Boolean, default=True, nullable=False)  # Enable/disable collection for this account
    last_fetch_at = Column(DateTime(timezone=True), nullable=True)  # Last successful fetch timestamp
    last_fetch_error = Column(Text, nullable=True)  # Last error message if fetch failed
    fetch_interval = Column(Integer, default=300, nullable=False)  # Fetch interval in seconds (default: 5 min)
    fetch_limit = Column(Integer, default=50, nullable=False)  # Max emails per fetch
    
    # Folder/Label Settings
    folders_to_fetch = Column(JSON, default=["INBOX"], nullable=False)  # List of folders to fetch
    skip_folders = Column(JSON, default=[], nullable=False)  # List of folders to skip
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="email_accounts")
    emails = relationship(
        "Email", 
        back_populates="email_account", 
        cascade="all, delete-orphan",
        lazy="dynamic"  # Lazy loading for better performance
    )
    
    def __repr__(self):
        return f"<EmailAccount(id={self.id}, email={self.email_address}, provider={self.provider_type})>"

