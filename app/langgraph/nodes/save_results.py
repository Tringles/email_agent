"""Save Results Node - Exit Node."""

from loguru import logger
from typing import Dict, Any
from datetime import datetime

from app.langgraph.state import EmailProcessingState
from app.models.email import EmailStatus, ImportanceLevel
from app.db.repositories.email_repo import EmailRepository
from app.db.session import SessionLocal


def save_results_node(state: EmailProcessingState) -> EmailProcessingState:
    """
    Exit Node: 처리 결과를 DB에 저장하고 상태 업데이트
    
    이 노드는 파이프라인의 종료점으로, 최종 상태를 검증하고
    처리 결과를 DB에 저장하며 결과 요약을 로깅합니다.
    
    Args:
        state: EmailProcessingState
        
    Returns:
        업데이트된 EmailProcessingState
    """
    db = None
    try:
        logger.info(f"Saving results for email {state['email_id']}")
        
        # 최종 상태 검증
        validation_result = _validate_final_state(state)
        if not validation_result["valid"]:
            logger.warning(
                f"State validation warnings for email {state['email_id']}: "
                f"{validation_result['warnings']}"
            )
        
        # 새로운 DB 세션 생성 (state에 포함하지 않으므로)
        db = SessionLocal()
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
        
        # 변경사항 커밋
        db.commit()
        
        state["completed_at"] = datetime.now()
        state["current_node"] = "save_results"
        state["completed_nodes"].append("save_results")
        
        # 결과 요약 로깅
        _log_processing_summary(state, validation_result)
        
        logger.info(f"Results saved successfully for email {state['email_id']}")
        
    except Exception as e:
        logger.error(f"Error saving results for email {state['email_id']}: {e}", exc_info=True)
        
        # 이메일 상태를 FAILED로 변경
        error_db = None
        try:
            if db is None:
                error_db = SessionLocal()
            else:
                error_db = db
            email_repo = EmailRepository(error_db)
            email = email_repo.get_email_by_id(state["email_id"], state["user_id"])
            if email:
                email.status = EmailStatus.FAILED
                email.is_processed = False
                error_db.commit()
        except Exception as save_error:
            logger.error(f"Error marking email as failed: {save_error}")
        finally:
            if error_db and error_db != db:
                error_db.close()
        
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
    finally:
        # DB 세션 정리 (성공/실패 모두)
        if db:
            db.close()
    
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


def _validate_final_state(state: EmailProcessingState) -> Dict[str, Any]:
    """
    최종 상태 검증
    
    Args:
        state: EmailProcessingState
        
    Returns:
        {
            "valid": bool,
            "warnings": List[str]
        }
    """
    warnings = []
    
    # 필수 필드 검증
    if not state.get("email_data"):
        warnings.append("email_data is missing")
    
    # 처리 결과 검증
    if not state.get("summary"):
        warnings.append("summary is missing")
    
    if state.get("importance_level") is None:
        warnings.append("importance_level is missing")
    
    if state.get("classification") is None:
        warnings.append("classification is missing")
    
    # 에러 확인
    if state.get("errors"):
        warnings.append(f"Processing had {len(state['errors'])} errors")
    
    # 완료된 노드 확인
    expected_nodes = ["load_email", "preprocess_html", "summarize", "classify", "vector_search", "rule_engine"]
    completed_nodes = state.get("completed_nodes", [])
    missing_nodes = [node for node in expected_nodes if node not in completed_nodes]
    if missing_nodes:
        warnings.append(f"Missing completed nodes: {missing_nodes}")
    
    return {
        "valid": len(warnings) == 0,
        "warnings": warnings
    }


def _log_processing_summary(state: EmailProcessingState, validation_result: Dict[str, Any]):
    """
    처리 결과 요약 로깅
    
    Args:
        state: EmailProcessingState
        validation_result: _validate_final_state 결과
    """
    email_id = state["email_id"]
    processing_time = None
    if state.get("started_at") and state.get("completed_at"):
        processing_time = (state["completed_at"] - state["started_at"]).total_seconds()
    
    expected_nodes_count = 6  # load_email, preprocess_html, summarize, classify, vector_search, rule_engine
    summary_lines = [
        f"=== Email Processing Summary (ID: {email_id}) ===",
        f"Processing time: {processing_time:.2f}s" if processing_time else "Processing time: N/A",
        f"Completed nodes: {len(state.get('completed_nodes', []))}/{expected_nodes_count}",
        f"Errors: {len(state.get('errors', []))}",
        f"Summary: {'Generated' if state.get('summary') else 'Missing'}",
        f"Importance level: {state.get('importance_level', 'N/A')}",
        f"Importance score: {state.get('importance_score', 'N/A')}",
        f"Classification: {state.get('classification', {}).get('category', 'N/A') if state.get('classification') else 'N/A'}",
        f"Vector DB ID: {state.get('vector_db_id', 'N/A')}",
        f"Rule applied: {state.get('rule_applied', 'N/A')}",
        f"Auto action: {state.get('auto_action', 'none')}",
    ]
    
    if validation_result["warnings"]:
        summary_lines.append(f"Validation warnings: {', '.join(validation_result['warnings'])}")
    
    if state.get("errors"):
        summary_lines.append("Errors:")
        for error in state["errors"]:
            summary_lines.append(f"  - [{error.get('node', 'unknown')}]: {error.get('error', 'unknown error')}")
    
    summary_lines.append("=" * 50)
    
    logger.info("\n".join(summary_lines))


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
