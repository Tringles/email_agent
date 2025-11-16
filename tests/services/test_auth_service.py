"""Auth Service tests."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from app.services.auth_service import AuthService
from app.models.user import User


class TestAuthService:
    """Auth Service tests."""
    
    def test_init(self):
        """Test AuthService initialization."""
        with patch('app.services.auth_service.settings') as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
            mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
            
            service = AuthService()
            
            assert service.google_client_id == "test-client-id"
            assert service.google_client_secret == "test-client-secret"
    
    @patch('app.services.auth_service.Flow')
    @patch('app.services.auth_service.settings')
    def test_get_google_auth_url(self, mock_settings, mock_flow_class):
        """Test getting Google OAuth authorization URL."""
        mock_settings.API_BASE_URL = "http://localhost:8000"
        mock_settings.API_V1_STR = "/api/v1"
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
        
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = ("http://auth.url", "state")
        mock_flow_class.from_client_config.return_value = mock_flow
        
        service = AuthService()
        url = service.get_google_auth_url()
        
        assert url == "http://auth.url"
        mock_flow.authorization_url.assert_called_once_with(
            access_type="offline",
            include_granted_scopes="false",
            prompt="consent"
        )
    
    @pytest.mark.asyncio
    @patch('app.services.auth_service.Flow')
    @patch('app.services.auth_service.build')
    @patch('app.services.auth_service.settings')
    async def test_handle_google_callback_success(self, mock_settings, mock_build, mock_flow_class, db, test_user):
        """Test handling Google OAuth callback successfully."""
        mock_settings.API_BASE_URL = "http://localhost:8000"
        mock_settings.API_V1_STR = "/api/v1"
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
        
        # Mock Flow
        mock_flow = MagicMock()
        mock_flow.fetch_token = MagicMock()
        mock_flow.credentials = MagicMock()
        mock_flow.credentials.token = "access-token"
        mock_flow.credentials.refresh_token = "refresh-token"
        mock_flow.credentials.scopes = ["openid", "https://www.googleapis.com/auth/userinfo.email"]
        mock_flow.credentials.expiry = datetime.now() + timedelta(hours=1)
        mock_flow_class.from_client_config.return_value = mock_flow
        
        # Mock Google API
        mock_service = MagicMock()
        mock_userinfo = MagicMock()
        mock_userinfo.get.return_value.execute.return_value = {
            "id": test_user.oauth_provider_user_id,  # Use existing user's ID
            "email": test_user.oauth_email,
            "name": "Test User",
            "picture": "https://example.com/pic.jpg"
        }
        mock_service.userinfo.return_value = mock_userinfo
        mock_build.return_value = mock_service
        
        service = AuthService()
        
        # Should return existing user (test_user)
        result = await service.handle_google_callback("test-code", db)
        
        assert isinstance(result, User)
        assert result.id == test_user.id
        assert result.oauth_provider == "google"
    
    @pytest.mark.asyncio
    @patch('app.services.auth_service.Flow')
    @patch('app.services.auth_service.settings')
    async def test_handle_google_callback_invalid_code(self, mock_settings, mock_flow_class, db):
        """Test handling Google OAuth callback with invalid code."""
        mock_settings.API_BASE_URL = "http://localhost:8000"
        mock_settings.API_V1_STR = "/api/v1"
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
        
        # Mock Flow to raise exception
        mock_flow = MagicMock()
        mock_flow.fetch_token.side_effect = Exception("Invalid code")
        mock_flow_class.from_client_config.return_value = mock_flow
        
        service = AuthService()
        
        with pytest.raises(Exception):
            await service.handle_google_callback("invalid-code", db)

