"""User Rule model for storing user-defined email processing rules."""

import enum
from datetime import datetime
from sqlalchemy.sql import func
from typing import Optional, Dict, Any
from sqlalchemy.orm import relationship
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text

from app.db.session import Base


class RuleType(str, enum.Enum):
    """Rule type enumeration."""
    SIMILARITY_BASED = "similarity_based"  # Vector DB 유사도 기반
    METADATA_BASED = "metadata_based"  # 메타데이터 기반 (발신자, 제목 등)
    CLASSIFICATION_BASED = "classification_based"  # 분류 결과 기반


class RuleAction(str, enum.Enum):
    """Rule action enumeration."""
    DELETE = "delete"
    ARCHIVE = "archive"
    TAG = "tag"
    MOVE = "move"
    MARK_READ = "mark_read"
    MARK_IMPORTANT = "mark_important"


class UserRule(Base):
    """
    User-defined email processing rule.
    
    사용자가 정의한 이메일 처리 규칙을 저장합니다.
    Vector DB 유사도 검색 또는 메타데이터 필터를 사용하여 규칙을 매칭합니다.
    """

    __tablename__ = "user_rules"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to User
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Rule basic information
    rule_name = Column(String(255), nullable=False)  # 규칙 이름
    rule_type = Column(
        Enum(RuleType),
        nullable=False,
        index=True
    )  # 규칙 타입
    action = Column(
        Enum(RuleAction),
        nullable=False
    )  # 적용할 액션

    # Rule status
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # 활성화 여부

    # === Vector DB 기반 규칙 (similarity_based) ===
    reference_email_id = Column(
        Integer,
        ForeignKey("emails.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )  # 예시 이메일 ID (이 이메일과 유사한 이메일 찾기)
    similarity_threshold = Column(
        Float,
        nullable=True
    )  # 유사도 임계값 (0.0~1.0, 낮을수록 유사)

    # === 메타데이터 기반 규칙 (metadata_based) ===
    sender_filter = Column(String(255), nullable=True)  # 발신자 필터 (정확 일치 또는 패턴)
    sender_pattern = Column(String(255), nullable=True)  # 발신자 패턴 (정규식)
    subject_keywords = Column(JSON, nullable=True)  # 제목 키워드 리스트 (모두 포함 또는 하나라도 포함)
    subject_pattern = Column(String(255), nullable=True)  # 제목 패턴 (정규식)
    category_filter = Column(String(50), nullable=True)  # 카테고리 필터 (work, personal, newsletter 등)
    importance_level_filter = Column(String(50), nullable=True)  # 중요도 레벨 필터 (low, medium, high, urgent)
    folder_filter = Column(String(100), nullable=True)  # 폴더 필터
    has_attachments_filter = Column(Boolean, nullable=True)  # 첨부파일 여부 필터

    # === 분류 기반 규칙 (classification_based) ===
    classification_category = Column(String(50), nullable=True)  # 분류 카테고리
    classification_tags = Column(JSON, nullable=True)  # 분류 태그 리스트

    # === 액션 상세 정보 ===
    action_details = Column(JSON, nullable=True)  # 액션 상세 정보
    # 예시:
    # - tag: {"tags": ["important", "work"]}
    # - move: {"folder": "Archive"}
    # - mark_important: {"is_important": true}

    # === 규칙 우선순위 ===
    priority = Column(Integer, default=0, nullable=False)  # 우선순위 (높을수록 먼저 평가)

    # === 규칙 설명 ===
    description = Column(Text, nullable=True)  # 규칙 설명

    # Metadata
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    user = relationship("User", backref="user_rules")
    reference_email = relationship("Email", foreign_keys=[reference_email_id])

    def __repr__(self):
        return f"<UserRule(id={self.id}, user_id={self.user_id}, rule_name={self.rule_name}, rule_type={self.rule_type}, action={self.action})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "rule_name": self.rule_name,
            "rule_type": self.rule_type.value if self.rule_type else None,
            "action": self.action.value if self.action else None,
            "is_active": self.is_active,
            "reference_email_id": self.reference_email_id,
            "similarity_threshold": self.similarity_threshold,
            "sender_filter": self.sender_filter,
            "sender_pattern": self.sender_pattern,
            "subject_keywords": self.subject_keywords,
            "subject_pattern": self.subject_pattern,
            "category_filter": self.category_filter,
            "importance_level_filter": self.importance_level_filter,
            "folder_filter": self.folder_filter,
            "has_attachments_filter": self.has_attachments_filter,
            "classification_category": self.classification_category,
            "classification_tags": self.classification_tags,
            "action_details": self.action_details,
            "priority": self.priority,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

