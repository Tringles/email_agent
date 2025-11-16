"""Agent API tests."""

import pytest

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestAgentAPI:
    """Agent endpoint tests."""
    
    def test_process_email_unauthorized(self, client: TestClient):
        """Test processing email without authentication."""
        response = client.post("/api/v1/agent/process?email_id=test-id")
        
        # FastAPI HTTPBearer returns 403 when no token is provided
        assert response.status_code in [401, 403]
    
    @patch('app.api.agent.process_email_agent_task')
    def test_process_email_async(
        self,
        mock_task,
        authenticated_client: TestClient,
        test_user,
        test_email
    ):
        """Test async email processing."""
        from app.core.id_encryption import encrypt_email_id
        
        encrypted_id = encrypt_email_id(test_email.id)
        mock_celery_task = MagicMock()
        mock_celery_task.id = "task-123"
        mock_task.delay.return_value = mock_celery_task
        
        response = authenticated_client.post(
            f"/api/v1/agent/process?email_id={encrypted_id}&async_mode=true"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "processing"
        assert "task_id" in data
        mock_task.delay.assert_called_once()
    
    @patch('app.api.agent.AgentService')
    def test_process_email_sync(
        self,
        mock_agent_service_class,
        authenticated_client: TestClient,
        test_user,
        test_email,
        db
    ):
        """Test sync email processing."""
        from app.core.id_encryption import encrypt_email_id
        
        encrypted_id = encrypt_email_id(test_email.id)
        
        from unittest.mock import AsyncMock
        
        mock_service = MagicMock()
        mock_agent_service_class.return_value = mock_service
        # process_email is async, use AsyncMock
        mock_service.process_email = AsyncMock(return_value={
            "success": True,
            "completed_nodes": ["load_email", "summarize", "classify"],
            "errors": [],
            "summary": "Test summary",
            "importance_level": "high",
            "classification": {"category": "work", "tags": ["important"]}
        })
        
        response = authenticated_client.post(
            f"/api/v1/agent/process?email_id={encrypted_id}&async_mode=false"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "completed"
        assert "summary" in data
        assert "importance_level" in data
    
    def test_process_email_invalid_id(
        self,
        authenticated_client: TestClient
    ):
        """Test processing email with invalid ID."""
        # Use an invalid encrypted ID format
        response = authenticated_client.post(
            "/api/v1/agent/process?email_id=invalid-id-format"
        )
        
        assert response.status_code == 400
        assert "Invalid email ID" in response.json()["detail"]
    
    @patch('app.api.agent.process_email_agent_task')
    def test_process_emails_batch(
        self,
        mock_task,
        authenticated_client: TestClient,
        test_user,
        test_email
    ):
        """Test batch email processing."""
        from app.core.id_encryption import encrypt_email_id
        
        encrypted_id = encrypt_email_id(test_email.id)
        mock_celery_task = MagicMock()
        mock_celery_task.id = "task-123"
        mock_task.delay.return_value = mock_celery_task
        
        request_data = {
            "email_ids": [encrypted_id, encrypted_id],  # Use same encrypted ID twice
            "async_mode": True
        }
        
        response = authenticated_client.post(
            "/api/v1/agent/process/batch",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert len(data["tasks"]) == 2
    
    def test_get_processing_stats(
        self,
        authenticated_client: TestClient,
        test_user,
        test_email_account,
        test_email
    ):
        """Test getting AI processing statistics."""
        response = authenticated_client.get("/api/v1/agent/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "processed" in data
        assert "pending" in data
        assert "processing" in data
        assert isinstance(data["processed"], int)
        assert isinstance(data["pending"], int)
        assert isinstance(data["processing"], int)
    
    def test_get_processing_emails(
        self,
        authenticated_client: TestClient,
        test_user,
        test_email_account,
        test_email
    ):
        """Test getting processing emails list."""
        response = authenticated_client.get("/api/v1/agent/processing")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_pending_emails(
        self,
        authenticated_client: TestClient,
        test_user,
        test_email_account
    ):
        """Test getting pending emails list."""
        response = authenticated_client.get("/api/v1/agent/pending")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

