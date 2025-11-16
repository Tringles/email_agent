"""Summarize Node."""

from loguru import logger

from app.core.config import settings
from app.langgraph.state import EmailProcessingState
from app.services.llm_service import get_llm_service
from app.langgraph.utils.email_text_processing import prepare_email_content_for_llm


def summarize_node(state: EmailProcessingState) -> EmailProcessingState:
    """
    이메일 본문을 LLM으로 요약
    
    Args:
        state: EmailProcessingState
        
    Returns:
        업데이트된 EmailProcessingState
    """
    try:
        logger.info(f"Summarizing email {state['email_id']}")
        
        # OpenAI API 키 확인
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set, skipping summarization")
            state["summary"] = None
            state["current_node"] = "summarize"
            state["completed_nodes"].append("summarize")
            return state
        
        # 본문 텍스트 선택 (processed_body_html 우선, 없으면 body_text)
        body_text = state.get("processed_body_html") or state["email_data"].get("body_text", "")
        
        if not body_text or len(body_text.strip()) == 0:
            logger.warning(f"No body text found for email {state['email_id']}")
            state["summary"] = None
            state["current_node"] = "summarize"
            state["completed_nodes"].append("summarize")
            return state
        
        # 제목 정보
        subject = state["email_data"].get("subject", "")
        
        model = settings.OPENAI_MODEL
        max_tokens = 8000  # 시스템 프롬프트와 응답 공간을 제외한 입력 토큰
        email_content = prepare_email_content_for_llm(
            body_text=body_text,
            subject=subject,
            model=model,
            max_tokens=max_tokens
        )
        
        # LLM으로 요약 생성
        summary = _generate_summary(email_content)
        
        state["summary"] = summary
        state["current_node"] = "summarize"
        state["completed_nodes"].append("summarize")
        
        logger.info(f"Summary generated for email {state['email_id']}")
        
    except Exception as e:
        logger.error(f"Error summarizing email {state['email_id']}: {e}", exc_info=True)
        # 요약 실패해도 다음 노드로 진행
        state["summary"] = None
        state["errors"].append({
            "node": "summarize",
            "error": str(e),
            "timestamp": state["started_at"].isoformat() if state.get("started_at") else None
        })
        state["current_node"] = "summarize"
        state["completed_nodes"].append("summarize")
    
    return state


def _generate_summary(email_content: str, max_length: int = 500) -> str:
    """
    LLM을 사용하여 이메일 요약 생성
    
    Args:
        email_content: 이메일 내용 (제목 + 본문, 이미 토큰 기반으로 잘라냄)
        max_length: 최대 요약 길이
        
    Returns:
        요약 텍스트
    """
    # LLM 서비스 가져오기
    llm_service = get_llm_service(temperature=0.3, max_tokens=200)
    
    # 프롬프트 템플릿 생성
    prompt_template = llm_service.create_prompt_template(
        system_prompt_name="summarize_system",
        human_template="{email_content}"
    )
    
    # 프롬프트 실행 (email_content는 이미 토큰 기반으로 잘라냄)
    summary = llm_service.invoke(
        prompt_template=prompt_template,
        input_variables={
            "email_content": email_content,  # 이미 토큰 기반으로 잘라낸 내용
            "max_length": max_length
        },
        operation_name="Summarize"
    )
    
    # 길이 제한
    if len(summary) > max_length:
        summary = summary[:max_length] + "..."
    
    return summary
