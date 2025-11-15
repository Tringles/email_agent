"""Email model for storing email metadata."""

import enum
from datetime import datetime
from sqlalchemy.sql import func
from typing import List, Optional
from sqlalchemy.orm import relationship
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, Text

from app.db.session import Base


class EmailStatus(str, enum.Enum):
    """Email processing status."""
    PENDING = "pending"  # Not yet processed by AI agent
    PROCESSING = "processing"  # Currently being processed
    PROCESSED = "processed"  # Processed by AI agent
    FAILED = "failed"  # Processing failed


class ImportanceLevel(str, enum.Enum):
    """Email importance level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Email(Base):
    """
    Email model for storing all email metadata.

    Stores metadata for emails collected from various providers.
    Raw MIME is stored in object storage (S3/MinIO).
    """

    __tablename__ = "emails"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to EmailAccount
    email_account_id = Column(
        Integer,
        ForeignKey("email_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Provider-specific identifiers
    provider_message_id = Column(
        String(512), nullable=False, index=True)  # Provider's message ID
    provider_thread_id = Column(
        String(512), nullable=True, index=True)  # Thread/conversation ID

    # Basic email information
    subject = Column(String(512), nullable=True, index=True)
    sender = Column(String(255), nullable=False, index=True)  # From address
    sender_name = Column(String(255), nullable=True)  # Display name
    recipient = Column(String(255), nullable=False, index=True)  # To address
    recipient_name = Column(String(255), nullable=True)  # Display name
    cc = Column(JSON, nullable=True)  # List of CC addresses
    bcc = Column(JSON, nullable=True)  # List of BCC addresses
    reply_to = Column(String(255), nullable=True)

    # Email content
    body_text = Column(Text, nullable=True)  # Plain text body
    body_html = Column(Text, nullable=True)  # HTML body
    preview = Column(String(500), nullable=True)  # Email preview/snippet

    # Email metadata
    email_date = Column(DateTime(timezone=True),
                        nullable=False, index=True)  # Original email date
    received_date = Column(DateTime(timezone=True),
                           nullable=True)  # Received date
    # Folder/label (INBOX, SENT, etc.)
    folder = Column(String(100), nullable=True, index=True)
    labels = Column(JSON, nullable=True)  # List of labels/tags

    # Attachments
    attachments = Column(JSON, nullable=True)  # List of attachment metadata
    attachment_count = Column(Integer, default=0, nullable=False)
    has_attachments = Column(Boolean, default=False, nullable=False)

    # Storage information
    # S3/MinIO path for raw MIME
    raw_mime_storage_path = Column(String(512), nullable=True)
    raw_mime_size = Column(Integer, nullable=True)  # Size in bytes

    # AI Processing status
    status = Column(
        Enum(EmailStatus),
        default=EmailStatus.PENDING,
        nullable=False,
        index=True
    )
    is_processed = Column(Boolean, default=False, nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # AI Processing results
    summary = Column(Text, nullable=True)  # AI-generated summary
    # Importance score (0.0 - 1.0)
    importance_score = Column(Float, nullable=True)
    importance_level = Column(
        Enum(ImportanceLevel),
        nullable=True,
        index=True
    )
    # Classification results (category, tags, etc.)
    classification = Column(JSON, nullable=True)
    # Sentiment analysis (positive, negative, neutral)
    sentiment = Column(String(50), nullable=True)

    # Vector DB
    vector_db_id = Column(String(255), nullable=True,
                          index=True)  # Vector DB document ID
    # Embedding model used
    embedding_model = Column(String(100), nullable=True)

    # User actions
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    is_starred = Column(Boolean, default=False, nullable=False, index=True)
    is_important = Column(Boolean, default=False, nullable=False, index=True)

    # Rule engine actions
    rule_applied = Column(String(100), nullable=True)  # Applied rule name
    # Auto action taken (delete, archive, tag, etc.)
    auto_action = Column(String(50), nullable=True)

    # Additional metadata
    headers = Column(JSON, nullable=True)  # Full email headers
    # Provider-specific metadata
    provider_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(
    ), onupdate=func.now(), nullable=False)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(
    ), nullable=False)  # When email was fetched

    # Relationships
    email_account = relationship("EmailAccount", back_populates="emails")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_email_account_status', 'email_account_id', 'status'),
        Index('idx_email_account_unprocessed',
              'email_account_id', 'is_processed'),
        Index('idx_email_date_status', 'email_date', 'status'),
        Index('idx_provider_message', 'email_account_id',
              'provider_message_id', unique=True),
    )

    def __repr__(self):
        return f"<Email(id={self.id}, subject={self.subject[:50]}, sender={self.sender})>"

    @property
    def is_unprocessed(self) -> bool:
        """Check if email is unprocessed by AI agent."""
        return not self.is_processed and self.status == EmailStatus.PENDING
