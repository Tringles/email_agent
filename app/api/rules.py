"""User Rule API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.repositories.user_rule_repo import UserRuleRepository
from app.db.repositories.email_repo import EmailRepository
from app.schemas.user_rule_schema import (
    UserRuleCreate,
    UserRuleUpdate,
    UserRuleResponse,
    CreateRuleFromEmailRequest
)
from app.models.user_rule import RuleType, RuleAction
from app.models.user import User
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


@router.post("", response_model=UserRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    rule_data: UserRuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user rule.
    
    규칙 타입에 따라 필요한 필드가 다릅니다:
    - similarity_based: reference_email_id, similarity_threshold 필수
    - metadata_based: 하나 이상의 메타데이터 필터 필수
    - classification_based: classification_category 또는 classification_tags 필수
    """
    rule_repo = UserRuleRepository(db)
    
    # Similarity-based rule validation
    if rule_data.rule_type == RuleType.SIMILARITY_BASED:
        if not rule_data.reference_email_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="reference_email_id is required for similarity-based rules"
            )
        if rule_data.similarity_threshold is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="similarity_threshold is required for similarity-based rules"
            )
        
        # 예시 이메일이 존재하고 사용자 소유인지 확인
        email_repo = EmailRepository(db)
        email = email_repo.get_email_by_id(rule_data.reference_email_id, current_user.id)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reference email not found or access denied"
            )
    
    # Create rule
    rule = rule_repo.create_rule(
        user_id=current_user.id,
        rule_name=rule_data.rule_name,
        rule_type=rule_data.rule_type,
        action=rule_data.action,
        reference_email_id=rule_data.reference_email_id,
        similarity_threshold=rule_data.similarity_threshold,
        sender_filter=rule_data.sender_filter,
        sender_pattern=rule_data.sender_pattern,
        subject_keywords=rule_data.subject_keywords,
        subject_pattern=rule_data.subject_pattern,
        category_filter=rule_data.category_filter,
        importance_level_filter=rule_data.importance_level_filter,
        folder_filter=rule_data.folder_filter,
        has_attachments_filter=rule_data.has_attachments_filter,
        classification_category=rule_data.classification_category,
        classification_tags=rule_data.classification_tags,
        action_details=rule_data.action_details,
        priority=rule_data.priority,
        description=rule_data.description,
    )
    
    return UserRuleResponse(**rule.to_dict())


@router.post("/from-email/{email_id}", response_model=UserRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule_from_email(
    email_id: int,
    rule_data: CreateRuleFromEmailRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a similarity-based rule from an email.
    
    "이런 메일 삭제" 같은 요청을 처리합니다.
    지정한 이메일과 유사한 이메일들에 대해 규칙을 적용합니다.
    """
    # 이메일 존재 및 소유권 확인
    email_repo = EmailRepository(db)
    email = email_repo.get_email_by_id(email_id, current_user.id)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found or access denied"
        )
    
    # Vector DB ID 확인
    if not email.vector_db_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email has not been processed by AI agent yet. Please process the email first."
        )
    
    # Similarity-based rule 생성
    rule_repo = UserRuleRepository(db)
    rule = rule_repo.create_rule(
        user_id=current_user.id,
        rule_name=rule_data.rule_name,
        rule_type=RuleType.SIMILARITY_BASED,
        action=rule_data.action,
        reference_email_id=email_id,
        similarity_threshold=rule_data.similarity_threshold,
        action_details=rule_data.action_details,
        priority=rule_data.priority,
        description=rule_data.description or f"Similar to email: {email.subject}",
    )
    
    return UserRuleResponse(**rule.to_dict())


@router.get("", response_model=List[UserRuleResponse])
async def get_rules(
    is_active: Optional[bool] = None,
    rule_type: Optional[RuleType] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all rules for the current user.
    
    Args:
        is_active: Filter by active status (optional)
        rule_type: Filter by rule type (optional)
    """
    rule_repo = UserRuleRepository(db)
    rules = rule_repo.get_rules_by_user(
        user_id=current_user.id,
        is_active=is_active,
        rule_type=rule_type
    )
    
    return [UserRuleResponse(**rule.to_dict()) for rule in rules]


@router.get("/{rule_id}", response_model=UserRuleResponse)
async def get_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific rule by ID."""
    rule_repo = UserRuleRepository(db)
    rule = rule_repo.get_rule_by_id(rule_id, current_user.id)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    return UserRuleResponse(**rule.to_dict())


@router.put("/{rule_id}", response_model=UserRuleResponse)
async def update_rule(
    rule_id: int,
    rule_data: UserRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a rule."""
    rule_repo = UserRuleRepository(db)
    
    # Update only provided fields
    update_dict = rule_data.dict(exclude_unset=True)
    rule = rule_repo.update_rule(rule_id, current_user.id, **update_dict)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    return UserRuleResponse(**rule.to_dict())


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a rule."""
    rule_repo = UserRuleRepository(db)
    deleted = rule_repo.delete_rule(rule_id, current_user.id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    return None


@router.post("/{rule_id}/toggle", response_model=UserRuleResponse)
async def toggle_rule_active(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle rule active status."""
    rule_repo = UserRuleRepository(db)
    rule = rule_repo.toggle_rule_active(rule_id, current_user.id)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    return UserRuleResponse(**rule.to_dict())

