"""State 검증 헬퍼 함수."""

from typing import Dict, Any, List, Optional
from loguru import logger

from app.langgraph.state import EmailProcessingState


def validate_basic_state(state: EmailProcessingState) -> Dict[str, Any]:
    """
    기본 상태 검증 (필수 필드)
    
    Args:
        state: EmailProcessingState
        
    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str]
        }
    """
    errors = []
    warnings = []
    
    # 필수 필드 검증
    if not isinstance(state.get("email_id"), int) or state.get("email_id") is None:
        errors.append("email_id is missing or invalid")
    
    if not isinstance(state.get("user_id"), int) or state.get("user_id") is None:
        errors.append("user_id is missing or invalid")
    
    if not isinstance(state.get("started_at"), type(None)) and state.get("started_at") is None:
        warnings.append("started_at is missing")
    
    if not isinstance(state.get("completed_nodes"), list):
        errors.append("completed_nodes must be a list")
    
    if not isinstance(state.get("errors"), list):
        errors.append("errors must be a list")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_node_prerequisites(
    state: EmailProcessingState,
    node_name: str,
    required_fields: List[str],
    optional_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    노드 실행 전 필수 필드 검증
    
    Args:
        state: EmailProcessingState
        node_name: 노드 이름
        required_fields: 필수 필드 리스트
        optional_fields: 선택적 필드 리스트 (경고만 발생)
        
    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str]
        }
    """
    errors = []
    warnings = []
    
    # 필수 필드 검증
    for field in required_fields:
        if field not in state or state[field] is None:
            errors.append(f"{field} is required for {node_name} node")
    
    # 선택적 필드 검증 (경고만)
    if optional_fields:
        for field in optional_fields:
            if field not in state or state[field] is None:
                warnings.append(f"{field} is missing (optional for {node_name} node)")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_email_data(email_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    email_data 검증
    
    Args:
        email_data: email_data 딕셔너리
        
    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str]
        }
    """
    errors = []
    warnings = []
    
    if not email_data:
        errors.append("email_data is missing")
        return {"valid": False, "errors": errors, "warnings": warnings}
    
    # 필수 필드 검증
    required_fields = ["subject", "sender", "recipient"]
    for field in required_fields:
        if field not in email_data or not email_data[field]:
            warnings.append(f"email_data.{field} is missing")
    
    # 본문 검증 (body_text 또는 body_html 중 하나는 있어야 함)
    if not email_data.get("body_text") and not email_data.get("body_html"):
        warnings.append("email_data: both body_text and body_html are missing")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_importance_score(score: Optional[float]) -> Dict[str, Any]:
    """
    importance_score 검증 (0.0-1.0 범위)
    
    Args:
        score: 중요도 점수
        
    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str]
        }
    """
    errors = []
    warnings = []
    
    if score is None:
        warnings.append("importance_score is None")
        return {"valid": True, "errors": errors, "warnings": warnings}
    
    if not isinstance(score, (int, float)):
        errors.append(f"importance_score must be a number, got {type(score)}")
        return {"valid": False, "errors": errors, "warnings": warnings}
    
    if score < 0.0 or score > 1.0:
        errors.append(f"importance_score must be between 0.0 and 1.0, got {score}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_importance_level(level: Optional[str]) -> Dict[str, Any]:
    """
    importance_level 검증
    
    Args:
        level: 중요도 레벨
        
    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str]
        }
    """
    errors = []
    warnings = []
    
    if level is None:
        warnings.append("importance_level is None")
        return {"valid": True, "errors": errors, "warnings": warnings}
    
    valid_levels = ["low", "medium", "high", "urgent"]
    if level not in valid_levels:
        errors.append(f"importance_level must be one of {valid_levels}, got {level}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_classification(classification: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    classification 검증
    
    Args:
        classification: 분류 딕셔너리
        
    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str]
        }
    """
    errors = []
    warnings = []
    
    if classification is None:
        warnings.append("classification is None")
        return {"valid": True, "errors": errors, "warnings": warnings}
    
    if not isinstance(classification, dict):
        errors.append(f"classification must be a dict, got {type(classification)}")
        return {"valid": False, "errors": errors, "warnings": warnings}
    
    # category 필드 검증
    if "category" not in classification:
        warnings.append("classification.category is missing")
    else:
        valid_categories = ["work", "personal", "newsletter", "notification", "spam", "other"]
        if classification["category"] not in valid_categories:
            warnings.append(
                f"classification.category should be one of {valid_categories}, "
                f"got {classification['category']}"
            )
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_node_output(
    state: EmailProcessingState,
    node_name: str,
    expected_fields: List[str]
) -> Dict[str, Any]:
    """
    노드 출력 검증 (노드 실행 후)
    
    Args:
        state: EmailProcessingState
        node_name: 노드 이름
        expected_fields: 노드가 설정해야 하는 필드 리스트
        
    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str]
        }
    """
    errors = []
    warnings = []
    
    for field in expected_fields:
        if field not in state:
            errors.append(f"{node_name} node should set {field}")
        elif state[field] is None:
            warnings.append(f"{node_name} node set {field} to None")
    
    # completed_nodes에 노드가 포함되어 있는지 확인
    if node_name not in state.get("completed_nodes", []):
        warnings.append(f"{node_name} not in completed_nodes")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_state_for_node(
    state: EmailProcessingState,
    node_name: str
) -> Dict[str, Any]:
    """
    특정 노드 실행을 위한 상태 검증 (노드별 필수 필드)
    
    Args:
        state: EmailProcessingState
        node_name: 노드 이름
        
    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str]
        }
    """
    # 기본 상태 검증
    basic_validation = validate_basic_state(state)
    if not basic_validation["valid"]:
        return basic_validation
    
    errors = basic_validation["errors"]
    warnings = basic_validation["warnings"]
    
    # 노드별 필수 필드 검증
    node_requirements = {
        "load_email": {
            "required": [],
            "optional": []
        },
        "preprocess_html": {
            "required": ["email_data"],
            "optional": []
        },
        "summarize": {
            "required": ["email_data"],
            "optional": ["processed_body_html"]
        },
        "classify": {
            "required": ["email_data"],
            "optional": ["summary"]
        },
        "vector_search": {
            "required": ["email_data"],
            "optional": ["summary", "classification"]
        },
        "rule_engine": {
            "required": ["email_data", "classification"],
            "optional": ["summary", "importance_level"]
        },
        "save_results": {
            "required": ["email_data"],
            "optional": ["summary", "importance_level", "classification"]
        }
    }
    
    if node_name in node_requirements:
        reqs = node_requirements[node_name]
        validation = validate_node_prerequisites(
            state=state,
            node_name=node_name,
            required_fields=reqs["required"],
            optional_fields=reqs.get("optional", [])
        )
        errors.extend(validation["errors"])
        warnings.extend(validation["warnings"])
        
        # email_data 상세 검증
        if "email_data" in reqs["required"]:
            email_validation = validate_email_data(state.get("email_data"))
            errors.extend(email_validation["errors"])
            warnings.extend(email_validation["warnings"])
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }

