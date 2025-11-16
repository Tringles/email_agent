"""LangGraph 이메일 처리 파이프라인 통합 테스트."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from app.langgraph.state import EmailProcessingState, initialize_state
from app.langgraph.nodes.load_email import load_email_node
from app.langgraph.nodes.preprocess_html import preprocess_html_node
from app.langgraph.nodes.summarize import summarize_node
from app.langgraph.nodes.classify import classify_node
from app.langgraph.nodes.vector_search import vector_search_node
from app.langgraph.nodes.rule_engine import rule_engine_node
from app.langgraph.nodes.save_results import save_results_node
from app.langgraph.utils.state_validator import validate_basic_state, validate_state_for_node
from app.langgraph.utils.error_handler import handle_node_error


class TestEmailProcessingPipeline:
    """전체 파이프라인 통합 테스트"""
    
    @pytest.fixture
    def mock_email_data(self):
        """테스트용 이메일 데이터"""
        return {
            "subject": "테스트 이메일",
            "sender": "test@example.com",
            "sender_name": "Test Sender",
            "recipient": "user@example.com",
            "recipient_name": "Test User",
            "body_text": "이것은 테스트 이메일 본문입니다.",
            "body_html": "<p>이것은 테스트 이메일 본문입니다.</p>",
            "email_date": "2025-01-01T00:00:00",
            "received_date": "2025-01-01T00:00:00",
            "folder": "INBOX",
            "labels": [],
            "cc": None,
            "bcc": None,
            "reply_to": None,
            "attachments": [],
            "attachment_count": 0,
            "has_attachments": False,
            "attachment_names": [],
            "preview": "테스트 이메일",
            "headers": {},
            "provider_metadata": {},
            "provider_message_id": "test-123",
            "provider_thread_id": "thread-123",
        }
    
    @pytest.fixture
    def initial_state(self):
        """초기 상태 생성"""
        return initialize_state(email_id=1, user_id=1)
    
    def test_initialize_state(self, initial_state):
        """초기 상태 생성 테스트"""
        assert initial_state["email_id"] == 1
        assert initial_state["user_id"] == 1
        assert initial_state["email_data"] is None
        assert initial_state["completed_nodes"] == []
        assert initial_state["errors"] == []
        assert initial_state["started_at"] is not None
    
    def test_basic_state_validation(self, initial_state):
        """기본 상태 검증 테스트"""
        validation = validate_basic_state(initial_state)
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
    
    @patch('app.langgraph.nodes.load_email.EmailRepository')
    @patch('app.langgraph.nodes.load_email.SessionLocal')
    def test_load_email_node_success(self, mock_session, mock_repo, initial_state, mock_email_data):
        """load_email_node 성공 테스트"""
        # Mock 설정
        mock_db = Mock()
        mock_session.return_value = mock_db
        mock_email_repo = Mock()
        mock_repo.return_value = mock_email_repo
        
        # Mock 이메일 객체
        mock_email = Mock()
        mock_email.email_account.user_id = 1
        mock_email.subject = mock_email_data["subject"]
        mock_email.sender = mock_email_data["sender"]
        mock_email.sender_name = mock_email_data["sender_name"]
        mock_email.recipient = mock_email_data["recipient"]
        mock_email.recipient_name = mock_email_data["recipient_name"]
        mock_email.body_text = mock_email_data["body_text"]
        mock_email.body_html = mock_email_data["body_html"]
        mock_email.email_date = datetime.fromisoformat(mock_email_data["email_date"])
        mock_email.received_date = datetime.fromisoformat(mock_email_data["received_date"])
        mock_email.folder = mock_email_data["folder"]
        mock_email.labels = mock_email_data["labels"]
        mock_email.cc = mock_email_data["cc"]
        mock_email.bcc = mock_email_data["bcc"]
        mock_email.reply_to = mock_email_data["reply_to"]
        mock_email.attachments = mock_email_data["attachments"]
        mock_email.attachment_count = mock_email_data["attachment_count"]
        mock_email.has_attachments = mock_email_data["has_attachments"]
        mock_email.preview = mock_email_data["preview"]
        mock_email.headers = mock_email_data["headers"]
        mock_email.provider_metadata = mock_email_data["provider_metadata"]
        mock_email.provider_message_id = mock_email_data["provider_message_id"]
        mock_email.provider_thread_id = mock_email_data["provider_thread_id"]
        
        mock_email_repo.get_email_by_id.return_value = mock_email
        
        # 노드 실행
        result_state = load_email_node(initial_state)
        
        # 검증
        assert result_state["email_data"] is not None
        assert result_state["email_data"]["subject"] == mock_email_data["subject"]
        assert "load_email" in result_state["completed_nodes"]
        assert result_state["current_node"] == "load_email"
        assert len(result_state["errors"]) == 0
    
    def test_preprocess_html_node_success(self, initial_state, mock_email_data):
        """preprocess_html_node 성공 테스트"""
        # 상태 설정
        state = initial_state.copy()
        state["email_data"] = mock_email_data
        
        # 노드 실행
        result_state = preprocess_html_node(state)
        
        # 검증
        assert result_state["processed_body_html"] is not None
        assert len(result_state["processed_body_html"]) > 0
        assert "preprocess_html" in result_state["completed_nodes"]
        assert result_state["current_node"] == "preprocess_html"
    
    @patch('app.langgraph.nodes.summarize.get_llm_service')
    @patch('app.langgraph.nodes.summarize.settings')
    def test_summarize_node_success(self, mock_settings, mock_llm_service, initial_state, mock_email_data):
        """summarize_node 성공 테스트"""
        # Mock 설정
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"
        mock_llm_service.return_value.invoke.return_value = "테스트 요약"
        
        # 상태 설정
        state = initial_state.copy()
        state["email_data"] = mock_email_data
        state["processed_body_html"] = "테스트 본문"
        
        # 노드 실행
        result_state = summarize_node(state)
        
        # 검증
        assert result_state["summary"] is not None
        assert "summarize" in result_state["completed_nodes"]
        assert result_state["current_node"] == "summarize"
    
    @patch('app.langgraph.nodes.summarize.settings')
    def test_summarize_node_no_api_key(self, mock_settings, initial_state, mock_email_data):
        """summarize_node API 키 없음 테스트"""
        # Mock 설정
        mock_settings.OPENAI_API_KEY = None
        
        # 상태 설정
        state = initial_state.copy()
        state["email_data"] = mock_email_data
        
        # 노드 실행
        result_state = summarize_node(state)
        
        # 검증 (API 키가 없어도 다음 노드로 진행)
        assert result_state["summary"] is None
        assert "summarize" in result_state["completed_nodes"]
    
    @patch('app.langgraph.nodes.classify.get_llm_service')
    @patch('app.langgraph.nodes.classify.settings')
    def test_classify_node_success(self, mock_settings, mock_llm_service, initial_state, mock_email_data):
        """classify_node 성공 테스트"""
        # Mock 설정
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_response = {
            "importance_score": 0.8,
            "importance_level": "high",
            "classification": {"category": "work", "tags": ["important"]}
        }
        mock_llm_service.return_value.invoke_with_messages.return_value = str(mock_response)
        
        # 상태 설정
        state = initial_state.copy()
        state["email_data"] = mock_email_data
        state["summary"] = "테스트 요약"
        
        # 노드 실행
        result_state = classify_node(state)
        
        # 검증
        assert result_state["importance_score"] is not None
        assert result_state["importance_level"] is not None
        assert result_state["classification"] is not None
        assert "classify" in result_state["completed_nodes"]
    
    def test_state_validation_for_node(self, initial_state, mock_email_data):
        """노드별 상태 검증 테스트"""
        # preprocess_html 노드 검증
        state = initial_state.copy()
        state["email_data"] = mock_email_data
        
        validation = validate_state_for_node(state, "preprocess_html")
        assert validation["valid"] is True
        
        # email_data 없이 검증 (실패해야 함)
        state_no_data = initial_state.copy()
        validation_fail = validate_state_for_node(state_no_data, "preprocess_html")
        assert validation_fail["valid"] is False
        assert len(validation_fail["errors"]) > 0


class TestErrorHandling:
    """에러 처리 테스트"""
    
    @pytest.fixture
    def initial_state(self):
        """초기 상태 생성"""
        return initialize_state(email_id=1, user_id=1)
    
    def test_handle_node_error(self, initial_state):
        """handle_node_error 테스트"""
        state = initial_state.copy()
        error = ValueError("Test error")
        
        handle_node_error(
            state=state,
            node_name="test_node",
            error=error,
            default_values={"test_field": "default_value"},
            continue_on_error=True
        )
        
        # 검증
        assert len(state["errors"]) == 1
        assert state["errors"][0]["node"] == "test_node"
        assert state["errors"][0]["error"] == "Test error"
        assert state["test_field"] == "default_value"
        assert "test_node" in state["completed_nodes"]
    
    def test_preprocess_html_node_error_handling(self, initial_state):
        """preprocess_html_node 에러 처리 테스트"""
        state = initial_state.copy()
        state["email_data"] = None  # 에러 유발
        
        # 노드 실행 (에러 발생 예상)
        result_state = preprocess_html_node(state)
        
        # 검증 (에러가 있어도 다음 노드로 진행)
        assert len(result_state["errors"]) > 0
        assert "preprocess_html" in result_state["completed_nodes"]
    
    @patch('app.langgraph.nodes.summarize.get_llm_service')
    @patch('app.langgraph.nodes.summarize.settings')
    def test_summarize_node_error_handling(self, mock_settings, mock_llm_service, initial_state):
        """summarize_node 에러 처리 테스트"""
        # Mock 설정 (에러 발생)
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"
        mock_llm_service.return_value.invoke.side_effect = Exception("LLM Error")
        
        # 상태 설정
        state = initial_state.copy()
        state["email_data"] = {"body_text": "test"}
        
        # 노드 실행
        result_state = summarize_node(state)
        
        # 검증 (에러가 있어도 다음 노드로 진행)
        assert len(result_state["errors"]) > 0
        assert result_state["summary"] is None
        assert "summarize" in result_state["completed_nodes"]


class TestStateValidation:
    """상태 검증 테스트"""
    
    def test_validate_importance_score(self):
        """importance_score 검증 테스트"""
        from app.langgraph.utils.state_validator import validate_importance_score
        
        # 유효한 값
        validation = validate_importance_score(0.5)
        assert validation["valid"] is True
        
        # 범위 밖 값
        validation = validate_importance_score(1.5)
        assert validation["valid"] is False
        
        # None 값 (경고만)
        validation = validate_importance_score(None)
        assert validation["valid"] is True
        assert len(validation["warnings"]) > 0
    
    def test_validate_importance_level(self):
        """importance_level 검증 테스트"""
        from app.langgraph.utils.state_validator import validate_importance_level
        
        # 유효한 값
        validation = validate_importance_level("high")
        assert validation["valid"] is True
        
        # 유효하지 않은 값
        validation = validate_importance_level("invalid")
        assert validation["valid"] is False
        
        # None 값 (경고만)
        validation = validate_importance_level(None)
        assert validation["valid"] is True
        assert len(validation["warnings"]) > 0
    
    def test_validate_classification(self):
        """classification 검증 테스트"""
        from app.langgraph.utils.state_validator import validate_classification
        
        # 유효한 값
        classification = {"category": "work", "tags": ["important"]}
        validation = validate_classification(classification)
        assert validation["valid"] is True
        
        # category 없음 (경고만)
        classification = {"tags": ["important"]}
        validation = validate_classification(classification)
        assert validation["valid"] is True
        assert len(validation["warnings"]) > 0
        
        # None 값 (경고만)
        validation = validate_classification(None)
        assert validation["valid"] is True
        assert len(validation["warnings"]) > 0


class TestPipelineIntegration:
    """파이프라인 통합 테스트"""
    
    @pytest.fixture
    def mock_email_data(self):
        """테스트용 이메일 데이터"""
        return {
            "subject": "통합 테스트 이메일",
            "sender": "test@example.com",
            "recipient": "user@example.com",
            "body_text": "통합 테스트 본문",
            "body_html": "<p>통합 테스트 본문</p>",
            "email_date": "2025-01-01T00:00:00",
            "received_date": "2025-01-01T00:00:00",
            "folder": "INBOX",
            "labels": [],
            "attachments": [],
            "attachment_count": 0,
            "has_attachments": False,
            "attachment_names": [],
        }
    
    def test_full_pipeline_state_flow(self, mock_email_data):
        """전체 파이프라인 상태 흐름 테스트"""
        # 초기 상태
        state = initialize_state(email_id=1, user_id=1)
        
        # 1. email_data 설정 (load_email_node 대체)
        state["email_data"] = mock_email_data
        state["completed_nodes"].append("load_email")
        
        # 2. preprocess_html
        state = preprocess_html_node(state)
        assert "preprocess_html" in state["completed_nodes"]
        assert state["processed_body_html"] is not None
        
        # 3. summarize (API 키 없이도 진행)
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            state = summarize_node(state)
            assert "summarize" in state["completed_nodes"]
        
        # 4. classify (기본값 사용)
        with patch('app.langgraph.nodes.classify.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            state = classify_node(state)
            assert "classify" in state["completed_nodes"]
            assert state["importance_level"] is not None
        
        # 5. vector_search (스킵)
        with patch('app.langgraph.nodes.vector_search.settings') as mock_settings:
            mock_settings.VECTOR_DB_URL = None
            mock_settings.OPENAI_API_KEY = None
            state = vector_search_node(state)
            assert "vector_search" in state["completed_nodes"]
        
        # 6. rule_engine
        state = rule_engine_node(state)
        assert "rule_engine" in state["completed_nodes"]
        
        # 최종 상태 검증
        assert len(state["completed_nodes"]) >= 5
        assert state["current_node"] == "rule_engine"

