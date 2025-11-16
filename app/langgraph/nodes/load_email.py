"""Load Email Node - Entry Node."""

from loguru import logger

from app.langgraph.state import EmailProcessingState


def load_email_node(state: EmailProcessingState) -> EmailProcessingState:
    """
    Entry Node: 이메일 존재 여부 확인 및 검증
    
    Note: State는 Agent Service에서 이미 초기화되어 있음
    이 노드는 이메일이 존재하는지 확인하고 검증만 수행
    
    Args:
        state: EmailProcessingState (이미 초기화됨)
        
    Returns:
        업데이트된 EmailProcessingState
    """
    email_id = state["email_id"]
    user_id = state["user_id"]
    
    logger.info(f"Loading email {email_id} for user {user_id}")
    
    # 이메일 데이터가 이미 로드되어 있는지 확인
    if not state.get("email_data"):
        error_msg = f"Email {email_id} not found or not accessible"
        logger.error(error_msg)
        state["errors"].append({
            "node": "load_email",
            "error": error_msg,
            "timestamp": state["started_at"].isoformat() if state.get("started_at") else None
        })
        raise ValueError(error_msg)
    
    # 이메일이 해당 사용자의 것인지 확인 (추가 검증)
    # Note: Agent Service에서 이미 검증했을 것으로 가정
    
    state["current_node"] = "load_email"
    state["completed_nodes"].append("load_email")
    
    logger.info(f"Email {email_id} loaded successfully")
    
    return state

