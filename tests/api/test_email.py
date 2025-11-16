"""Email API tests."""

import pytest

from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestEmailAPI:
    """Email endpoint tests."""
    
    def test_get_emails_unauthorized(self, client: TestClient):
        """Test getting emails without authentication."""
        response = client.get("/api/v1/email")
        
        # FastAPI HTTPBearer returns 403 when no token is provided
        assert response.status_code in [401, 403]  # Unauthorized
    
    def test_get_emails_success(
        self,
        authenticated_client: TestClient,
        test_user,
        test_email_account,
        test_email
    ):
        """Test getting emails with authentication."""
        response = authenticated_client.get("/api/v1/email")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert isinstance(data["items"], list)
    
    def test_get_emails_with_pagination(
        self,
        authenticated_client: TestClient,
        test_user,
        test_email_account,
        test_email
    ):
        """Test email pagination."""
        response = authenticated_client.get("/api/v1/email?page=1&page_size=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
    
    def test_get_emails_with_filters(
        self,
        authenticated_client: TestClient,
        test_user,
        test_email_account,
        test_email
    ):
        """Test email filtering."""
        # Test is_read filter
        response = authenticated_client.get("/api/v1/email?is_read=false")
        assert response.status_code == 200
        
        # Test is_deleted filter
        response = authenticated_client.get("/api/v1/email?is_deleted=false")
        assert response.status_code == 200
        
        # Test search
        response = authenticated_client.get("/api/v1/email?search=test")
        assert response.status_code == 200
    
    def test_get_email_by_id_unauthorized(self, client: TestClient):
        """Test getting email by ID without authentication."""
        response = client.get("/api/v1/email/test-id")
        
        # FastAPI HTTPBearer returns 403 when no token is provided
        assert response.status_code in [401, 403]
    
    def test_get_email_by_id_success(
        self,
        authenticated_client: TestClient,
        test_user,
        test_email_account,
        test_email
    ):
        """Test getting email by ID."""
        from app.core.id_encryption import encrypt_email_id
        
        encrypted_id = encrypt_email_id(test_email.id)
        response = authenticated_client.get(f"/api/v1/email/{encrypted_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None
        assert data["subject"] == test_email.subject
    
    def test_get_email_by_id_not_found(
        self,
        authenticated_client: TestClient,
        test_user
    ):
        """Test getting non-existent email."""
        from app.core.id_encryption import encrypt_email_id
        
        # Encrypt a non-existent ID
        encrypted_id = encrypt_email_id(99999)
        response = authenticated_client.get(f"/api/v1/email/{encrypted_id}")
        
        assert response.status_code == 404
    
    def test_mark_email_important(
        self,
        authenticated_client: TestClient,
        test_user,
        test_email_account,
        test_email
    ):
        """Test marking email as important."""
        from app.core.id_encryption import encrypt_email_id
        
        encrypted_id = encrypt_email_id(test_email.id)
        response = authenticated_client.patch(f"/api/v1/email/{encrypted_id}/important?important=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_important"] is True
    
    def test_archive_email(
        self,
        authenticated_client: TestClient,
        test_user,
        test_email_account,
        test_email
    ):
        """Test archiving email."""
        from app.core.id_encryption import encrypt_email_id
        
        encrypted_id = encrypt_email_id(test_email.id)
        response = authenticated_client.patch(f"/api/v1/email/{encrypted_id}/archive?archived=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_archived"] is True
    
    @patch('app.api.email.get_email_provider')
    def test_delete_email(
        self,
        mock_get_provider,
        authenticated_client: TestClient,
        test_user,
        test_email_account,
        test_email
    ):
        """Test soft deleting email."""
        from app.core.id_encryption import encrypt_email_id
        
        # Mock email provider
        mock_provider = MagicMock()
        mock_provider.connect = MagicMock(return_value=True)
        mock_provider.delete_email = MagicMock(return_value=True)
        mock_provider.disconnect = MagicMock()
        mock_get_provider.return_value = mock_provider
        
        encrypted_id = encrypt_email_id(test_email.id)
        response = authenticated_client.delete(f"/api/v1/email/{encrypted_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_sync_emails(
        self,
        authenticated_client: TestClient,
        test_user,
        test_email_account
    ):
        """Test syncing emails from provider."""
        from app.core.id_encryption import encrypt_account_id
        
        encrypted_account_id = encrypt_account_id(test_email_account.id)
        
        # Mock the Celery task to avoid Redis connection errors
        with patch('app.api.email.fetch_emails_for_account') as mock_celery_task_class:
            mock_celery_task = MagicMock()
            mock_celery_task.id = "task-123"
            mock_celery_task.delay = MagicMock(return_value=mock_celery_task)
            mock_celery_task_class.delay = MagicMock(return_value=mock_celery_task)
            
            # Use /ingest endpoint with account_id parameter
            response = authenticated_client.post(
                f"/api/v1/email/ingest?account_id={encrypted_account_id}"
            )
            
            # If endpoint returns 503 (Celery not available), skip the test
            if response.status_code == 503:
                pytest.skip("Celery broker not available in test environment")
            
            assert response.status_code == 200
            data = response.json()
            assert "triggered_count" in data or "task_id" in data

