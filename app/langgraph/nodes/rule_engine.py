"""Rule Engine Node."""

from loguru import logger
from typing import Dict, Any

from app.langgraph.state import EmailProcessingState


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
        logger.error(f"Error in rule engine for email {state['email_id']}: {e}", exc_info=True)
        # 실패 시 기본값 설정
        state["rule_applied"] = None
        state["auto_action"] = "none"
        state["action_details"] = {}
        state["errors"].append({
            "node": "rule_engine",
            "error": str(e),
            "timestamp": state["started_at"].isoformat() if state.get("started_at") else None
        })
        state["current_node"] = "rule_engine"
        state["completed_nodes"].append("rule_engine")
    
    return state


def _evaluate_rules(state: EmailProcessingState) -> Dict[str, Any]:
    """
    규칙 평가 및 자동 액션 결정
    
    Args:
        state: EmailProcessingState
        
    Returns:
        {
            "rule_applied": str,  # 적용된 규칙 이름
            "auto_action": str,    # "delete", "archive", "tag", "move", "none"
            "action_details": dict  # 액션 상세 정보
        }
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
