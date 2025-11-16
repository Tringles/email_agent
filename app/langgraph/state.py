"""LangGraph State 정의."""

from datetime import datetime
from sqlalchemy.orm import Session
from typing import TypedDict, Optional, List, Dict, Any


class EmailProcessingState(TypedDict):
    """이메일 처리 파이프라인의 상태를 관리하는 State"""
    
    # === 입력 데이터 ===
    email_id: int  # 처리할 이메일 ID
    user_id: int   # 사용자 ID (인증/인가용)
    
    # === 이메일 원본 데이터 ===
    email_data: Dict[str, Any]  # DB에서 가져온 이메일 데이터
    # 포함 필드 (중요도 평가 및 VectorDB 저장에 사용):
    # - 기본 정보: subject, sender, sender_name, recipient, recipient_name
    # - 본문: body_text, body_html
    # - 날짜: email_date, received_date
    # - 폴더/라벨: folder, labels
    # - 참조: cc, bcc, reply_to
    # - 첨부파일: attachments (전체 메타데이터), attachment_count, has_attachments, attachment_names (파일 이름 리스트)
    # - 기타: preview, headers, provider_metadata, provider_message_id, provider_thread_id
    
    # === 처리 결과 (각 노드에서 업데이트) ===
    processed_body_html: Optional[str]  # Preprocess Node 결과 (HTML 전처리된 텍스트)
    summary: Optional[str]  # Summarize Node 결과
    importance_score: Optional[float]  # Classify Node 결과 (0.0-1.0)
    importance_level: Optional[str]  # "low", "medium", "high", "urgent"
    classification: Optional[Dict[str, Any]]  # 카테고리, 태그 등
    
    # === VectorDB 관련 ===
    vector_db_id: Optional[str]  # Vector Search Node 결과
    embedding_model: Optional[str]  # 사용한 임베딩 모델
    similar_emails: Optional[List[Dict[str, Any]]]  # 유사 이메일 목록
    vector_metadata: Optional[Dict[str, Any]]  # VectorDB에 저장된 메타데이터 (이메일 메타데이터 포함)
    
    # === Rule Engine 결과 ===
    rule_applied: Optional[str]  # 적용된 규칙 이름
    auto_action: Optional[str]  # "delete", "archive", "tag", "move", "none"
    action_details: Optional[Dict[str, Any]]  # 액션 상세 정보
    
    # === 처리 상태 관리 ===
    current_node: Optional[str]  # 현재 실행 중인 노드 이름
    completed_nodes: List[str]  # 완료된 노드 목록
    errors: List[Dict[str, Any]]  # 에러 정보 (노드명, 에러 메시지, 타임스탬프)
    
    # === 컨텍스트 데이터 ===
    user_rules: Optional[List[Dict[str, Any]]]  # 사용자 정의 규칙
    # Note: db_session은 state에 포함하지 않음 (직렬화 불가)
    # 각 노드에서 필요한 경우 새로운 세션을 생성하거나 외부에서 전달받음
    
    # === 메타데이터 ===
    started_at: Optional[datetime]  # 처리 시작 시간
    completed_at: Optional[datetime]  # 처리 완료 시간


def initialize_state(
    email_id: int,
    user_id: int
) -> EmailProcessingState:
    """
    State를 초기화 (기본 구조만 생성)
    
    Note: 이메일 데이터는 load_email_node에서 로드됩니다.
    이 함수는 Entry 노드 진입 전 기본 state만 생성합니다.
    
    Args:
        email_id: 처리할 이메일 ID
        user_id: 사용자 ID
        
    Returns:
        초기화된 EmailProcessingState (email_data는 None)
    """
    return EmailProcessingState(
        email_id=email_id,
        user_id=user_id,
        email_data=None,  # load_email_node에서 로드
        processed_body_html=None,
        summary=None,
        importance_score=None,
        importance_level=None,
        classification=None,
        vector_db_id=None,
        vector_metadata=None,
        embedding_model=None,
        similar_emails=None,
        rule_applied=None,
        auto_action=None,
        action_details=None,
        current_node=None,
        completed_nodes=[],
        errors=[],
        user_rules=None,  # 추후 구현
        started_at=datetime.now(),
        completed_at=None,
    )
