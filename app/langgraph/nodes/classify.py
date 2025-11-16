"""Classify Node."""

import json
from loguru import logger

from app.core.config import settings
from app.langgraph.state import EmailProcessingState
from app.services.llm_service import get_llm_service
from app.langgraph.utils.error_handler import handle_node_error
from app.langgraph.utils.state_validator import validate_state_for_node, validate_importance_score, validate_importance_level, validate_classification


# 메타데이터 우선순위 설정
METADATA_PRIORITY = {
    "high": [
        "subject",          # 제목이 가장 중요
        "sender",           # 발신자 (중요한 사람인지 판단)
        "labels",           # 라벨 (중요 표시 등)
        "folder",           # 폴더 (INBOX vs 기타)
        "attachment_names", # 첨부파일 이름 (중요한 문서인지 판단)
    ],
    "medium": [
        "cc",               # 참조인
        "bcc",              # 숨은 참조인
        "reply_to",         # 회신 주소
        "email_date",       # 이메일 날짜 (최근일수록 중요할 수 있음)
        "attachment_count", # 첨부파일 개수
        "has_attachments",  # 첨부파일 존재 여부
    ],
    "low": [
        "recipient",        # 수신인 (보통 자신)
        "preview",          # 미리보기
        "headers",          # 헤더 정보
        "provider_metadata", # 프로바이더 메타데이터
    ]
}


def classify_node(state: EmailProcessingState) -> EmailProcessingState:
    """
    중요도 평가 및 분류 (메타데이터 우선순위 적용)
    
    Args:
        state: EmailProcessingState
        
    Returns:
        업데이트된 EmailProcessingState
    """
    try:
        logger.info(f"Classifying email {state['email_id']}")
        
        # 상태 검증
        validation = validate_state_for_node(state, "classify")
        if not validation["valid"]:
            logger.warning(f"State validation failed for classify node: {validation['errors']}")
            # 필수 필드가 없으면 에러 발생
            if validation["errors"]:
                raise ValueError(f"State validation failed: {', '.join(validation['errors'])}")
        
        # OpenAI API 키 확인
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set, using default classification")
            state["importance_score"] = 0.5
            state["importance_level"] = "medium"
            state["classification"] = {"category": "unknown"}
            state["current_node"] = "classify"
            state["completed_nodes"].append("classify")
            return state
        
        # 메타데이터 수집
        email_data = state["email_data"]
        summary = state.get("summary", "")
        
        # 우선순위별로 메타데이터 정리
        high_priority_data = _extract_metadata_by_priority(email_data, "high")
        medium_priority_data = _extract_metadata_by_priority(email_data, "medium")
        low_priority_data = _extract_metadata_by_priority(email_data, "low")
        
        # LLM으로 중요도 평가 및 분류
        try:
            result = _classify_email(
                summary=summary,
                high_priority=high_priority_data,
                medium_priority=medium_priority_data,
                low_priority=low_priority_data
            )
            
            importance_score = result.get("importance_score", 0.5)
            importance_level = result.get("importance_level", "medium")
            classification = result.get("classification", {})
            
            # 출력 값 검증
            score_validation = validate_importance_score(importance_score)
            level_validation = validate_importance_level(importance_level)
            class_validation = validate_classification(classification)
            
            if not score_validation["valid"]:
                logger.warning(f"Invalid importance_score: {score_validation['errors']}, using default 0.5")
                importance_score = 0.5
            
            if not level_validation["valid"]:
                logger.warning(f"Invalid importance_level: {level_validation['errors']}, using default 'medium'")
                importance_level = "medium"
            
            if not class_validation["valid"]:
                logger.warning(f"Invalid classification: {class_validation['errors']}, using default")
                classification = {"category": "unknown"}
            
            state["importance_score"] = importance_score
            state["importance_level"] = importance_level
            state["classification"] = classification
        except Exception as classify_error:
            # 내부 에러 처리 (기본값 설정)
            logger.error(f"Error in _classify_email: {classify_error}", exc_info=True)
            state["importance_score"] = 0.5
            state["importance_level"] = "medium"
            state["classification"] = {"category": "unknown"}
            handle_node_error(
                state=state,
                node_name="classify",
                error=classify_error,
                default_values={
                    "importance_score": 0.5,
                    "importance_level": "medium",
                    "classification": {"category": "unknown"}
                },
                continue_on_error=True
            )
        
        state["current_node"] = "classify"
        state["completed_nodes"].append("classify")
        
        logger.info(
            f"Classification completed for email {state['email_id']}: "
            f"level={state['importance_level']}, score={state['importance_score']}"
        )
        
    except Exception as e:
        # 공통 에러 처리 (기본값 설정)
        handle_node_error(
            state=state,
            node_name="classify",
            error=e,
            default_values={
                "importance_score": 0.5,
                "importance_level": "medium",
                "classification": {"category": "unknown"}
            },
            continue_on_error=True
        )
    
    return state


def _extract_metadata_by_priority(email_data: dict, priority: str) -> dict:
    """
    우선순위에 따라 메타데이터 추출
    
    Args:
        email_data: 이메일 데이터
        priority: "high", "medium", "low"
        
    Returns:
        우선순위별 메타데이터 딕셔너리
    """
    result = {}
    fields = METADATA_PRIORITY.get(priority, [])
    
    for field in fields:
        if field in email_data and email_data[field] is not None:
            result[field] = email_data[field]
    
    return result


