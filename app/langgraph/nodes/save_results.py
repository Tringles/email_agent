"""Save Results Node - Exit Node."""

from loguru import logger
from datetime import datetime

from app.langgraph.state import EmailProcessingState
from app.models.email import EmailStatus, ImportanceLevel
from app.db.repositories.email_repo import EmailRepository


def save_results_node(state: EmailProcessingState) -> EmailProcessingState:
    """
    Exit Node: 처리 결과를 DB에 저장하고 상태 업데이트
    
    Args:
        state: EmailProcessingState
        
    Returns:
        업데이트된 EmailProcessingState
    """
    try:
        logger.info(f"Saving results for email {state['email_id']}")
        
        db = state["db_session"]
        email_repo = EmailRepository(db)
        
        # 이메일 조회
        email = email_repo.get_email_by_id(state["email_id"], state["user_id"])
        if not email:
            raise ValueError(f"Email {state['email_id']} not found")
        
        # 처리 결과 업데이트
        update_data = {
            "status": EmailStatus.PROCESSED,
            "is_processed": True,
            "processed_at": datetime.now(),
            "summary": state.get("summary"),
            "importance_score": state.get("importance_score"),
            "importance_level": _parse_importance_level(state.get("importance_level")),
            "classification": state.get("classification"),
            "vector_db_id": state.get("vector_db_id"),
            "embedding_model": state.get("embedding_model"),
            "rule_applied": state.get("rule_applied"),
            "auto_action": state.get("auto_action"),
        }
        
        # None 값 제거
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        # 이메일 업데이트
        email = email_repo.update_email(email, **update_data)
        
        # 자동 액션 적용
        _apply_auto_action(email, state, email_repo)
        
        state["completed_at"] = datetime.now()
        state["current_node"] = "save_results"
        state["completed_nodes"].append("save_results")
        
        logger.info(f"Results saved successfully for email {state['email_id']}")
        
    except Exception as e:
        logger.error(f"Error saving results for email {state['email_id']}: {e}", exc_info=True)
        
        # 이메일 상태를 FAILED로 변경
        try:
            db = state["db_session"]
            email_repo = EmailRepository(db)
            email = email_repo.get_email_by_id(state["email_id"], state["user_id"])
            if email:
                email.status = EmailStatus.FAILED
                email.is_processed = False
                db.commit()
        except Exception as save_error:
            logger.error(f"Error marking email as failed: {save_error}")
        
        state["errors"].append({
            "node": "save_results",
            "error": str(e),
            "timestamp": state["started_at"].isoformat() if state.get("started_at") else None
        })
        state["completed_at"] = datetime.now()
        state["current_node"] = "save_results"
        state["completed_nodes"].append("save_results")
        
        # 에러를 다시 발생시켜서 그래프가 실패로 처리되도록
        raise
    
    return state


def _parse_importance_level(level: str) -> ImportanceLevel:
    """
    중요도 레벨 문자열을 Enum으로 변환
    
    Args:
        level: "low", "medium", "high", "urgent"
        
    Returns:
        ImportanceLevel Enum
    """
    if not level:
        return None
    
    level_lower = level.lower()
    try:
        return ImportanceLevel(level_lower)
    except ValueError:
        logger.warning(f"Invalid importance level: {level}, defaulting to medium")
        return ImportanceLevel.MEDIUM


def _apply_auto_action(email, state: EmailProcessingState, email_repo: EmailRepository):
    """
    자동 액션 적용
    
    Args:
        email: Email 모델 인스턴스
        state: EmailProcessingState
        email_repo: EmailRepository
    """
    auto_action = state.get("auto_action")
    action_details = state.get("action_details", {})
    
    if not auto_action or auto_action == "none":
        return
    
    try:
        if auto_action == "delete":
            # 삭제는 실제로는 아카이브로 처리 (데이터 보존)
            email.is_deleted = True
            logger.info(f"Auto-deleted email {email.id} (marked as deleted)")
            
        elif auto_action == "archive":
            email.is_archived = True
            logger.info(f"Auto-archived email {email.id}")
            
        elif auto_action == "tag":
            # 태그는 classification에 저장되므로 별도 처리 불필요
            # 중요 표시는 별도로 처리
            tags = action_details.get("tags", [])
            if "important" in tags:
                email.is_important = True
                logger.info(f"Auto-marked email {email.id} as important")
            
        elif auto_action == "move":
            # 폴더 이동은 추후 구현 (현재는 로그만)
            logger.info(f"Auto-move requested for email {email.id}, but not implemented yet")
        
        # 변경사항 저장
        email_repo.db.commit()
        
    except Exception as e:
        logger.error(f"Error applying auto action {auto_action} for email {email.id}: {e}")
