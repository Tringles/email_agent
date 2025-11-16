"""User Repository tests."""

import pytest
from datetime import datetime, timedelta

from app.db.repositories.user_repo import UserRepository
from app.models.user import User


class TestUserRepository:
    """User Repository tests."""
    
    def test_get_user_by_id(self, db, test_user):
        """Test getting user by ID."""
        repo = UserRepository(db)
        user = repo.get_user_by_id(test_user.id)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.oauth_email == test_user.oauth_email
    
    def test_get_user_by_id_not_found(self, db):
        """Test getting non-existent user."""
        repo = UserRepository(db)
        user = repo.get_user_by_id(99999)
        
        assert user is None
    
    def test_get_user_by_email(self, db, test_user):
        """Test getting user by email."""
        repo = UserRepository(db)
        user = repo.get_user_by_email(test_user.oauth_email)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.oauth_email == test_user.oauth_email
    
    def test_get_user_by_email_not_found(self, db):
        """Test getting user by non-existent email."""
        repo = UserRepository(db)
        user = repo.get_user_by_email("nonexistent@example.com")
        
        assert user is None
    
    def test_get_user_by_oauth_provider_user_id(self, db, test_user):
        """Test getting user by OAuth provider and provider user ID."""
        repo = UserRepository(db)
        user = repo.get_user_by_oauth_provider_user_id(
            provider=test_user.oauth_provider,
            provider_user_id=test_user.oauth_provider_user_id
        )
        
        assert user is not None
        assert user.id == test_user.id
        assert user.oauth_provider == test_user.oauth_provider
        assert user.oauth_provider_user_id == test_user.oauth_provider_user_id
    
    def test_get_user_by_oauth_provider_user_id_not_found(self, db):
        """Test getting user by non-existent OAuth provider user ID."""
        repo = UserRepository(db)
        user = repo.get_user_by_oauth_provider_user_id(
            provider="google",
            provider_user_id="nonexistent-id"
        )
        
        assert user is None
    
    def test_create_user(self, db):
        """Test creating user."""
        repo = UserRepository(db)
        user_data = {
            "oauth_provider": "google",
            "oauth_provider_user_id": "new-user-123",
            "oauth_email": "newuser@example.com",
            "display_name": "New User",
            "is_active": True
        }
        user = repo.create_user(user_data)
        
        assert user.id is not None
        assert user.oauth_provider == "google"
        assert user.oauth_provider_user_id == "new-user-123"
        assert user.oauth_email == "newuser@example.com"
        assert user.display_name == "New User"
        assert user.is_active is True
    
    def test_update_user(self, db, test_user):
        """Test updating user."""
        repo = UserRepository(db)
        updated_user = repo.update_user(
            test_user,
            display_name="Updated Name",
            profile_image_url="https://example.com/new-avatar.jpg",
            locale="en"
        )
        
        assert updated_user.display_name == "Updated Name"
        assert updated_user.profile_image_url == "https://example.com/new-avatar.jpg"
        assert updated_user.locale == "en"
    
    def test_update_user_oauth_tokens(self, db, test_user):
        """Test updating user OAuth tokens."""
        repo = UserRepository(db)
        new_token = "new-access-token"
        new_refresh_token = "new-refresh-token"
        expires_at = datetime.now() + timedelta(hours=1)
        
        updated_user = repo.update_user(
            test_user,
            oauth_access_token=new_token,
            oauth_refresh_token=new_refresh_token,
            oauth_token_expires_at=expires_at
        )
        
        assert updated_user.oauth_access_token == new_token
        assert updated_user.oauth_refresh_token == new_refresh_token
        assert updated_user.oauth_token_expires_at == expires_at
    
    def test_deactivate_user(self, db, test_user):
        """Test deactivating user."""
        # Ensure user is active first
        test_user.is_active = True
        db.commit()
        
        repo = UserRepository(db)
        deactivated_user = repo.deactivate_user(test_user.id)
        
        assert deactivated_user is not None
        assert deactivated_user.is_active is False
    
    def test_activate_user(self, db, test_user):
        """Test activating user."""
        # Deactivate user first
        test_user.is_active = False
        db.commit()
        
        repo = UserRepository(db)
        activated_user = repo.activate_user(test_user.id)
        
        assert activated_user is not None
        assert activated_user.is_active is True
    
    def test_deactivate_user_not_found(self, db):
        """Test deactivating non-existent user."""
        repo = UserRepository(db)
        result = repo.deactivate_user(99999)
        
        assert result is None
    
    def test_activate_user_not_found(self, db):
        """Test activating non-existent user."""
        repo = UserRepository(db)
        result = repo.activate_user(99999)
        
        assert result is None

