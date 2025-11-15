"""User model for SSO (OAuth) authentication."""

from typing import Optional
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text

from app.db.session import Base


class User(Base):
    """
    User model for SSO (OAuth) authentication.

    Supports multiple OAuth providers (Google, Naver, etc.)
    Each user can have multiple email accounts connected.
    """

    __tablename__ = "users"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # OAuth Provider Information
    # 'google', 'naver', etc.
    oauth_provider = Column(String(50), nullable=False, index=True)
    oauth_provider_user_id = Column(
        String(255), nullable=False, index=True)  # Provider's user ID
    oauth_email = Column(String(255), nullable=False,
                         index=True)  # Email from OAuth provider

    # OAuth Tokens (encrypted in production)
    oauth_access_token = Column(Text, nullable=True)  # Encrypted access token
    oauth_refresh_token = Column(
        Text, nullable=True)  # Encrypted refresh token
    oauth_token_expires_at = Column(
        DateTime(timezone=True), nullable=True)  # Token expiration
    # ID token (for some providers)
    oauth_id_token = Column(Text, nullable=True)

    # User Profile Information (from OAuth provider)
    display_name = Column(String(255), nullable=True)  # User's display name
    profile_image_url = Column(String(512), nullable=True)  # Profile image URL
    # User's locale (e.g., 'ko', 'en')
    locale = Column(String(10), nullable=True)

    # User Settings
    # Account active status
    is_active = Column(Boolean, default=True, nullable=False)
    is_email_collection_enabled = Column(
        Boolean, default=True, nullable=False)  # Enable/disable email collection
    # Collection interval in seconds (default: 5 min)
    email_collection_interval = Column(Integer, default=300, nullable=False)

    # Metadata
    last_login_at = Column(DateTime(timezone=True),
                           nullable=True)  # Last login timestamp
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(
    ), onupdate=func.now(), nullable=False)

    # Additional OAuth data (provider-specific)
    # Store additional provider-specific data
    oauth_metadata = Column(JSON, nullable=True)

    # Relationships
    email_accounts = relationship(
        "EmailAccount",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"  # Lazy loading for better performance
    )

    def __repr__(self):
        return f"<User(id={self.id}, oauth_provider={self.oauth_provider}, oauth_email={self.oauth_email})>"

    @property
    def is_token_expired(self) -> bool:
        """Check if OAuth token is expired."""
        if not self.oauth_token_expires_at:
            return True
        return datetime.now(timezone=self.oauth_token_expires_at.tzinfo) > self.oauth_token_expires_at
