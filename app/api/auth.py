"""OAuth authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from loguru import logger

from app.db.session import get_db
from app.services.auth_service import AuthService
from app.core.config import settings
from app.core.security import create_user_token

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
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.oauth_email,
                "provider": user.oauth_provider,
                "display_name": user.display_name,
                "profile_image_url": user.profile_image_url,
            },
            "message": "Login successful"
        }
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


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
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Initiate Gmail account connection flow.
    Requests Gmail API access permissions.
    """
    try:
        from app.services.email_account_service import EmailAccountService
        
        email_account_service = EmailAccountService()
        auth_url = email_account_service.get_gmail_connect_url(user_id)
        return RedirectResponse(url=auth_url)
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
        from app.services.email_account_service import EmailAccountService
        
        user_id = int(state)  # Extract user_id from state
        email_account_service = EmailAccountService()
        email_account = await email_account_service.handle_gmail_callback(
            code, user_id, db
        )
        
        return {
            "email_account_id": email_account.id,
            "email": email_account.email_address,
            "message": "Gmail account connected successfully"
        }
    except Exception as e:
        logger.error(f"Gmail callback error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

