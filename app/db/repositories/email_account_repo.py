"""Email account repository for database operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.models.email_account import EmailAccount, EmailProviderType
from app.models.user import User


class EmailAccountRepository:
    """Repository for email account database operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_account_by_id(self, account_id: int) -> Optional[EmailAccount]:
        """Get email account by ID."""
        return self.db.query(EmailAccount).filter(EmailAccount.id == account_id).first()
    
    def get_active_accounts(self, user_id: Optional[int] = None) -> List[EmailAccount]:
        """
        Get all active email accounts.
        
        Args:
            user_id: Filter by user ID (optional)
            
        Returns:
            List of active EmailAccount objects
        """
        query = self.db.query(EmailAccount).filter(
            EmailAccount.is_active == True
        )
        
        if user_id:
            query = query.filter(EmailAccount.user_id == user_id)
        
        return query.all()
    
    def get_accounts_by_provider(
        self, 
        provider_type: EmailProviderType,
        user_id: Optional[int] = None
    ) -> List[EmailAccount]:
        """
        Get email accounts by provider type.
        
        Args:
            provider_type: Email provider type
            user_id: Filter by user ID (optional)
            
        Returns:
            List of EmailAccount objects
        """
        query = self.db.query(EmailAccount).filter(
            EmailAccount.provider_type == provider_type,
            EmailAccount.is_active == True
        )
        
        if user_id:
            query = query.filter(EmailAccount.user_id == user_id)
        
        return query.all()
    
    def update_last_fetch(
        self, 
        account_id: int, 
        success: bool = True, 
        error_message: Optional[str] = None
    ) -> Optional[EmailAccount]:
        """
        Update last fetch timestamp and error message.
        
        Args:
            account_id: Email account ID
            success: Whether fetch was successful
            error_message: Error message if fetch failed
            
        Returns:
            Updated EmailAccount or None
        """
        account = self.get_account_by_id(account_id)
        if account:
            from datetime import datetime
            if success:
                account.last_fetch_at = datetime.now()
                account.last_fetch_error = None
            else:
                account.last_fetch_error = error_message
            
            self.db.commit()
            self.db.refresh(account)
        
        return account

