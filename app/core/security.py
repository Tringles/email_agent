"""Security utilities for JWT token generation and validation."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from loguru import logger

from app.core.config import settings


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Dictionary containing user data (e.g., {"sub": user_id, "email": email})
        expires_delta: Optional expiration time delta. Defaults to JWT_ACCESS_TOKEN_EXPIRE_MINUTES.
    
    Returns:
        Encoded JWT token string
    """
    if not settings.JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY is not set in environment variables")
    
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate JWT access token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload if valid, None otherwise
    """
    if not settings.JWT_SECRET_KEY:
        logger.warning("JWT_SECRET_KEY is not set, cannot decode token")
        return None
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        return None


def create_user_token(user_id: int, email: str, provider: str) -> str:
    """
    Create JWT token for authenticated user.
    
    Args:
        user_id: User ID
        email: User email
        provider: OAuth provider (e.g., 'google')
    
    Returns:
        JWT token string
    """
    data = {
        "sub": str(user_id),  # Subject (user ID)
        "email": email,
        "provider": provider,
    }
    return create_access_token(data)
