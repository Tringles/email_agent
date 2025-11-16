"""Rule Engine Node."""

import re
from loguru import logger
from typing import Dict, Any, List, Optional

from app.db.session import SessionLocal
from app.db.repositories.user_rule_repo import UserRuleRepository
from app.db.repositories.email_repo import EmailRepository
from app.langgraph.state import EmailProcessingState
from app.langgraph.utils.error_handler import handle_node_error
from app.models.user_rule import RuleType, RuleAction


def rule_engine_node(state: EmailProcessingState) -> EmailProcessingState:
    """
    규칙 평가 및 자동 액션 결정
    
    Args:
        state: EmailProcessingState
        
    Returns:
        업데이트된 EmailProcessingState
    """
    try:
        logger.info(f"Running rule engine for email {state['email_id']}")
        
        # 규칙 평가
        rule_result = _evaluate_rules(state)
        
        state["rule_applied"] = rule_result.get("rule_applied")
        state["auto_action"] = rule_result.get("auto_action", "none")
        state["action_details"] = rule_result.get("action_details", {})
        
        state["current_node"] = "rule_engine"
        state["completed_nodes"].append("rule_engine")
        
        logger.info(
            f"Rule engine completed for email {state['email_id']}: "
            f"rule={state['rule_applied']}, action={state['auto_action']}"
        )
        
    except Exception as e:
        # 공통 에러 처리 (실패 시 기본값 설정)
        handle_node_error(
            state=state,
            node_name="rule_engine",
            error=e,
            default_values={
                "rule_applied": None,
                "auto_action": "none",
                "action_details": {}
            },
            continue_on_error=True
        )
    
    return state


def _evaluate_rules(state: EmailProcessingState) -> Dict[str, Any]:
    """
    규칙 평가 및 자동 액션 결정
    
    우선순위:
    1. 사용자 정의 규칙 (우선순위 높은 순)
    2. 하드코딩된 기본 규칙
    
    Args:
        state: EmailProcessingState
        
    Returns:
        {
            "rule_applied": str,  # 적용된 규칙 이름
            "auto_action": str,    # "delete", "archive", "tag", "move", "none"
            "action_details": dict  # 액션 상세 정보
        }
    """
    # 1. 사용자 정의 규칙 평가 (우선순위 높은 순)
    user_rule_result = _evaluate_user_rules(state)
    if user_rule_result and user_rule_result.get("auto_action") != "none":
        return user_rule_result
    
    # 2. 하드코딩된 기본 규칙 평가
    return _evaluate_default_rules(state)


def _evaluate_user_rules(state: EmailProcessingState) -> Optional[Dict[str, Any]]:
    """
    사용자 정의 규칙 평가
    
    Args:
        state: EmailProcessingState
        
    Returns:
        규칙 매칭 결과 또는 None
    """
    db = None
    try:
        # DB 세션 생성
        db = SessionLocal()
        rule_repo = UserRuleRepository(db)
        
        # 활성화된 사용자 규칙 가져오기 (우선순위 순)
        user_rules = rule_repo.get_active_rules_by_user(state["user_id"])
        
        for rule in user_rules:
            # 규칙 타입별 매칭
            if rule.rule_type == RuleType.SIMILARITY_BASED:
                if _matches_similarity_rule(state, rule, db):
                    return {
                        "rule_applied": rule.rule_name,
                        "auto_action": rule.action.value,
                        "action_details": rule.action_details or {}
                    }
            
            elif rule.rule_type == RuleType.METADATA_BASED:
                if _matches_metadata_rule(state, rule):
                    return {
                        "rule_applied": rule.rule_name,
                        "auto_action": rule.action.value,
                        "action_details": rule.action_details or {}
                    }
            
            elif rule.rule_type == RuleType.CLASSIFICATION_BASED:
                if _matches_classification_rule(state, rule):
                    return {
                        "rule_applied": rule.rule_name,
                        "auto_action": rule.action.value,
                        "action_details": rule.action_details or {}
                    }
        
        return None
        
    except Exception as e:
        logger.error(f"Error evaluating user rules: {e}", exc_info=True)
        return None
    finally:
        if db:
            db.close()


