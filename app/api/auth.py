"""OAuth authentication endpoints."""

import urllib.parse

from loguru import logger
from typing import Optional
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse
from fastapi import APIRouter, Body, Depends, HTTPException, Request

from app.models.user import User
from app.db.session import get_db
from app.core.config import settings
from app.services.auth_service import AuthService
from app.core.id_encryption import encrypt_account_id
from app.core.security import create_user_token, get_current_user
from app.services.email_account_service import EmailAccountService
from app.db.repositories.email_account_repo import EmailAccountRepository

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/google/login")
async def google_login():
    """
    Initiate Google OAuth login flow.
    Redirects user to Google OAuth consent screen.
    """
    auth_service = AuthService()
    auth_url = auth_service.get_google_auth_url()
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Google OAuth callback endpoint.
    Exchanges authorization code for tokens and creates/updates user.
    Redirects to frontend callback page with token in URL fragment or query param.
    """
    try:
        auth_service = AuthService()
        user = await auth_service.handle_google_callback(code, db)

        # Generate JWT token
        access_token = create_user_token(
            user_id=user.id,
            email=user.oauth_email,
            provider=user.oauth_provider
        )

        # Frontend callback URL with token and user info
        # Encode user info in URL params
        callback_url = (
            f"{settings.FRONTEND_URL}/callback?"
            f"token={urllib.parse.quote(access_token)}&"
            f"user_id={user.id}&"
            f"email={urllib.parse.quote(user.oauth_email)}&"
            f"display_name={urllib.parse.quote(user.display_name or '')}&"
            f"profile_image_url={urllib.parse.quote(user.profile_image_url or '')}"
        )

        return RedirectResponse(url=callback_url)
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        # Redirect to frontend error page
        error_url = f"{settings.FRONTEND_URL}/login?error={str(e)}"
        return RedirectResponse(url=error_url)


@router.get("/naver/login")
async def naver_login():
    """
    Initiate Naver OAuth login flow.
    Redirects user to Naver OAuth consent screen.
    """
    auth_service = AuthService()
    auth_url = auth_service.get_naver_auth_url()
    return RedirectResponse(url=auth_url)


@router.get("/naver/callback")
async def naver_callback(
    code: str,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Naver OAuth callback endpoint.
    Exchanges authorization code for tokens and creates/updates user.
    """
    try:
        auth_service = AuthService()
        user = await auth_service.handle_naver_callback(code, state, db)

        return {
            "user_id": user.id,
            "email": user.oauth_email,
            "provider": user.oauth_provider,
            "message": "Login successful"
        }
    except Exception as e:
        logger.error(f"Naver OAuth callback error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/email-accounts/gmail/connect")
async def connect_gmail_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Initiate Gmail account connection flow.
    Requests Gmail API access permissions.
    Requires authentication.
    
    Returns JSON with redirect URL instead of RedirectResponse
    to allow frontend to include auth token in request.
    """
    try:
        email_account_service = EmailAccountService()
        auth_url = email_account_service.get_gmail_connect_url(current_user.id)
        return {"redirect_url": auth_url}
    except Exception as e:
        logger.error(f"Gmail connect error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/email-accounts/gmail/callback")
async def gmail_account_callback(
    code: str,
    state: str,  # Contains user_id
    db: Session = Depends(get_db)
):
    """
    Gmail account connection callback.
    Creates EmailAccount with Gmail credentials.
    """
    try:
        user_id = int(state)  # Extract user_id from state
        email_account_service = EmailAccountService()
        email_account = await email_account_service.handle_gmail_callback(
            code, user_id, db
        )

        # Redirect to frontend success page
        frontend_url = settings.FRONTEND_URL
        success_url = f"{frontend_url}/settings/accounts?success=gmail&email={urllib.parse.quote(email_account.email_address)}"
        return RedirectResponse(url=success_url)
    except Exception as e:
        logger.error(f"Gmail callback error: {e}")
        # Redirect to frontend error page
        frontend_url = settings.FRONTEND_URL
        error_url = f"{frontend_url}/settings/accounts?error={urllib.parse.quote(str(e))}"
        return RedirectResponse(url=error_url)


@router.get("/email-accounts")
async def get_email_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all email accounts for the current user.
    Requires authentication.

    Returns:
        List of email accounts with their details
    """
    try:
        account_repo = EmailAccountRepository(db)
        accounts = account_repo.get_accounts_by_user(current_user.id)

        # Convert EmailAccount models to dict (exclude sensitive credentials)
        result = []
        for account in accounts:
            result.append({
                "id": encrypt_account_id(account.id),  # 암호화된 ID
                "user_id": account.user_id,
                "email_address": account.email_address,
                "provider_type": account.provider_type.value,
                "display_name": account.display_name,
                "is_active": account.is_active,
                "last_fetch_at": account.last_fetch_at.isoformat() if account.last_fetch_at else None,
                "last_fetch_error": account.last_fetch_error,
                "fetch_interval": account.fetch_interval,
                "fetch_limit": account.fetch_limit,
                "folders_to_fetch": account.folders_to_fetch,
                "skip_folders": account.skip_folders,
                "created_at": account.created_at.isoformat() if account.created_at else None,
                "updated_at": account.updated_at.isoformat() if account.updated_at else None,
            })

        return result
    except Exception as e:
        logger.error(f"Error fetching email accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/email-accounts/naver/connect")
async def connect_naver_account(
    email: str = Body(..., description="Naver email address"),
    password: str = Body(...,
                         description="Naver email password or app password"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Connect Naver email account using IMAP credentials.
    Requires authentication.

    Body Parameters:
        email: Naver email address
        password: Naver email password or app password
    """
    try:
        email_account_service = EmailAccountService()
        email_account = await email_account_service.connect_naver_account(
            current_user.id, email, password, db
        )

        return {
            "email_account_id": encrypt_account_id(email_account.id),  # 암호화된 ID
            "email": email_account.email_address,
            "message": "Naver account connected successfully"
        }
    except ValueError as e:
        logger.error(f"Naver connect error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Naver connect error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to connect Naver account: {str(e)}")
