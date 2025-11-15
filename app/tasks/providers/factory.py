"""Factory for creating email providers."""

from typing import Optional

from app.tasks.providers.base import EmailProvider
from app.tasks.providers.gmail import GmailProvider
from app.tasks.providers.naver import NaverProvider


def get_email_provider(
    provider_type: str, credentials: dict
) -> Optional[EmailProvider]:
    """
    Factory function to create email provider instances.
    
    Args:
        provider_type: Type of provider ('gmail', 'naver', etc.)
        credentials: Provider-specific credentials
        
    Returns:
        EmailProvider instance or None if provider type is not supported
    """
    providers = {
        "gmail": GmailProvider,
        "naver": NaverProvider,
        # Add more providers here as needed
        # "outlook": OutlookProvider,
    }
    
    provider_class = providers.get(provider_type.lower())
    if not provider_class:
        raise ValueError(f"Unsupported email provider: {provider_type}")
    
    return provider_class(credentials)

