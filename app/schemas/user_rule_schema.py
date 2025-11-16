"""User Rule API schemas."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime

from app.models.user_rule import RuleType, RuleAction


class UserRuleBase(BaseModel):
    """Base schema for user rule."""
    rule_name: str = Field(..., description="규칙 이름", max_length=255)
    rule_type: RuleType = Field(..., description="규칙 타입")
    action: RuleAction = Field(..., description="적용할 액션")
    description: Optional[str] = Field(None, description="규칙 설명")
    priority: int = Field(0, description="규칙 우선순위 (높을수록 먼저 평가)", ge=0)


class SimilarityBasedRuleCreate(UserRuleBase):
    """Schema for creating similarity-based rule."""
    rule_type: RuleType = Field(RuleType.SIMILARITY_BASED, description="규칙 타입")
    reference_email_id: int = Field(..., description="예시 이메일 ID")
    similarity_threshold: float = Field(
        ...,
        description="유사도 임계값 (0.0~1.0, 낮을수록 유사)",
        ge=0.0,
        le=1.0
    )
    action_details: Optional[Dict[str, Any]] = Field(None, description="액션 상세 정보")


class MetadataBasedRuleCreate(UserRuleBase):
    """Schema for creating metadata-based rule."""
    rule_type: RuleType = Field(RuleType.METADATA_BASED, description="규칙 타입")
    sender_filter: Optional[str] = Field(None, description="발신자 필터 (정확 일치)")
    sender_pattern: Optional[str] = Field(None, description="발신자 패턴 (정규식)")
    subject_keywords: Optional[List[str]] = Field(None, description="제목 키워드 리스트")
    subject_pattern: Optional[str] = Field(None, description="제목 패턴 (정규식)")
    category_filter: Optional[str] = Field(None, description="카테고리 필터")
    importance_level_filter: Optional[str] = Field(None, description="중요도 레벨 필터")
    folder_filter: Optional[str] = Field(None, description="폴더 필터")
    has_attachments_filter: Optional[bool] = Field(None, description="첨부파일 여부 필터")
    action_details: Optional[Dict[str, Any]] = Field(None, description="액션 상세 정보")


class ClassificationBasedRuleCreate(UserRuleBase):
    """Schema for creating classification-based rule."""
    rule_type: RuleType = Field(RuleType.CLASSIFICATION_BASED, description="규칙 타입")
    classification_category: Optional[str] = Field(None, description="분류 카테고리")
    classification_tags: Optional[List[str]] = Field(None, description="분류 태그 리스트")
    action_details: Optional[Dict[str, Any]] = Field(None, description="액션 상세 정보")


class UserRuleCreate(BaseModel):
    """Schema for creating user rule (union of all rule types)."""
    rule_name: str = Field(..., description="규칙 이름", max_length=255)
    rule_type: RuleType = Field(..., description="규칙 타입")
    action: RuleAction = Field(..., description="적용할 액션")
    description: Optional[str] = Field(None, description="규칙 설명")
    priority: int = Field(0, description="규칙 우선순위", ge=0)
    
    # Similarity-based fields
    reference_email_id: Optional[int] = Field(None, description="예시 이메일 ID")
    similarity_threshold: Optional[float] = Field(
        None,
        description="유사도 임계값 (0.0~1.0)",
        ge=0.0,
        le=1.0
    )
    
    # Metadata-based fields
    sender_filter: Optional[str] = Field(None, description="발신자 필터")
    sender_pattern: Optional[str] = Field(None, description="발신자 패턴 (정규식)")
    subject_keywords: Optional[List[str]] = Field(None, description="제목 키워드 리스트")
    subject_pattern: Optional[str] = Field(None, description="제목 패턴 (정규식)")
    category_filter: Optional[str] = Field(None, description="카테고리 필터")
    importance_level_filter: Optional[str] = Field(None, description="중요도 레벨 필터")
    folder_filter: Optional[str] = Field(None, description="폴더 필터")
    has_attachments_filter: Optional[bool] = Field(None, description="첨부파일 여부 필터")
    
    # Classification-based fields
    classification_category: Optional[str] = Field(None, description="분류 카테고리")
    classification_tags: Optional[List[str]] = Field(None, description="분류 태그 리스트")
    
    # Action details
    action_details: Optional[Dict[str, Any]] = Field(None, description="액션 상세 정보")

    @validator("reference_email_id")
    def validate_similarity_rule(cls, v, values):
        """Validate similarity-based rule fields."""
        if values.get("rule_type") == RuleType.SIMILARITY_BASED:
            if v is None:
                raise ValueError("reference_email_id is required for similarity-based rules")
            if values.get("similarity_threshold") is None:
                raise ValueError("similarity_threshold is required for similarity-based rules")
        return v


class UserRuleUpdate(BaseModel):
    """Schema for updating user rule."""
    rule_name: Optional[str] = Field(None, description="규칙 이름", max_length=255)
    rule_type: Optional[RuleType] = Field(None, description="규칙 타입")
    action: Optional[RuleAction] = Field(None, description="적용할 액션")
    is_active: Optional[bool] = Field(None, description="활성화 여부")
    description: Optional[str] = Field(None, description="규칙 설명")
    priority: Optional[int] = Field(None, description="규칙 우선순위", ge=0)
    
    # Similarity-based fields
    reference_email_id: Optional[int] = Field(None, description="예시 이메일 ID")
    similarity_threshold: Optional[float] = Field(
        None,
        description="유사도 임계값 (0.0~1.0)",
        ge=0.0,
        le=1.0
    )
    
    # Metadata-based fields
    sender_filter: Optional[str] = Field(None, description="발신자 필터")
    sender_pattern: Optional[str] = Field(None, description="발신자 패턴 (정규식)")
    subject_keywords: Optional[List[str]] = Field(None, description="제목 키워드 리스트")
    subject_pattern: Optional[str] = Field(None, description="제목 패턴 (정규식)")
    category_filter: Optional[str] = Field(None, description="카테고리 필터")
    importance_level_filter: Optional[str] = Field(None, description="중요도 레벨 필터")
    folder_filter: Optional[str] = Field(None, description="폴더 필터")
    has_attachments_filter: Optional[bool] = Field(None, description="첨부파일 여부 필터")
    
    # Classification-based fields
    classification_category: Optional[str] = Field(None, description="분류 카테고리")
    classification_tags: Optional[List[str]] = Field(None, description="분류 태그 리스트")
    
    # Action details
    action_details: Optional[Dict[str, Any]] = Field(None, description="액션 상세 정보")


class UserRuleResponse(BaseModel):
    """Schema for user rule response."""
    id: int
    user_id: int
    rule_name: str
    rule_type: str
    action: str
    is_active: bool
    reference_email_id: Optional[int]
    similarity_threshold: Optional[float]
    sender_filter: Optional[str]
    sender_pattern: Optional[str]
    subject_keywords: Optional[List[str]]
    subject_pattern: Optional[str]
    category_filter: Optional[str]
    importance_level_filter: Optional[str]
    folder_filter: Optional[str]
    has_attachments_filter: Optional[bool]
    classification_category: Optional[str]
    classification_tags: Optional[List[str]]
    action_details: Optional[Dict[str, Any]]
    priority: int
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreateRuleFromEmailRequest(BaseModel):
    """Schema for creating rule from email (similarity-based)."""
    rule_name: str = Field(..., description="규칙 이름", max_length=255)
    action: RuleAction = Field(..., description="적용할 액션")
    similarity_threshold: float = Field(
        0.3,
        description="유사도 임계값 (0.0~1.0, 낮을수록 유사)",
        ge=0.0,
        le=1.0
    )
    description: Optional[str] = Field(None, description="규칙 설명")
    priority: int = Field(0, description="규칙 우선순위", ge=0)
    action_details: Optional[Dict[str, Any]] = Field(None, description="액션 상세 정보")