def _matches_similarity_rule(
    state: EmailProcessingState,
    rule,
    db: SessionLocal
) -> bool:
    """
    Vector DB 유사도 검색으로 규칙 매칭
    
    Args:
        state: EmailProcessingState
        rule: UserRule 객체
        db: DB 세션
        
    Returns:
        규칙 매칭 여부
    """
    try:
        if not rule.reference_email_id or rule.similarity_threshold is None:
            return False
        
        # 예시 이메일 조회 (soft delete된 이메일도 조회 가능하도록 include_deleted=True)
        email_repo = EmailRepository(db)
        reference_email = email_repo.get_email_by_id(
            rule.reference_email_id, 
            state["user_id"],
            include_deleted=True  # Soft delete된 이메일도 참조 가능
        )
        if not reference_email or not reference_email.vector_db_id:
            logger.warning(f"Reference email {rule.reference_email_id} not found or not processed")
            return False
        
        # 현재 이메일이 Vector DB에 저장되어 있는지 확인
        if not state.get("vector_db_id"):
            logger.warning(f"Current email {state['email_id']} not in Vector DB yet")
            return False
        
        # Vector DB에서 유사도 검색
        similarity = _calculate_similarity(
            state=state,
            reference_vector_id=reference_email.vector_db_id
        )
        
        if similarity is None:
            return False
        
        # 유사도가 임계값 이하이면 매칭 (낮을수록 유사)
        is_match = similarity <= rule.similarity_threshold
        
        if is_match:
            logger.info(
                f"Similarity rule matched: {rule.rule_name}, "
                f"similarity={similarity:.4f}, threshold={rule.similarity_threshold}"
            )
        
        return is_match
        
    except Exception as e:
        logger.error(f"Error matching similarity rule: {e}", exc_info=True)
        return False


