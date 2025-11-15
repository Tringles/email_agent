"""OAuth authentication service."""

import httpx

from loguru import logger
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from app.models.user import User
from app.core.config import settings


class AuthService:
    """Service for handling OAuth authentication."""

    # Google OAuth settings
    GOOGLE_SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    # Naver OAuth settings
    NAVER_AUTH_URL = "https://nid.naver.com/oauth2.0/authorize"
    NAVER_TOKEN_URL = "https://nid.naver.com/oauth2.0/token"
    NAVER_USERINFO_URL = "https://openapi.naver.com/v1/nid/me"

    def __init__(self):
        self.google_client_id = settings.GOOGLE_CLIENT_ID
        self.google_client_secret = settings.GOOGLE_CLIENT_SECRET
        # TODO: Add Naver client credentials to settings
        # self.naver_client_id = settings.NAVER_CLIENT_ID
        # self.naver_client_secret = settings.NAVER_CLIENT_SECRET

    def get_google_auth_url(self) -> str:
        """Generate Google OAuth authorization URL."""
        redirect_uri = f"{settings.API_BASE_URL}{settings.API_V1_STR}/auth/google/callback"

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.google_client_id,
                    "client_secret": self.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=self.GOOGLE_SCOPES,
        )
        flow.redirect_uri = redirect_uri

        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            # Don't include previously granted scopes to avoid scope mismatch
            include_granted_scopes="false",
            prompt="consent",  # Force consent to get refresh token
        )

        return authorization_url

    async def handle_google_callback(
        self, code: str, db: Session
    ) -> User:
        """
        Handle Google OAuth callback.
        Exchange code for tokens and create/update user.
        """
        redirect_uri = f"{settings.API_BASE_URL}{settings.API_V1_STR}/auth/google/callback"

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.google_client_id,
                    "client_secret": self.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=self.GOOGLE_SCOPES,
        )
        flow.redirect_uri = redirect_uri

        try:
            # Exchange code for tokens
            flow.fetch_token(code=code)
        except Exception as e:
            # If scope mismatch error, try to fetch token without strict scope validation
            error_msg = str(e)
            if "Scope has changed" in error_msg or "scope" in error_msg.lower():
                logger.warning(
                    f"Scope mismatch detected, attempting to fetch token with granted scopes: {e}")
                # Recreate flow with empty scopes to accept whatever Google grants
                flow = Flow.from_client_config(
                    {
                        "web": {
                            "client_id": self.google_client_id,
                            "client_secret": self.google_client_secret,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "redirect_uris": [redirect_uri],
                        }
                    },
                    scopes=[],  # Empty scopes to accept granted scopes
                )
                flow.redirect_uri = redirect_uri
                flow.fetch_token(code=code)
            else:
                raise

        credentials = flow.credentials

        # Verify we have at least the required scopes for user info
        granted_scopes = credentials.scopes if credentials.scopes else []
        required_scopes = set(self.GOOGLE_SCOPES)
        granted_scopes_set = set(granted_scopes)

        # Check if we have the minimum required scopes (userinfo.email and userinfo.profile)
        has_minimum_scopes = (
            "https://www.googleapis.com/auth/userinfo.email" in granted_scopes_set or
            "openid" in granted_scopes_set
        )

        if not has_minimum_scopes:
            logger.warning(
                f"Granted scopes {granted_scopes} do not include required userinfo scopes. "
                f"Required: {required_scopes}"
            )
            # Still proceed if we have openid scope (which includes basic user info)
            if "openid" not in granted_scopes_set:
                raise ValueError(
                    f"Insufficient scopes granted. Required: {required_scopes}, "
                    f"Granted: {granted_scopes}"
                )

        # Get user info
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()

        # Create or update user
        user = db.query(User).filter(
            User.oauth_provider == "google",
            User.oauth_provider_user_id == user_info["id"]
        ).first()

        if user:
            # Update existing user
            user.oauth_access_token = credentials.token
            user.oauth_refresh_token = credentials.refresh_token
            user.oauth_token_expires_at = credentials.expiry
            user.oauth_email = user_info["email"]
            user.display_name = user_info.get("name")
            user.profile_image_url = user_info.get("picture")
            user.locale = user_info.get("locale")
            user.last_login_at = datetime.now()
        else:
            # Create new user
            user = User(
                oauth_provider="google",
                oauth_provider_user_id=user_info["id"],
                oauth_email=user_info["email"],
                oauth_access_token=credentials.token,
                oauth_refresh_token=credentials.refresh_token,
                oauth_token_expires_at=credentials.expiry,
                display_name=user_info.get("name"),
                profile_image_url=user_info.get("picture"),
                locale=user_info.get("locale"),
                last_login_at=datetime.now(),
            )
            db.add(user)

        db.commit()
        db.refresh(user)

        logger.info(f"User logged in: {user.id} ({user.oauth_email})")
        return user

    def get_naver_auth_url(self) -> str:
        """Generate Naver OAuth authorization URL."""
        # TODO: Implement Naver OAuth URL generation
        # params = {
        #     "response_type": "code",
        #     "client_id": self.naver_client_id,
        #     "redirect_uri": f"{settings.API_V1_STR}/auth/naver/callback",
        #     "state": "random_state_string",
        # }
        # return f"{self.NAVER_AUTH_URL}?{urlencode(params)}"
        raise NotImplementedError("Naver OAuth not yet implemented")

    async def handle_naver_callback(
        self, code: str, state: str, db: Session
    ) -> User:
        """Handle Naver OAuth callback."""
        # TODO: Implement Naver OAuth callback handling
        raise NotImplementedError("Naver OAuth not yet implemented")
