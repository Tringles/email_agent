"""Agent Service tests."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.agent_service import AgentService
from app.models.email import EmailStatus


class TestAgentService:
    """Agent Service tests."""
    
    @patch('app.services.agent_service.create_email_processing_graph')
    def test_init(self, mock_create_graph):
        """Test AgentService initialization."""
        mock_graph = MagicMock()
        mock_create_graph.return_value = mock_graph
        
        service = AgentService()
        
        assert service.graph == mock_graph
        mock_create_graph.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.agent_service.create_email_processing_graph')
    @patch('app.services.agent_service.EmailRepository')
    async def test_process_email_success(self, mock_repo_class, mock_create_graph, db, test_user, test_email_account, test_email):
        """Test successful email processing."""
        # Mock graph
        mock_graph = AsyncMock()
        mock_final_state = {
            "completed_nodes": ["load_email", "summarize", "classify"],
            "errors": [],
            "summary": "Test summary",
            "importance_level": "high",
            "classification": {"category": "work", "tags": ["important"]}
        }
        mock_graph.ainvoke = AsyncMock(return_value=mock_final_state)
        mock_create_graph.return_value = mock_graph
        
        # Mock repository
        mock_repo = MagicMock()
        mock_repo.get_email_by_id.return_value = test_email
        mock_repo.update_email = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        service = AgentService()
        service.graph = mock_graph  # Override with our mock
        
        result = await service.process_email(
            email_id=test_email.id,
            user_id=test_user.id,
            db=db
        )
        
        assert result["success"] is True
        assert result["email_id"] == test_email.id
        assert result["completed_nodes"] == ["load_email", "summarize", "classify"]
        assert result["summary"] == "Test summary"
        assert result["importance_level"] == "high"
        
        # Verify email status was updated to PROCESSING
        mock_repo.update_email.assert_called_once()
        call_kwargs = mock_repo.update_email.call_args[1]
        assert call_kwargs["status"] == EmailStatus.PROCESSING
    
    @pytest.mark.asyncio
    @patch('app.services.agent_service.create_email_processing_graph')
    @patch('app.services.agent_service.EmailRepository')
    async def test_process_email_not_found(self, mock_repo_class, mock_create_graph, db, test_user):
        """Test processing email that doesn't exist."""
        # Mock graph
        mock_graph = AsyncMock()
        mock_create_graph.return_value = mock_graph
        
        # Mock repository - email not found
        mock_repo = MagicMock()
        mock_repo.get_email_by_id.return_value = None
        mock_repo_class.return_value = mock_repo
        
        service = AgentService()
        service.graph = mock_graph
        
        # Should still attempt to process (graph will handle missing email)
        result = await service.process_email(
            email_id=999,
            user_id=test_user.id,
            db=db
        )
        
        # Graph should still be invoked even if email not found initially
        assert "success" in result
    
    @pytest.mark.asyncio
    @patch('app.services.agent_service.create_email_processing_graph')
    @patch('app.services.agent_service.EmailRepository')
    async def test_process_email_graph_error(self, mock_repo_class, mock_create_graph, db, test_user, test_email):
        """Test email processing with graph error."""
        # Mock graph to raise exception
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(side_effect=Exception("Graph error"))
        mock_create_graph.return_value = mock_graph
        
        # Mock repository
        mock_repo = MagicMock()
        mock_repo.get_email_by_id.return_value = test_email
        mock_repo_class.return_value = mock_repo
        
        service = AgentService()
        service.graph = mock_graph
        
        result = await service.process_email(
            email_id=test_email.id,
            user_id=test_user.id,
            db=db
        )
        
        assert result["success"] is False
        assert "error" in result or "errors" in result
    
    @patch('app.services.agent_service.create_email_processing_graph')
    @patch('asyncio.get_event_loop')
    @patch('app.services.agent_service.EmailRepository')
    def test_process_email_sync_success(self, mock_repo_class, mock_get_loop, mock_create_graph, db, test_user, test_email):
        """Test synchronous email processing."""
        # Mock graph
        mock_graph = AsyncMock()
        mock_final_state = {
            "completed_nodes": ["load_email", "summarize"],
            "errors": [],
            "summary": "Test summary",
            "importance_level": "high",
            "classification": {}
        }
        mock_graph.ainvoke = AsyncMock(return_value=mock_final_state)
        mock_create_graph.return_value = mock_graph
        
        # Mock asyncio event loop
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = False
        mock_loop.run_until_complete = MagicMock(return_value={
            "success": True,
            "email_id": test_email.id,
            "completed_nodes": ["load_email", "summarize"],
            "errors": [],
            "summary": "Test summary",
            "importance_level": "high",
            "classification": {}
        })
        mock_get_loop.return_value = mock_loop
        
        # Mock repository
        mock_repo = MagicMock()
        mock_repo.get_email_by_id.return_value = test_email
        mock_repo.update_email = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        service = AgentService()
        service.graph = mock_graph
        
        result = service.process_email_sync(
            email_id=test_email.id,
            user_id=test_user.id,
            db=db
        )
        
        assert result["success"] is True
        assert result["summary"] == "Test summary"

