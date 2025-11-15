"""Email repository for database operations."""

from loguru import logger
from datetime import datetime
from sqlalchemy import and_, or_
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload

from app.models.email import Email, EmailStatus
from app.models.email_account import EmailAccount


class EmailRepository:
    """Repository for email database operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_unprocessed_emails(
        self,
        account_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Email]:
        """
        Get unprocessed emails for AI agent.

        Args:
            account_id: Filter by email account ID (optional)
            limit: Maximum number of emails to return

        Returns:
            List of unprocessed Email objects
        """
        query = self.db.query(Email).filter(
            Email.is_processed == False,
            Email.status == EmailStatus.PENDING
        )

        if account_id:
            query = query.filter(Email.email_account_id == account_id)

        return query.limit(limit).all()

    def get_emails(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        is_read: Optional[bool] = None,
        is_important: Optional[bool] = None,
        search: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> Tuple[List[Email], int]:
        """
        Get emails with pagination and filtering.

        Args:
            user_id: User ID to filter emails by user's accounts
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by email status (pending, processing, processed, failed)
            is_read: Filter by read status
            is_important: Filter by important status
            search: Search in subject, sender, recipient, body
            account_id: Filter by email account ID

        Returns:
            Tuple of (list of Email objects, total count)
        """
        # Start with base query - join with EmailAccount to filter by user_id
        # Use joinedload to eager load email_account relationship
        query = self.db.query(Email).options(
            joinedload(Email.email_account)
        ).join(
            EmailAccount, Email.email_account_id == EmailAccount.id
        ).filter(EmailAccount.user_id == user_id)

        # Filter by account_id if provided
        if account_id:
            query = query.filter(Email.email_account_id == account_id)

        # Filter by status
        if status:
            try:
                email_status = EmailStatus(status.lower())
                query = query.filter(Email.status == email_status)
            except ValueError:
                logger.warning(f"Invalid status filter: {status}")

        # Filter by is_read
        if is_read is not None:
            query = query.filter(Email.is_read == is_read)

        # Filter by is_important
        if is_important is not None:
            query = query.filter(Email.is_important == is_important)

        # Search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Email.subject.ilike(search_pattern),
                    Email.sender.ilike(search_pattern),
                    Email.recipient.ilike(search_pattern),
                    Email.body_text.ilike(search_pattern),
                )
            )

        # Get total count before pagination
        total = query.count()

        # Apply pagination and ordering (newest first)
        emails = query.order_by(Email.email_date.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return emails, total

    def get_email_by_id(self, email_id: int, user_id: Optional[int] = None) -> Optional[Email]:
        """
        Get email by ID.

        Args:
            email_id: Email ID
            user_id: Optional user ID to verify ownership

        Returns:
            Email object or None
        """
        # Use joinedload to eager load email_account relationship
        query = self.db.query(Email).options(
            joinedload(Email.email_account)
        ).filter(Email.id == email_id)

        # If user_id provided, verify ownership
        if user_id:
            query = query.join(
                EmailAccount, Email.email_account_id == EmailAccount.id
            ).filter(EmailAccount.user_id == user_id)

        return query.first()

    def create_email(self, email_data: dict) -> Email:
        """Create a new email record."""
        email = Email(**email_data)
        self.db.add(email)
        self.db.commit()
        self.db.refresh(email)
        return email

    def update_email(self, email: Email, **kwargs) -> Email:
        """Update email record."""
        for key, value in kwargs.items():
            setattr(email, key, value)
        self.db.commit()
        self.db.refresh(email)
        return email

    def mark_as_read(self, email_id: int, user_id: int, read: bool = True) -> Optional[Email]:
        """Mark email as read/unread."""
        email = self.get_email_by_id(email_id, user_id)
        if email:
            email.is_read = read
            self.db.commit()
            self.db.refresh(email)
        return email

    def mark_as_important(self, email_id: int, user_id: int, important: bool = True) -> Optional[Email]:
        """Mark email as important/unimportant."""
        email = self.get_email_by_id(email_id, user_id)
        if email:
            email.is_important = important
            self.db.commit()
            self.db.refresh(email)
        return email

    def archive_email(self, email_id: int, user_id: int, archived: bool = True) -> Optional[Email]:
        """Archive/unarchive email."""
        email = self.get_email_by_id(email_id, user_id)
        if email:
            email.is_archived = archived
            self.db.commit()
            self.db.refresh(email)
        return email

    def delete_email(self, email_id: int, user_id: int) -> bool:
        """
        Soft delete email (mark as deleted).

        Args:
            email_id: Email ID
            user_id: User ID to verify ownership

        Returns:
            True if deleted, False otherwise
        """
        email = self.get_email_by_id(email_id, user_id)
        if email:
            email.is_deleted = True
            self.db.commit()
            return True
        return False

    def mark_as_processed(self, email_id: int) -> Optional[Email]:
        """Mark email as processed by AI agent."""
        email = self.get_email_by_id(email_id)
        if email:
            email.is_processed = True
            email.status = EmailStatus.PROCESSED
            email.processed_at = datetime.now()
            self.db.commit()
            self.db.refresh(email)
        return email
