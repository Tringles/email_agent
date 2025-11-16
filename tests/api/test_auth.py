"""Authentication API tests."""

import pytest

from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestAuthAPI:
    """Authentication endpoint tests."""
    
    def test_google_login_redirect(self, client: TestClient, mock_auth_service):
        """Test Google OAuth login redirect."""
        response = client.get("/api/v1/auth/google/login", follow_redirects=False)
        
        assert response.status_code == 307  # Redirect
        assert "accounts.google.com" in response.headers.get("location", "")
    
    @patch('app.api.auth.AuthService')
    @patch('app.api.auth.create_user_token')
    def test_google_callback_success(
        self,
        mock_create_token,
        mock_auth_service_class,
        client: TestClient,
        db,
        test_user
    ):
        """Test successful Google OAuth callback."""
        from unittest.mock import AsyncMock
        
        # Setup mocks
        mock_service = MagicMock()
        mock_auth_service_class.return_value = mock_service
        # handle_google_callback is async, use AsyncMock
        mock_service.handle_google_callback = AsyncMock(return_value=test_user)
        mock_create_token.return_value = "test-token-123"
        
        response = client.get(
            "/api/v1/auth/google/callback?code=test-code-123",
            follow_redirects=False
        )
        
        assert response.status_code == 307  # Redirect
        location = response.headers.get("location", "")
        assert "token=" in location
        assert "user_id=" in location
    
    @patch('app.api.auth.AuthService')
    def test_google_callback_error(
        self,
        mock_auth_service_class,
        client: TestClient
    ):
        """Test Google OAuth callback with error."""
        from unittest.mock import AsyncMock
        
        # Setup mocks
        mock_service = MagicMock()
        mock_auth_service_class.return_value = mock_service
        # handle_google_callback is async, use AsyncMock
        mock_service.handle_google_callback = AsyncMock(side_effect=Exception("OAuth error"))
        
        response = client.get(
            "/api/v1/auth/google/callback?code=invalid-code",
            follow_redirects=False
        )
        
        assert response.status_code == 307  # Redirect to error page
        location = response.headers.get("location", "")
        assert "error" in location.lower() or "login" in location.lower()
    
    def test_naver_login_redirect(self, client: TestClient):
        """Test Naver OAuth login redirect."""
        with patch('app.api.auth.AuthService') as mock_auth_service_class:
            mock_service = MagicMock()
            mock_auth_service_class.return_value = mock_service
            mock_service.get_naver_auth_url = MagicMock(return_value="https://nid.naver.com/oauth")
            
            response = client.get("/api/v1/auth/naver/login", follow_redirects=False)
            
            assert response.status_code == 307  # Redirect
            assert "naver.com" in response.headers.get("location", "")

