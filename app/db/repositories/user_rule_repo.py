"""User Rule repository for database operations."""

from loguru import logger
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.models.user_rule import UserRule, RuleType, RuleAction


class UserRuleRepository:
    """Repository for user rule database operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_rule(
        self,
        user_id: int,
        rule_name: str,
        rule_type: RuleType,
        action: RuleAction,
        **kwargs
    ) -> UserRule:
        """
        Create a new user rule.

        Args:
            user_id: User ID
            rule_name: Rule name
            rule_type: Rule type
            action: Rule action
            **kwargs: Additional rule fields

        Returns:
            Created UserRule object
        """
        rule = UserRule(
            user_id=user_id,
            rule_name=rule_name,
            rule_type=rule_type,
            action=action,
            reference_email_id=kwargs.get("reference_email_id"),
            similarity_threshold=kwargs.get("similarity_threshold"),
            sender_filter=kwargs.get("sender_filter"),
            sender_pattern=kwargs.get("sender_pattern"),
            subject_keywords=kwargs.get("subject_keywords"),
            subject_pattern=kwargs.get("subject_pattern"),
            category_filter=kwargs.get("category_filter"),
            importance_level_filter=kwargs.get("importance_level_filter"),
            folder_filter=kwargs.get("folder_filter"),
            has_attachments_filter=kwargs.get("has_attachments_filter"),
            classification_category=kwargs.get("classification_category"),
            classification_tags=kwargs.get("classification_tags"),
            action_details=kwargs.get("action_details", {}),
            priority=kwargs.get("priority", 0),
            description=kwargs.get("description"),
            is_active=kwargs.get("is_active", True),
        )

        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)

        logger.info(f"Created user rule: {rule.id} for user {user_id}")
        return rule

    def get_rule_by_id(self, rule_id: int, user_id: int) -> Optional[UserRule]:
        """
        Get a rule by ID (with user ownership check).

        Args:
            rule_id: Rule ID
            user_id: User ID (for ownership check)

        Returns:
            UserRule object or None
        """
        return self.db.query(UserRule).filter(
            UserRule.id == rule_id,
            UserRule.user_id == user_id
        ).first()

    def get_rules_by_user(
        self,
        user_id: int,
        is_active: Optional[bool] = None,
        rule_type: Optional[RuleType] = None
    ) -> List[UserRule]:
        """
        Get all rules for a user.

        Args:
            user_id: User ID
            is_active: Filter by active status (optional)
            rule_type: Filter by rule type (optional)

        Returns:
            List of UserRule objects
        """
        query = self.db.query(UserRule).filter(
            UserRule.user_id == user_id
        )

        if is_active is not None:
            query = query.filter(UserRule.is_active == is_active)

        if rule_type is not None:
            query = query.filter(UserRule.rule_type == rule_type)

        # 우선순위 순으로 정렬 (높은 우선순위가 먼저)
        query = query.order_by(desc(UserRule.priority), desc(UserRule.created_at))

        return query.all()

    def get_active_rules_by_user(
        self,
        user_id: int,
        rule_type: Optional[RuleType] = None
    ) -> List[UserRule]:
        """
        Get active rules for a user (ordered by priority).

        Args:
            user_id: User ID
            rule_type: Filter by rule type (optional)

        Returns:
            List of active UserRule objects
        """
        return self.get_rules_by_user(
            user_id=user_id,
            is_active=True,
            rule_type=rule_type
        )

    def update_rule(
        self,
        rule_id: int,
        user_id: int,
        **kwargs
    ) -> Optional[UserRule]:
        """
        Update a rule.

        Args:
            rule_id: Rule ID
            user_id: User ID (for ownership check)
            **kwargs: Fields to update

        Returns:
            Updated UserRule object or None
        """
        rule = self.get_rule_by_id(rule_id, user_id)
        if not rule:
            return None

        # 업데이트 가능한 필드들
        updatable_fields = [
            "rule_name", "rule_type", "action", "is_active",
            "reference_email_id", "similarity_threshold",
            "sender_filter", "sender_pattern",
            "subject_keywords", "subject_pattern",
            "category_filter", "importance_level_filter",
            "folder_filter", "has_attachments_filter",
            "classification_category", "classification_tags",
            "action_details", "priority", "description"
        ]

        for field in updatable_fields:
            if field in kwargs:
                setattr(rule, field, kwargs[field])

        self.db.commit()
        self.db.refresh(rule)

        logger.info(f"Updated user rule: {rule_id}")
        return rule

    def delete_rule(self, rule_id: int, user_id: int) -> bool:
        """
        Delete a rule.

        Args:
            rule_id: Rule ID
            user_id: User ID (for ownership check)

        Returns:
            True if deleted, False otherwise
        """
        rule = self.get_rule_by_id(rule_id, user_id)
        if not rule:
            return False

        self.db.delete(rule)
        self.db.commit()

        logger.info(f"Deleted user rule: {rule_id}")
        return True

    def toggle_rule_active(self, rule_id: int, user_id: int) -> Optional[UserRule]:
        """
        Toggle rule active status.

        Args:
            rule_id: Rule ID
            user_id: User ID (for ownership check)

        Returns:
            Updated UserRule object or None
        """
        rule = self.get_rule_by_id(rule_id, user_id)
        if not rule:
            return None

        rule.is_active = not rule.is_active
        self.db.commit()
        self.db.refresh(rule)

        logger.info(f"Toggled rule {rule_id} active status to {rule.is_active}")
        return rule