def _classify_email(
    summary: str,
    high_priority: dict,
    medium_priority: dict,
    low_priority: dict
) -> dict:
    """
    LLM을 사용하여 이메일 중요도 평가 및 분류 (LangChain 1.0 메시지 시스템 사용)
    
    Args:
        summary: 이메일 요약
        high_priority: High Priority 메타데이터
        medium_priority: Medium Priority 메타데이터
        low_priority: Low Priority 메타데이터
        
    Returns:
        {
            "importance_score": float (0.0-1.0),
            "importance_level": str ("low", "medium", "high", "urgent"),
            "classification": dict (카테고리, 태그 등)
        }
    """
    # LLM 서비스 가져오기 (JSON 응답을 위해 충분한 토큰 할당)
    llm_service = get_llm_service(temperature=0.2, max_tokens=5000)
    
    # Human 메시지 내용 준비
    human_content = f"""이메일 요약:
{summary or "요약 없음"}

[High Priority 메타데이터]
{_format_metadata(high_priority)}

[Medium Priority 메타데이터]
{_format_metadata(medium_priority)}

[Low Priority 메타데이터]
{_format_metadata(low_priority)}

위 정보를 바탕으로 중요도를 평가하고 분류해주세요. JSON 형식으로 응답해주세요."""
    
    # LangChain 1.0 메시지 시스템 사용 (JSON 형식 강제)
    response = llm_service.invoke_with_messages(
        system_prompt=llm_service.load_system_prompt("classify_system"),
        human_content=human_content,
        model_kwargs={"response_format": {"type": "json_object"}},
        operation_name="Classify"
    )
    
    # Output 로깅
    logger.debug(f"[Classify] LLM Output:\n{response}")
    
    # 토큰 사용량 로깅은 invoke_with_messages 내부에서 처리됨
    
    # JSON 파싱
    try:
        # 응답 내용 가져오기 (이미 문자열로 반환됨)
        content = response.strip()
        
        if not content:
            logger.warning("[Classify] Empty response from LLM")
            raise ValueError("Empty response from LLM")
        
        # JSON 코드 블록 제거 (```json ... ``` 형식)
        if content.startswith("```"):
            # 첫 번째 ``` 이후부터 마지막 ``` 이전까지 추출
            lines = content.split("\n")
            if lines[0].startswith("```"):
                # 첫 번째 줄 제거
                lines = lines[1:]
            # 마지막 ``` 제거
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        
        # JSON 객체 추출 (중괄호로 감싸진 부분만 추출)
        if "{" in content and "}" in content:
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            if start_idx < end_idx:
                content = content[start_idx:end_idx]
        
        # JSON 파싱
        result = json.loads(content)
        
        # 검증 및 정규화
        importance_score = float(result.get("importance_score", 0.5))
        importance_score = max(0.0, min(1.0, importance_score))  # 0.0-1.0 범위로 제한
        
        importance_level = result.get("importance_level", "medium")
        if importance_level not in ["low", "medium", "high", "urgent"]:
            importance_level = "medium"
        
        classification = result.get("classification", {})
        
        return {
            "importance_score": importance_score,
            "importance_level": importance_level,
            "classification": classification
        }
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Error parsing classification result: {e}")
        logger.error(f"Response content: {response[:500] if isinstance(response, str) else str(response)[:500]}")
        # 기본값 반환
        return {
            "importance_score": 0.5,
            "importance_level": "medium",
            "classification": {"category": "unknown"}
        }


def _log_token_usage(response, operation_name: str = "LLM invoke"):
    """
    토큰 사용량 정보를 logger.debug로 로깅
    
    Args:
        response: LLM 응답 객체
        operation_name: 작업 이름 (로깅용)
    """
    try:
        # LangChain 1.0: response_metadata에서 토큰 정보 가져오기
        response_metadata = getattr(response, "response_metadata", {})
        token_usage = response_metadata.get("token_usage", {})
        
        if token_usage:
            prompt_tokens = token_usage.get("prompt_tokens", 0)
            completion_tokens = token_usage.get("completion_tokens", 0)
            total_tokens = token_usage.get("total_tokens", 0)
            
            logger.debug(
                f"[{operation_name}] Token usage - "
                f"Prompt: {prompt_tokens}, "
                f"Completion: {completion_tokens}, "
                f"Total: {total_tokens}"
            )
        else:
            logger.debug(f"[{operation_name}] Token usage information not available")
    except Exception as e:
        logger.debug(f"[{operation_name}] Error logging token usage: {e}")


def _format_metadata(metadata: dict) -> str:
    """
    메타데이터를 읽기 쉬운 문자열로 변환
    
    Args:
        metadata: 메타데이터 딕셔너리
        
    Returns:
        포맷된 문자열
    """
    if not metadata:
        return "없음"
    
    lines = []
    for key, value in metadata.items():
        if value is None:
            continue
        
        # 리스트나 딕셔너리는 JSON 문자열로 변환
        if isinstance(value, (list, dict)):
            value_str = json.dumps(value, ensure_ascii=False)
        else:
            value_str = str(value)
        
        lines.append(f"- {key}: {value_str}")
    
    return "\n".join(lines) if lines else "없음"
