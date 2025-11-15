"""Gmail provider implementation using Gmail API."""

import re
import base64

from loguru import logger
from datetime import datetime
from typing import List, Optional
from dateutil.parser import parse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from email.utils import parsedate_to_datetime
from app.tasks.utils import decode_encoded_words
from app.tasks.providers.base import EmailMessage, EmailProvider


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
            # Handle both formats: direct credentials dict or nested "token" key
            creds_dict = self.credentials.copy()
            if "token" in creds_dict and isinstance(creds_dict["token"], dict):
                creds_dict = creds_dict["token"].copy()

            # Convert expiry datetime to ISO string if needed
            # Credentials.from_authorized_user_info expects string or None
            if "expiry" in creds_dict:
                expiry = creds_dict["expiry"]
                if isinstance(expiry, datetime):
                    creds_dict["expiry"] = expiry.isoformat()
                elif expiry is None:
                    creds_dict["expiry"] = None
                # If it's already a string, keep it as is

            # Create credentials object
            self.creds = Credentials.from_authorized_user_info(creds_dict)

            # Refresh token if expired
            if self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())

            self.service = build("gmail", "v1", credentials=self.creds)
            return True
        except Exception as e:
            logger.error(f"Gmail connection error: {e}")
            logger.exception(e)  # Full traceback for debugging
            self.service = None
            self.creds = None
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
            connected = await self.connect()
            if not connected:
                logger.error("Failed to connect to Gmail API")
                return []

        if not self.service:
            logger.error("Gmail service is not available")
            return []

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

            # Extract headers and decode encoded words
            subject = next(
                (h["value"] for h in headers if h["name"] == "Subject"), ""
            )
            subject = decode_encoded_words(subject)
            sender = next(
                (h["value"] for h in headers if h["name"] == "From"), ""
            )
            sender = decode_encoded_words(sender)
            recipient = next(
                (h["value"] for h in headers if h["name"] == "To"), ""
            )
            recipient = decode_encoded_words(recipient)
            date_str = next(
                (h["value"] for h in headers if h["name"] == "Date"), ""
            )

            # Parse body and attachments
            body, html_body, attachments = self._extract_body_and_attachments(
                payload, message_id)

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
                attachments=attachments,
                raw_mime=raw_mime,
            )

        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            return None

    def _extract_body_and_attachments(
        self, payload: dict, message_id: str
    ) -> tuple[str, Optional[str], List[dict]]:
        """
        Extract plain text body, HTML body, and attachments from payload.
        Handles nested multipart structures recursively.

        Returns:
            Tuple of (body, html_body, attachments)
        """
        body = ""
        html_body = None
        attachments = []

        mime_type = payload.get("mimeType", "")

        # Handle multipart messages (nested structure)
        if "parts" in payload:
            for part in payload["parts"]:
                part_mime = part.get("mimeType", "")
                part_body = part.get("body", {})

                # Check if this part is an attachment
                headers = part.get("headers", [])
                content_disposition = next(
                    (h["value"] for h in headers if h["name"].lower()
                     == "content-disposition"),
                    ""
                )

                # Check for attachment
                if "attachment" in content_disposition.lower() or (
                    part_body.get("attachmentId") and part_mime not in [
                        "text/plain", "text/html"]
                ):
                    # Extract attachment info
                    filename = self._extract_filename(
                        headers, part.get("filename", ""))
                    attachment_id = part_body.get("attachmentId")

                    if attachment_id:
                        attachments.append({
                            "attachment_id": attachment_id,
                            "filename": filename,
                            "mime_type": part_mime,
                            "size": part_body.get("size", 0),
                        })
                    continue

                # Recursively process nested multipart
                if part_mime.startswith("multipart/"):
                    nested_body, nested_html, nested_attachments = self._extract_body_and_attachments(
                        part, message_id
                    )
                    if nested_body and not body:
                        body = nested_body
                    if nested_html and not html_body:
                        html_body = nested_html
                    attachments.extend(nested_attachments)

                # Extract text/plain
                elif part_mime == "text/plain":
                    data = part_body.get("data", "")
                    if data and not body:
                        try:
                            body = base64.urlsafe_b64decode(
                                data).decode("utf-8", errors="ignore")
                        except Exception as e:
                            logger.warning(
                                f"Failed to decode text/plain body: {e}")

                # Extract text/html
                elif part_mime == "text/html":
                    data = part_body.get("data", "")
                    if data and not html_body:
                        try:
                            html_body = base64.urlsafe_b64decode(
                                data).decode("utf-8", errors="ignore")
                        except Exception as e:
                            logger.warning(
                                f"Failed to decode text/html body: {e}")

        # Handle simple (non-multipart) messages
        elif mime_type == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                try:
                    body = base64.urlsafe_b64decode(
                        data).decode("utf-8", errors="ignore")
                except Exception as e:
                    logger.warning(f"Failed to decode text/plain body: {e}")

        elif mime_type == "text/html":
            data = payload.get("body", {}).get("data", "")
            if data:
                try:
                    html_body = base64.urlsafe_b64decode(
                        data).decode("utf-8", errors="ignore")
                except Exception as e:
                    logger.warning(f"Failed to decode text/html body: {e}")

        return body, html_body, attachments

    def _extract_filename(self, headers: List[dict], default: str = "") -> str:
        """Extract filename from headers."""
        # Try Content-Disposition header first
        content_disposition = next(
            (h["value"]
             for h in headers if h["name"].lower() == "content-disposition"),
            ""
        )

        if "filename=" in content_disposition:
            match = re.search(
                r'filename[*]?=["\']?([^"\';]+)', content_disposition)
            if match:
                filename = match.group(1).strip()
                # Decode encoded words in filename
                filename = decode_encoded_words(filename)
                return filename

        # Try Content-Type header
        content_type = next(
            (h["value"]
             for h in headers if h["name"].lower() == "content-type"),
            ""
        )

        if "name=" in content_type:
            match = re.search(r'name=["\']?([^"\';]+)', content_type)
            if match:
                filename = match.group(1).strip()
                # Decode encoded words in filename
                filename = decode_encoded_words(filename)
                return filename

        return default

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse email date string."""
        try:
            return parsedate_to_datetime(date_str)
        except:
            return None

    def get_provider_name(self) -> str:
        """Return provider name."""
        return "gmail"