def _calculate_similarity(
    state: EmailProcessingState,
    reference_vector_id: str
) -> Optional[float]:
    """
    현재 이메일과 예시 이메일의 유사도 계산
    
    Args:
        state: EmailProcessingState
        reference_vector_id: 예시 이메일의 Vector DB ID
        
    Returns:
        유사도 점수 (0.0~1.0, 낮을수록 유사) 또는 None
    """
    try:
        from app.core.config import settings
        from langchain_openai import OpenAIEmbeddings
        
        if not settings.VECTOR_DB_URL or not settings.OPENAI_API_KEY:
            return None
        
        # 임베딩 모델 초기화
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        # Qdrant 클라이언트 초기화
        from app.langgraph.nodes.vector_search import _get_qdrant_client, COLLECTION_NAME
        qdrant_client = _get_qdrant_client()
        
        # 현재 이메일의 텍스트 준비
        from app.langgraph.nodes.vector_search import _prepare_text_for_embedding
        query_text = _prepare_text_for_embedding(state)
        
        # 현재 이메일의 임베딩 생성
        current_embedding = embeddings.embed_query(query_text)
        
        # reference_vector_id의 임베딩 가져오기 (Qdrant에서 직접)
        # Qdrant 클라이언트의 retrieve는 리스트를 직접 반환
        # with_vectors=True를 명시적으로 전달해야 벡터 데이터를 가져올 수 있음
        result = qdrant_client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[reference_vector_id],
            with_vectors=True
        )
        
        # result가 리스트인지 확인 (최신 Qdrant 클라이언트는 리스트를 직접 반환)
        if isinstance(result, list):
            points = result
        else:
            # 구버전: result.points 사용
            points = getattr(result, 'points', [])
        
        if not points or len(points) == 0:
            logger.warning(f"Reference vector {reference_vector_id} not found in Qdrant")
            return None
        
        reference_point = points[0]
        
        # 벡터 데이터 추출 (PointStruct 또는 dict 형태)
        # Qdrant Python 클라이언트는 PointStruct 객체를 반환하며, vector 속성은 리스트 형태
        vector = None
        
        # PointStruct 객체인 경우
        if hasattr(reference_point, 'vector'):
            vector_attr = reference_point.vector
            # 벡터가 딕셔너리인 경우 (named vectors - 여러 벡터가 있는 경우)
            if isinstance(vector_attr, dict):
                # 기본 벡터 이름을 사용하거나 첫 번째 벡터 사용
                vector = vector_attr.get('vector') or vector_attr.get('default') or (list(vector_attr.values())[0] if vector_attr else None)
            # 벡터가 리스트인 경우 (일반적인 경우)
            elif isinstance(vector_attr, list):
                vector = vector_attr
            else:
                vector = vector_attr
        # dict 형태인 경우
        elif isinstance(reference_point, dict):
            vector_attr = reference_point.get('vector')
            if isinstance(vector_attr, dict):
                vector = vector_attr.get('vector') or vector_attr.get('default') or (list(vector_attr.values())[0] if vector_attr else None)
            elif isinstance(vector_attr, list):
                vector = vector_attr
            else:
                vector = vector_attr
        else:
            # 벡터 속성 접근 시도
            vector_attr = getattr(reference_point, 'vector', None)
            if isinstance(vector_attr, dict):
                vector = vector_attr.get('vector') or vector_attr.get('default') or (list(vector_attr.values())[0] if vector_attr else None)
            elif isinstance(vector_attr, list):
                vector = vector_attr
            else:
                vector = vector_attr
        
        if not vector:
            # 디버깅을 위해 reference_point의 구조 로깅
            logger.debug(
                f"Reference point structure for {reference_vector_id}: "
                f"type={type(reference_point)}, "
                f"has_vector={hasattr(reference_point, 'vector') if not isinstance(reference_point, dict) else 'vector' in reference_point}, "
                f"vector_attr_type={type(getattr(reference_point, 'vector', None)) if hasattr(reference_point, 'vector') else 'N/A'}, "
                f"attrs={[attr for attr in dir(reference_point) if not attr.startswith('_')][:10]}"
            )
            logger.warning(f"Reference vector {reference_vector_id} has no vector data")
            return None
        
        # 벡터가 리스트인지 확인
        if not isinstance(vector, (list, tuple)):
            logger.warning(
                f"Reference vector {reference_vector_id} vector is not a list/tuple: "
                f"type={type(vector)}"
            )
            return None
        
        # 코사인 거리 계산 (Qdrant는 코사인 거리 사용)
        import numpy as np
        current_vec = np.array(current_embedding, dtype=np.float32)
        reference_vec = np.array(vector, dtype=np.float32)
        
        # 정규화
        current_norm = np.linalg.norm(current_vec)
        reference_norm = np.linalg.norm(reference_vec)
        
        if current_norm == 0 or reference_norm == 0:
            return None
        
        # 코사인 유사도 계산 (0.0~1.0, 높을수록 유사)
        cosine_similarity = np.dot(current_vec, reference_vec) / (current_norm * reference_norm)
        
        # 코사인 거리로 변환 (0.0~2.0, 낮을수록 유사)
        # 코사인 거리 = 1 - 코사인 유사도
        cosine_distance = 1.0 - cosine_similarity
        
        # Qdrant의 코사인 거리는 0.0~2.0 범위이지만,
        # 우리는 0.0~1.0 범위로 정규화해서 사용 (낮을수록 유사)
        # normalized_distance = cosine_distance / 2.0
        
        # 하지만 Qdrant의 similarity_search_with_score는 이미 거리를 반환하므로
        # 그대로 사용 (0.0~2.0 범위)
        # 사용자가 설정한 threshold도 0.0~1.0 범위이므로, 2로 나눠서 비교
        normalized_distance = cosine_distance / 2.0
        
        return float(normalized_distance)
        
    except Exception as e:
        logger.error(f"Error calculating similarity: {e}", exc_info=True)
        return None


def _matches_metadata_rule(state: EmailProcessingState, rule) -> bool:
    """
    메타데이터 기반 규칙 매칭
    
    Args:
        state: EmailProcessingState
        rule: UserRule 객체
        
    Returns:
        규칙 매칭 여부
    """
    email_data = state["email_data"]
    classification = state.get("classification", {})
    importance_level = state.get("importance_level", "medium")
    
    # 발신자 필터
    if rule.sender_filter:
        if email_data.get("sender", "").lower() != rule.sender_filter.lower():
            return False
    
    if rule.sender_pattern:
        if not re.search(rule.sender_pattern, email_data.get("sender", ""), re.IGNORECASE):
            return False
    
    # 제목 키워드
    if rule.subject_keywords:
        subject = email_data.get("subject", "").lower()
        if not all(keyword.lower() in subject for keyword in rule.subject_keywords):
            return False
    
    if rule.subject_pattern:
        if not re.search(rule.subject_pattern, email_data.get("subject", ""), re.IGNORECASE):
            return False
    
    # 카테고리 필터
    if rule.category_filter:
        if classification.get("category", "") != rule.category_filter:
            return False
    
    # 중요도 레벨 필터
    if rule.importance_level_filter:
        if importance_level != rule.importance_level_filter:
            return False
    
    # 폴더 필터
    if rule.folder_filter:
        if email_data.get("folder", "") != rule.folder_filter:
            return False
    
    # 첨부파일 필터
    if rule.has_attachments_filter is not None:
        if email_data.get("has_attachments", False) != rule.has_attachments_filter:
            return False
    
    return True


