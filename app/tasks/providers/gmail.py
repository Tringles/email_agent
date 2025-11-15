"""Gmail provider implementation using Gmail API."""

from typing import List, Optional
from datetime import datetime
from loguru import logger

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.tasks.providers.base import EmailProvider, EmailMessage


class GmailProvider(EmailProvider):
    """Gmail provider using Gmail API."""
    
    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.service = None
        self.creds: Optional[Credentials] = None
    
    async def connect(self) -> bool:
        """Connect to Gmail API."""
        try:
            # OAuth2 credentials from credentials dict
            self.creds = Credentials.from_authorized_user_info(
                self.credentials.get("token", {})
            )
            self.service = build("gmail", "v1", credentials=self.creds)
            return True
        except Exception as e:
            logger.error(f"Gmail connection error: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Gmail API."""
        self.service = None
        self.creds = None
    
    async def fetch_emails(
        self,
        limit: int = 10,
        since: Optional[datetime] = None,
        folder: str = "INBOX",
    ) -> List[EmailMessage]:
        """Fetch emails from Gmail."""
        if not self.service:
            await self.connect()
        
        try:
            # Build query
            query = ""
            if since:
                query = f"after:{int(since.timestamp())}"
            
            # Fetch message list
            results = (
                self.service.users()
                .messages()
                .list(userId="me", maxResults=limit, q=query)
                .execute()
            )
            
            messages = results.get("messages", [])
            email_messages = []
            
            for msg in messages:
                email = await self.fetch_email_by_id(msg["id"])
                if email:
                    email_messages.append(email)
            
            return email_messages
            
        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            return []
    
    async def fetch_email_by_id(self, message_id: str) -> Optional[EmailMessage]:
        """Fetch specific email by ID."""
        if not self.service:
            await self.connect()
        
        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            
            payload = message.get("payload", {})
            headers = payload.get("headers", [])
            
            # Extract headers
            subject = next(
                (h["value"] for h in headers if h["name"] == "Subject"), ""
            )
            sender = next(
                (h["value"] for h in headers if h["name"] == "From"), ""
            )
            recipient = next(
                (h["value"] for h in headers if h["name"] == "To"), ""
            )
            date_str = next(
                (h["value"] for h in headers if h["name"] == "Date"), ""
            )
            
            # Parse body
            body = self._extract_body(payload)
            html_body = self._extract_html_body(payload)
            
            # Get raw MIME
            raw_message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="raw")
                .execute()
            )
            raw_mime = raw_message.get("raw", "")
            
            return EmailMessage(
                message_id=message_id,
                subject=subject,
                sender=sender,
                recipient=recipient,
                body=body,
                html_body=html_body,
                date=self._parse_date(date_str),
                raw_mime=raw_mime,
            )
            
        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            return None
    
    def _extract_body(self, payload: dict) -> str:
        """Extract plain text body from payload."""
        body = ""
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    import base64
                    body = base64.urlsafe_b64decode(data).decode("utf-8")
                    break
        elif payload.get("mimeType") == "text/plain":
            data = payload["body"].get("data", "")
            import base64
            body = base64.urlsafe_b64decode(data).decode("utf-8")
        return body
    
    def _extract_html_body(self, payload: dict) -> Optional[str]:
        """Extract HTML body from payload."""
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/html":
                    data = part["body"].get("data", "")
                    import base64
                    return base64.urlsafe_b64decode(data).decode("utf-8")
        elif payload.get("mimeType") == "text/html":
            data = payload["body"].get("data", "")
            import base64
            return base64.urlsafe_b64decode(data).decode("utf-8")
        return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse email date string."""
        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(date_str)
        except:
            return None
    
    def get_provider_name(self) -> str:
        """Return provider name."""
        return "gmail"

