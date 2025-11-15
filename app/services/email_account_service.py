"""Email account service for connecting email accounts."""

from loguru import logger
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.models.user import User
from app.core.config import settings
from app.tasks.providers.naver import NaverProvider
from app.models.email_account import EmailAccount, EmailProviderType


class EmailAccountService:
    """Service for managing email account connections."""

    # Gmail API scopes for email access
    # gmail.readonly: Full read access including search queries
    # gmail.metadata: Metadata only (doesn't support query parameter)
    GMAIL_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
    ]

    def __init__(self):
        self.google_client_id = settings.GOOGLE_CLIENT_ID
        self.google_client_secret = settings.GOOGLE_CLIENT_SECRET

    def get_gmail_connect_url(self, user_id: int) -> str:
        """
        Generate Gmail OAuth URL for connecting email account.

        Args:
            user_id: User ID to associate the email account with

        Returns:
            Gmail OAuth authorization URL
        """
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.google_client_id,
                    "client_secret": self.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [
                        f"{settings.API_BASE_URL}{settings.API_V1_STR}/auth/email-accounts/gmail/callback"
                    ],
                }
            },
            scopes=self.GMAIL_SCOPES,
        )
        flow.redirect_uri = (
            f"{settings.API_BASE_URL}{settings.API_V1_STR}/auth/email-accounts/gmail/callback"
        )

        # Store user_id in state for callback
        # include_granted_scopes="false" to avoid scope mismatch errors
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            # Only request Gmail scopes, not previous userinfo scopes
            include_granted_scopes="false",
            prompt="consent",
            state=str(user_id),  # Pass user_id through state
        )

        return authorization_url

    async def handle_gmail_callback(
        self, code: str, user_id: int, db: Session
    ) -> EmailAccount:
        """
        Handle Gmail account connection callback.
        Create EmailAccount with Gmail credentials.

        Args:
            code: Authorization code from OAuth callback
            user_id: User ID to associate the account with
            db: Database session

        Returns:
            Created EmailAccount
        """
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.google_client_id,
                    "client_secret": self.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [
                        f"{settings.API_BASE_URL}{settings.API_V1_STR}/auth/email-accounts/gmail/callback"
                    ],
                }
            },
            scopes=self.GMAIL_SCOPES,
        )
        flow.redirect_uri = (
            f"{settings.API_BASE_URL}{settings.API_V1_STR}/auth/email-accounts/gmail/callback"
        )

        # Exchange code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Verify that we have the required Gmail scopes
        granted_scopes = credentials.scopes if credentials.scopes else []
        required_scopes = set(self.GMAIL_SCOPES)
        granted_scopes_set = set(granted_scopes)

        if not required_scopes.issubset(granted_scopes_set):
            missing_scopes = required_scopes - granted_scopes_set
            raise ValueError(
                f"Missing required Gmail scopes: {missing_scopes}. "
                f"Granted scopes: {granted_scopes}"
            )

        # Get Gmail account info
        service = build("gmail", "v1", credentials=credentials)
        profile = service.users().getProfile(userId="me").execute()
        email_address = profile["emailAddress"]

        # Check if account already exists
        existing_account = db.query(EmailAccount).filter(
            EmailAccount.user_id == user_id,
            EmailAccount.email_address == email_address,
            EmailAccount.provider_type == EmailProviderType.GMAIL,
        ).first()

        if existing_account:
            # Update existing account credentials
            existing_account.credentials = {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes,
                "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
            }
            db.commit()
            db.refresh(existing_account)
            logger.info(f"Updated Gmail account: {email_address}")
            return existing_account

        # Create new email account
        email_account = EmailAccount(
            user_id=user_id,
            email_address=email_address,
            provider_type=EmailProviderType.GMAIL,
            display_name=email_address,
            credentials={
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes,
                "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
            },
            is_active=True,
        )

        db.add(email_account)
        db.commit()
        db.refresh(email_account)

        logger.info(
            f"Connected Gmail account: {email_address} for user {user_id}")
        return email_account

    async def connect_naver_account(
        self, user_id: int, email: str, password: str, db: Session
    ) -> EmailAccount:
        """
        Connect Naver email account using IMAP credentials.

        Args:
            user_id: User ID to associate the account with
            email: Naver email address
            password: Naver email password (or app password)
            db: Database session

        Returns:
            Created EmailAccount
        """
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Validate email format (basic check)
        # Naver domain is naver.com
        if "@naver.com" not in email.lower():
            raise ValueError("Invalid Naver email address. Must be @naver.com")

        # Test IMAP connection to verify credentials
        try:
            test_provider = NaverProvider({
                "username": email,
                "password": password,
                "server": "imap.naver.com",  # INCOMING SERVER
                "port": 993,  # SSL/TLS
            })

            # Try to connect
            connected = await test_provider.connect()
            if not connected:
                raise ValueError(
                    "Failed to connect to Naver IMAP server. Please check your credentials.")

            # Get email address from connection (verify it works)
            await test_provider.disconnect()
        except Exception as e:
            logger.error(f"Naver IMAP connection test failed: {e}")
            raise ValueError(f"Failed to verify Naver credentials: {str(e)}")

        # Check if account already exists
        existing_account = db.query(EmailAccount).filter(
            EmailAccount.user_id == user_id,
            EmailAccount.email_address == email.lower(),
            EmailAccount.provider_type == EmailProviderType.NAVER,
        ).first()

        if existing_account:
            # Update existing account credentials
            existing_account.credentials = {
                "username": email.lower(),
                "password": password,  # In production, encrypt this
                # INCOMING SERVER: imap.naver.com:993 (SSL/TLS)
                "server": "imap.naver.com",
                "port": 993,
                "smtp_server": "smtp.naver.com",  # OUTGOING SERVER: smtp.naver.com:587
                "smtp_port": 587,
            }
            existing_account.is_active = True
            db.commit()
            db.refresh(existing_account)
            logger.info(f"Updated Naver account: {email}")
            return existing_account

        # Create new email account
        email_account = EmailAccount(
            user_id=user_id,
            email_address=email.lower(),
            provider_type=EmailProviderType.NAVER,
            display_name=email.lower(),
            credentials={
                "username": email.lower(),
                "password": password,  # In production, encrypt this
                # INCOMING SERVER: imap.naver.com:993 (SSL/TLS)
                "server": "imap.naver.com",
                "port": 993,
                "smtp_server": "smtp.naver.com",  # OUTGOING SERVER: smtp.naver.com:587
                "smtp_port": 587,
            },
            is_active=True,
        )

        db.add(email_account)
        db.commit()
        db.refresh(email_account)

        logger.info(
            f"Connected Naver account: {email} for user {user_id}")
        return email_account
