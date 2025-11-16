"""Email Account Repository tests."""

import pytest
from datetime import datetime

from app.db.repositories.email_account_repo import EmailAccountRepository
from app.models.email_account import EmailAccount, EmailProviderType


class TestEmailAccountRepository:
    """Email Account Repository tests."""
    
    def test_get_account_by_id(self, db, test_email_account):
        """Test getting account by ID."""
        repo = EmailAccountRepository(db)
        account = repo.get_account_by_id(test_email_account.id)
        
        assert account is not None
        assert account.id == test_email_account.id
        assert account.email_address == test_email_account.email_address
    
    def test_get_account_by_id_not_found(self, db):
        """Test getting non-existent account."""
        repo = EmailAccountRepository(db)
        account = repo.get_account_by_id(99999)
        
        assert account is None
    
    def test_get_accounts_by_user(self, db, test_user):
        """Test getting all accounts for a user."""
        # Create multiple accounts
        account1 = EmailAccount(
            user_id=test_user.id,
            email_address="test1@example.com",
            provider_type=EmailProviderType.GMAIL,
            display_name="Test Account 1",
            credentials={"token": "token1"},
            is_active=True
        )
        account2 = EmailAccount(
            user_id=test_user.id,
            email_address="test2@example.com",
            provider_type=EmailProviderType.NAVER,
            display_name="Test Account 2",
            credentials={"token": "token2"},
            is_active=True
        )
        db.add(account1)
        db.add(account2)
        db.commit()
        
        repo = EmailAccountRepository(db)
        accounts = repo.get_accounts_by_user(test_user.id)
        
        assert len(accounts) >= 2
        account_ids = [a.id for a in accounts]
        assert account1.id in account_ids
        assert account2.id in account_ids
        # Should be ordered by created_at desc
        assert accounts[0].created_at >= accounts[1].created_at
    
    def test_get_active_accounts(self, db, test_user):
        """Test getting active accounts."""
        # Create active and inactive accounts
        active_account = EmailAccount(
            user_id=test_user.id,
            email_address="active@example.com",
            provider_type=EmailProviderType.GMAIL,
            display_name="Active Account",
            credentials={"token": "token"},
            is_active=True
        )
        inactive_account = EmailAccount(
            user_id=test_user.id,
            email_address="inactive@example.com",
            provider_type=EmailProviderType.GMAIL,
            display_name="Inactive Account",
            credentials={"token": "token"},
            is_active=False
        )
        db.add(active_account)
        db.add(inactive_account)
        db.commit()
        
        repo = EmailAccountRepository(db)
        active_accounts = repo.get_active_accounts(user_id=test_user.id)
        
        assert any(a.id == active_account.id for a in active_accounts)
        assert not any(a.id == inactive_account.id for a in active_accounts)
        assert all(a.is_active == True for a in active_accounts)
    
    def test_get_active_accounts_all_users(self, db, test_user):
        """Test getting active accounts for all users."""
        # Create another user
        from app.models.user import User
        other_user = User(
            oauth_provider="google",
            oauth_provider_user_id="other-user-123",
            oauth_email="other@example.com"
        )
        db.add(other_user)
        db.commit()
        
        account1 = EmailAccount(
            user_id=test_user.id,
            email_address="user1@example.com",
            provider_type=EmailProviderType.GMAIL,
            display_name="User 1 Account",
            credentials={"token": "token"},
            is_active=True
        )
        account2 = EmailAccount(
            user_id=other_user.id,
            email_address="user2@example.com",
            provider_type=EmailProviderType.GMAIL,
            display_name="User 2 Account",
            credentials={"token": "token"},
            is_active=True
        )
        db.add(account1)
        db.add(account2)
        db.commit()
        
        repo = EmailAccountRepository(db)
        all_active_accounts = repo.get_active_accounts()
        
        assert len(all_active_accounts) >= 2
        account_ids = [a.id for a in all_active_accounts]
        assert account1.id in account_ids
        assert account2.id in account_ids
    
    def test_get_accounts_by_provider(self, db, test_user):
        """Test getting accounts by provider type."""
        gmail_account = EmailAccount(
            user_id=test_user.id,
            email_address="gmail@example.com",
            provider_type=EmailProviderType.GMAIL,
            display_name="Gmail Account",
            credentials={"token": "token"},
            is_active=True
        )
        naver_account = EmailAccount(
            user_id=test_user.id,
            email_address="naver@naver.com",
            provider_type=EmailProviderType.NAVER,
            display_name="Naver Account",
            credentials={"token": "token"},
            is_active=True
        )
        db.add(gmail_account)
        db.add(naver_account)
        db.commit()
        
        repo = EmailAccountRepository(db)
        gmail_accounts = repo.get_accounts_by_provider(EmailProviderType.GMAIL, user_id=test_user.id)
        naver_accounts = repo.get_accounts_by_provider(EmailProviderType.NAVER, user_id=test_user.id)
        
        assert any(a.id == gmail_account.id for a in gmail_accounts)
        assert not any(a.id == naver_account.id for a in gmail_accounts)
        assert any(a.id == naver_account.id for a in naver_accounts)
        assert not any(a.id == gmail_account.id for a in naver_accounts)
        assert all(a.provider_type == EmailProviderType.GMAIL for a in gmail_accounts)
        assert all(a.provider_type == EmailProviderType.NAVER for a in naver_accounts)
    
    def test_update_last_fetch_success(self, db, test_email_account):
        """Test updating last fetch timestamp on success."""
        repo = EmailAccountRepository(db)
        original_fetch_time = test_email_account.last_fetch_at
        
        updated_account = repo.update_last_fetch(test_email_account.id, success=True)
        
        assert updated_account is not None
        assert updated_account.last_fetch_at is not None
        assert updated_account.last_fetch_at != original_fetch_time
        assert updated_account.last_fetch_error is None
    
    def test_update_last_fetch_error(self, db, test_email_account):
        """Test updating last fetch with error message."""
        repo = EmailAccountRepository(db)
        error_message = "Connection timeout"
        
        updated_account = repo.update_last_fetch(
            test_email_account.id,
            success=False,
            error_message=error_message
        )
        
        assert updated_account is not None
        assert updated_account.last_fetch_error == error_message
    
    def test_update_last_fetch_not_found(self, db):
        """Test updating last fetch for non-existent account."""
        repo = EmailAccountRepository(db)
        updated_account = repo.update_last_fetch(99999, success=True)
        
        assert updated_account is None

