"""Base class for email providers."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional


class EmailMessage:
    """Standardized email message structure."""
    
    def __init__(
        self,
        message_id: str,
        subject: str,
        sender: str,
        recipient: str,
        body: str,
        html_body: Optional[str] = None,
        date: Optional[datetime] = None,
        attachments: Optional[List[dict]] = None,
        raw_mime: Optional[str] = None,
    ):
        self.message_id = message_id
        self.subject = subject
        self.sender = sender
        self.recipient = recipient
        self.body = body
        self.html_body = html_body
        self.date = date or datetime.now()
        self.attachments = attachments or []
        self.raw_mime = raw_mime


class EmailProvider(ABC):
    """Abstract base class for email providers."""
    
    def __init__(self, credentials: dict):
        """
        Initialize email provider.
        
        Args:
            credentials: Provider-specific credentials
        """
        self.credentials = credentials
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to email service."""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Close connection to email service."""
        pass
    
    @abstractmethod
    async def fetch_emails(
        self,
        limit: int = 10,
        since: Optional[datetime] = None,
        folder: str = "INBOX",
    ) -> List[EmailMessage]:
        """
        Fetch emails from the provider.
        
        Args:
            limit: Maximum number of emails to fetch
            since: Fetch emails since this datetime
            folder: Email folder to fetch from
            
        Returns:
            List of EmailMessage objects
        """
        pass
    
    @abstractmethod
    async def fetch_email_by_id(self, message_id: str) -> Optional[EmailMessage]:
        """Fetch a specific email by message ID."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of the provider (e.g., 'gmail', 'naver')."""
        pass
    
    @abstractmethod
    async def delete_email(self, message_id: str) -> bool:
        """
        Delete an email from the provider.
        
        Args:
            message_id: Provider-specific message ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass

