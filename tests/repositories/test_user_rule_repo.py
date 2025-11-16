"""User Rule Repository tests."""

import pytest

from app.db.repositories.user_rule_repo import UserRuleRepository
from app.models.user_rule import UserRule, RuleType, RuleAction


class TestUserRuleRepository:
    """User Rule Repository tests."""
    
    def test_create_rule_similarity_based(self, db, test_user, test_email):
        """Test creating similarity-based rule."""
        repo = UserRuleRepository(db)
        rule = repo.create_rule(
            user_id=test_user.id,
            rule_name="Test Similarity Rule",
            rule_type=RuleType.SIMILARITY_BASED,
            action=RuleAction.DELETE,
            reference_email_id=test_email.id,
            similarity_threshold=0.8,
            description="Test rule"
        )
        
        assert rule.id is not None
        assert rule.user_id == test_user.id
        assert rule.rule_name == "Test Similarity Rule"
        assert rule.rule_type == RuleType.SIMILARITY_BASED
        assert rule.action == RuleAction.DELETE
        assert rule.reference_email_id == test_email.id
        assert rule.similarity_threshold == 0.8
        assert rule.is_active is True
    
    def test_create_rule_metadata_based(self, db, test_user):
        """Test creating metadata-based rule."""
        repo = UserRuleRepository(db)
        rule = repo.create_rule(
            user_id=test_user.id,
            rule_name="Test Metadata Rule",
            rule_type=RuleType.METADATA_BASED,
            action=RuleAction.ARCHIVE,
            sender_filter="spam@example.com",
            subject_keywords=["spam", "advertisement"],
            priority=100
        )
        
        assert rule.id is not None
        assert rule.rule_type == RuleType.METADATA_BASED
        assert rule.action == RuleAction.ARCHIVE
        assert rule.sender_filter == "spam@example.com"
        assert rule.subject_keywords == ["spam", "advertisement"]
        assert rule.priority == 100
    
    def test_create_rule_classification_based(self, db, test_user):
        """Test creating classification-based rule."""
        repo = UserRuleRepository(db)
        rule = repo.create_rule(
            user_id=test_user.id,
            rule_name="Test Classification Rule",
            rule_type=RuleType.CLASSIFICATION_BASED,
            action=RuleAction.MARK_READ,
            classification_category="newsletter",
            classification_tags=["newsletter", "marketing"]
        )
        
        assert rule.id is not None
        assert rule.rule_type == RuleType.CLASSIFICATION_BASED
        assert rule.classification_category == "newsletter"
        assert rule.classification_tags == ["newsletter", "marketing"]
    
    def test_get_rule_by_id(self, db, test_user, test_email):
        """Test getting rule by ID."""
        repo = UserRuleRepository(db)
        created_rule = repo.create_rule(
            user_id=test_user.id,
            rule_name="Test Rule",
            rule_type=RuleType.SIMILARITY_BASED,
            action=RuleAction.DELETE,
            reference_email_id=test_email.id
        )
        
        rule = repo.get_rule_by_id(created_rule.id, test_user.id)
        
        assert rule is not None
        assert rule.id == created_rule.id
        assert rule.user_id == test_user.id
    
    def test_get_rule_by_id_wrong_user(self, db, test_user, test_email):
        """Test getting rule by ID with wrong user (should return None)."""
        # Create another user
        from app.models.user import User
        other_user = User(
            oauth_provider="google",
            oauth_provider_user_id="other-user-123",
            oauth_email="other@example.com"
        )
        db.add(other_user)
        db.commit()
        
        repo = UserRuleRepository(db)
        created_rule = repo.create_rule(
            user_id=test_user.id,
            rule_name="Test Rule",
            rule_type=RuleType.SIMILARITY_BASED,
            action=RuleAction.DELETE
        )
        
        # Try to get rule with wrong user
        rule = repo.get_rule_by_id(created_rule.id, other_user.id)
        
        assert rule is None
    
    def test_get_rules_by_user(self, db, test_user):
        """Test getting all rules for a user."""
        repo = UserRuleRepository(db)
        
        # Create multiple rules
        rule1 = repo.create_rule(
            user_id=test_user.id,
            rule_name="Rule 1",
            rule_type=RuleType.METADATA_BASED,
            action=RuleAction.DELETE,
            priority=100
        )
        rule2 = repo.create_rule(
            user_id=test_user.id,
            rule_name="Rule 2",
            rule_type=RuleType.METADATA_BASED,
            action=RuleAction.ARCHIVE,
            priority=50
        )
        
        rules = repo.get_rules_by_user(test_user.id)
        
        assert len(rules) >= 2
        rule_ids = [r.id for r in rules]
        assert rule1.id in rule_ids
        assert rule2.id in rule_ids
        # Should be ordered by priority (descending)
        assert rules[0].priority >= rules[1].priority
    
    def test_get_rules_by_user_filter_active(self, db, test_user):
        """Test getting rules filtered by active status."""
        repo = UserRuleRepository(db)
        
        active_rule = repo.create_rule(
            user_id=test_user.id,
            rule_name="Active Rule",
            rule_type=RuleType.METADATA_BASED,
            action=RuleAction.DELETE,
            is_active=True
        )
        inactive_rule = repo.create_rule(
            user_id=test_user.id,
            rule_name="Inactive Rule",
            rule_type=RuleType.METADATA_BASED,
            action=RuleAction.DELETE,
            is_active=False
        )
        
        active_rules = repo.get_rules_by_user(test_user.id, is_active=True)
        inactive_rules = repo.get_rules_by_user(test_user.id, is_active=False)
        
        assert any(r.id == active_rule.id for r in active_rules)
        assert not any(r.id == inactive_rule.id for r in active_rules)
        assert any(r.id == inactive_rule.id for r in inactive_rules)
        assert not any(r.id == active_rule.id for r in inactive_rules)
    
    def test_get_rules_by_user_filter_type(self, db, test_user):
        """Test getting rules filtered by rule type."""
        repo = UserRuleRepository(db)
        
        similarity_rule = repo.create_rule(
            user_id=test_user.id,
            rule_name="Similarity Rule",
            rule_type=RuleType.SIMILARITY_BASED,
            action=RuleAction.DELETE
        )
        metadata_rule = repo.create_rule(
            user_id=test_user.id,
            rule_name="Metadata Rule",
            rule_type=RuleType.METADATA_BASED,
            action=RuleAction.DELETE
        )
        
        similarity_rules = repo.get_rules_by_user(test_user.id, rule_type=RuleType.SIMILARITY_BASED)
        metadata_rules = repo.get_rules_by_user(test_user.id, rule_type=RuleType.METADATA_BASED)
        
        assert any(r.id == similarity_rule.id for r in similarity_rules)
        assert not any(r.id == metadata_rule.id for r in similarity_rules)
        assert any(r.id == metadata_rule.id for r in metadata_rules)
        assert not any(r.id == similarity_rule.id for r in metadata_rules)
    
    def test_get_active_rules_by_user(self, db, test_user):
        """Test getting active rules for a user."""
        repo = UserRuleRepository(db)
        
        active_rule = repo.create_rule(
            user_id=test_user.id,
            rule_name="Active Rule",
            rule_type=RuleType.METADATA_BASED,
            action=RuleAction.DELETE,
            is_active=True
        )
        inactive_rule = repo.create_rule(
            user_id=test_user.id,
            rule_name="Inactive Rule",
            rule_type=RuleType.METADATA_BASED,
            action=RuleAction.DELETE,
            is_active=False
        )
        
        active_rules = repo.get_active_rules_by_user(test_user.id)
        
        assert any(r.id == active_rule.id for r in active_rules)
        assert not any(r.id == inactive_rule.id for r in active_rules)
        assert all(r.is_active == True for r in active_rules)
    
    def test_update_rule(self, db, test_user):
        """Test updating rule."""
        repo = UserRuleRepository(db)
        rule = repo.create_rule(
            user_id=test_user.id,
            rule_name="Original Name",
            rule_type=RuleType.METADATA_BASED,
            action=RuleAction.DELETE,
            sender_filter="old@example.com"
        )
        
        updated_rule = repo.update_rule(
            rule.id,
            test_user.id,
            rule_name="Updated Name",
            sender_filter="new@example.com",
            priority=200
        )
        
        assert updated_rule is not None
        assert updated_rule.rule_name == "Updated Name"
        assert updated_rule.sender_filter == "new@example.com"
        assert updated_rule.priority == 200
    
    def test_update_rule_not_found(self, db, test_user):
        """Test updating non-existent rule."""
        repo = UserRuleRepository(db)
        updated_rule = repo.update_rule(
            99999,
            test_user.id,
            rule_name="Updated Name"
        )
        
        assert updated_rule is None
    
    def test_delete_rule(self, db, test_user):
        """Test deleting rule."""
        repo = UserRuleRepository(db)
        rule = repo.create_rule(
            user_id=test_user.id,
            rule_name="Rule to Delete",
            rule_type=RuleType.METADATA_BASED,
            action=RuleAction.DELETE
        )
        
        result = repo.delete_rule(rule.id, test_user.id)
        
        assert result is True
        # Verify rule is deleted
        deleted_rule = repo.get_rule_by_id(rule.id, test_user.id)
        assert deleted_rule is None
    
    def test_delete_rule_not_found(self, db, test_user):
        """Test deleting non-existent rule."""
        repo = UserRuleRepository(db)
        result = repo.delete_rule(99999, test_user.id)
        
        assert result is False
    
    def test_toggle_rule_active(self, db, test_user):
        """Test toggling rule active status."""
        repo = UserRuleRepository(db)
        rule = repo.create_rule(
            user_id=test_user.id,
            rule_name="Toggle Rule",
            rule_type=RuleType.METADATA_BASED,
            action=RuleAction.DELETE,
            is_active=True
        )
        
        original_active = rule.is_active
        toggled_rule = repo.toggle_rule_active(rule.id, test_user.id)
        
        assert toggled_rule is not None
        assert toggled_rule.is_active != original_active
        
        # Toggle again
        toggled_again = repo.toggle_rule_active(rule.id, test_user.id)
        assert toggled_again.is_active == original_active

