"""공통 에러 처리 유틸리티."""

import time

from loguru import logger
from functools import wraps
from typing import Callable, Any, Optional, Dict

from app.langgraph.state import EmailProcessingState


def handle_node_error(
    state: EmailProcessingState,
    node_name: str,
    error: Exception,
    default_values: Optional[Dict[str, Any]] = None,
    continue_on_error: bool = True
) -> None:
    """
    노드 에러를 state에 기록하고 기본값 설정
    
    Args:
        state: EmailProcessingState
        node_name: 노드 이름
        error: 발생한 에러
        default_values: 에러 발생 시 설정할 기본값
        continue_on_error: 에러 발생 시에도 다음 노드로 진행할지 여부
    """
    error_info = {
        "node": node_name,
        "error": str(error),
        "error_type": type(error).__name__,
        "timestamp": state["started_at"].isoformat() if state.get("started_at") else None
    }
    
    state["errors"].append(error_info)
    state["current_node"] = node_name
    
    # 기본값 설정
    if default_values:
        for key, value in default_values.items():
            state[key] = value
    
    # 완료된 노드로 표시 (에러가 있어도 다음 노드로 진행 가능)
    if continue_on_error:
        if node_name not in state["completed_nodes"]:
            state["completed_nodes"].append(node_name)
    
    logger.error(
        f"Error in {node_name} for email {state['email_id']}: {error}",
        exc_info=True
    )


def retry_on_error(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    retryable_exceptions: tuple = (Exception,),
    backoff_factor: float = 2.0
):
    """
    재시도 데코레이터
    
    Args:
        max_retries: 최대 재시도 횟수
        retry_delay: 초기 재시도 지연 시간 (초)
        retryable_exceptions: 재시도할 예외 타입
        backoff_factor: 지수 백오프 팩터
    
    Usage:
        @retry_on_error(max_retries=3, retry_delay=1.0)
        def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = retry_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {current_delay:.2f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
            
            # 모든 재시도 실패 시 예외 재발생
            raise last_exception
        
        return wrapper
    return decorator


def is_retryable_error(error: Exception) -> bool:
    """
    에러가 재시도 가능한지 판단
    
    Args:
        error: 발생한 에러
        
    Returns:
        재시도 가능 여부
    """
    # 재시도 가능한 에러 타입
    retryable_types = (
        ConnectionError,
        TimeoutError,
        OSError,
    )
    
    # 재시도 가능한 에러 메시지 패턴
    retryable_patterns = (
        "rate limit",
        "timeout",
        "connection",
        "temporary",
        "service unavailable",
        "503",
        "502",
        "429",
    )
    
    error_str = str(error).lower()
    
    # 타입 체크
    if isinstance(error, retryable_types):
        return True
    
    # 메시지 패턴 체크
    if any(pattern in error_str for pattern in retryable_patterns):
        return True
    
    return False


def get_error_severity(error: Exception) -> str:
    """
    에러 심각도 판단
    
    Args:
        error: 발생한 에러
        
    Returns:
        "critical", "high", "medium", "low"
    """
    # Critical: 데이터 손실, 권한 문제 등
    critical_types = (
        PermissionError,
        ValueError,  # 잘못된 데이터
    )
    
    # High: 외부 서비스 실패 등
    high_types = (
        ConnectionError,
        TimeoutError,
    )
    
    if isinstance(error, critical_types):
        return "critical"
    elif isinstance(error, high_types):
        return "high"
    else:
        return "medium"