def _matches_classification_rule(state: EmailProcessingState, rule) -> bool:
    """
    분류 기반 규칙 매칭
    
    Args:
        state: EmailProcessingState
        rule: UserRule 객체
        
    Returns:
        규칙 매칭 여부
    """
    classification = state.get("classification", {})
    
    # 카테고리 필터
    if rule.classification_category:
        if classification.get("category", "") != rule.classification_category:
            return False
    
    # 태그 필터
    if rule.classification_tags:
        email_tags = classification.get("tags", [])
        if not any(tag in email_tags for tag in rule.classification_tags):
            return False
    
    return True


def _evaluate_default_rules(state: EmailProcessingState) -> Dict[str, Any]:
    """
    하드코딩된 기본 규칙 평가
    
    Args:
        state: EmailProcessingState
        
    Returns:
        규칙 평가 결과
    """
    email_data = state["email_data"]
    importance_level = state.get("importance_level", "medium")
    classification = state.get("classification", {})
    summary = state.get("summary", "")
    
    # 규칙 1: 스팸/광고 이메일 자동 삭제
    if _is_spam(email_data, classification, summary):
        return {
            "rule_applied": "auto_delete_spam",
            "auto_action": "delete",
            "action_details": {
                "reason": "스팸/광고 이메일로 판단됨",
                "classification": classification
            }
        }
    
    # 규칙 2: 중요도가 매우 낮은 이메일 아카이브
    if importance_level == "low":
        category = classification.get("category", "")
        if category in ["newsletter", "notification"]:
            return {
                "rule_applied": "auto_archive_low_importance",
                "auto_action": "archive",
                "action_details": {
                    "reason": "중요도가 낮고 뉴스레터/알림 카테고리",
                    "importance_level": importance_level,
                    "category": category
                }
            }
    
    # 규칙 3: 중요도가 높은 이메일 중요 표시
    if importance_level in ["high", "urgent"]:
        return {
            "rule_applied": "auto_mark_important",
            "auto_action": "tag",
            "action_details": {
                "reason": "중요도가 높은 이메일",
                "importance_level": importance_level,
                "tags": ["important", importance_level]
            }
        }
    
    # 규칙 4: 첨부파일이 있는 이메일 중요 표시
    if email_data.get("has_attachments", False):
        attachment_names = email_data.get("attachment_names", [])
        # 중요한 문서 확장자 체크
        important_extensions = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]
        has_important_attachment = any(
            any(ext in name.lower() for ext in important_extensions)
            for name in attachment_names
        )
        
        if has_important_attachment:
            return {
                "rule_applied": "auto_mark_important_attachment",
                "auto_action": "tag",
                "action_details": {
                    "reason": "중요한 문서 첨부파일이 있는 이메일",
                    "attachment_names": attachment_names,
                    "tags": ["has_attachment", "important"]
                }
            }
    
    # 기본: 액션 없음
    return {
        "rule_applied": None,
        "auto_action": "none",
        "action_details": {}
    }


def _is_spam(email_data: dict, classification: dict, summary: str) -> bool:
    """
    스팸/광고 이메일인지 판단
    
    Args:
        email_data: 이메일 데이터
        classification: 분류 결과
        summary: 요약
        
    Returns:
        스팸 여부
    """
    # 카테고리가 spam인 경우
    category = classification.get("category", "")
    if category == "spam":
        return True
    
    # 제목에 스팸 키워드가 있는 경우
    subject = email_data.get("subject", "").lower()
    spam_keywords = ["광고", "할인", "프로모션", "무료", "지금", "특가", "세일", "advertisement"]
    if any(keyword in subject for keyword in spam_keywords):
        # 단, 중요도가 높으면 스팸이 아닐 수 있음
        return False  # 일단 보수적으로 처리
    
    # 발신자가 알려진 스팸 도메인인 경우 (추후 확장 가능)
    # sender = email_data.get("sender", "")
    
    return False
