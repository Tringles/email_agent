"""Email repository for database operations."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from loguru import logger

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
    
    def get_email_by_id(self, email_id: int) -> Optional[Email]:
        """Get email by ID."""
        return self.db.query(Email).filter(Email.id == email_id).first()
    
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

