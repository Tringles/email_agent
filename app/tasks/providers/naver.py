"""Naver email provider implementation using IMAP."""

import email
import imaplib
from datetime import datetime
from email.header import decode_header
from typing import List, Optional

from loguru import logger

from app.tasks.providers.base import EmailMessage, EmailProvider


class NaverProvider(EmailProvider):
    """Naver email provider using IMAP."""
    
    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.imap = None
        self.username = credentials.get("username")
        self.password = credentials.get("password")
        self.server = credentials.get("server", "imap.naver.com")
        self.port = credentials.get("port", 993)
    
    async def connect(self) -> bool:
        """Connect to Naver IMAP server."""
        try:
            self.imap = imaplib.IMAP4_SSL(self.server, self.port)
            self.imap.login(self.username, self.password)
            return True
        except Exception as e:
            logger.error(f"Naver IMAP connection error: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from IMAP server."""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
            except:
                pass
            self.imap = None
    
    async def fetch_emails(
        self,
        limit: int = 10,
        since: Optional[datetime] = None,
        folder: str = "INBOX",
    ) -> List[EmailMessage]:
        """Fetch emails from Naver."""
        if not self.imap:
            await self.connect()
        
        try:
            self.imap.select(folder)
            
            # Build search criteria
            search_criteria = "ALL"
            if since:
                date_str = since.strftime("%d-%b-%Y")
                search_criteria = f'SINCE "{date_str}"'
            
            # Search for emails
            status, messages = self.imap.search(None, search_criteria)
            if status != "OK":
                return []
            
            email_ids = messages[0].split()
            # Get most recent emails
            email_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids
            
            email_messages = []
            for email_id in reversed(email_ids):
                email = await self.fetch_email_by_id(email_id.decode())
                if email:
                    email_messages.append(email)
            
            return email_messages
            
        except Exception as e:
            logger.error(f"Naver IMAP error: {e}")
            return []
    
    async def fetch_email_by_id(self, message_id: str) -> Optional[EmailMessage]:
        """Fetch specific email by ID."""
        if not self.imap:
            await self.connect()
        
        try:
            status, msg_data = self.imap.fetch(message_id, "(RFC822)")
            if status != "OK":
                return None
            
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Extract headers
            subject = self._decode_header(email_message["Subject"])
            sender = email_message["From"]
            recipient = email_message["To"]
            date_str = email_message["Date"]
            
            # Extract body
            body, html_body = self._extract_body(email_message)
            
            # Get raw MIME
            raw_mime = raw_email.decode("utf-8", errors="ignore")
            
            return EmailMessage(
                message_id=message_id,
                subject=subject or "",
                sender=sender or "",
                recipient=recipient or "",
                body=body,
                html_body=html_body,
                date=self._parse_date(date_str),
                raw_mime=raw_mime,
            )
            
        except Exception as e:
            logger.error(f"Naver IMAP error: {e}")
            return None
    
    def _decode_header(self, header: Optional[str]) -> str:
        """Decode email header."""
        if not header:
            return ""
        decoded_parts = decode_header(header)
        decoded_string = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_string += part.decode(encoding or "utf-8", errors="ignore")
            else:
                decoded_string += part
        return decoded_string
    
    def _extract_body(self, msg: email.message.Message) -> tuple[str, Optional[str]]:
        """Extract plain text and HTML body."""
        body = ""
        html_body = None
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if "attachment" not in content_disposition:
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    elif content_type == "text/html":
                        html_body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                if content_type == "text/plain":
                    body = payload.decode("utf-8", errors="ignore")
                elif content_type == "text/html":
                    html_body = payload.decode("utf-8", errors="ignore")
        
        return body, html_body
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse email date string."""
        if not date_str:
            return None
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except:
            return None
    
    def get_provider_name(self) -> str:
        """Return provider name."""
        return "naver"

