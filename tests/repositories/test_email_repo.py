"""Email Repository tests."""

import pytest
from datetime import datetime

from app.db.repositories.email_repo import EmailRepository
from app.models.email import Email, EmailStatus
from app.models.email_account import EmailAccount, EmailProviderType


class TestEmailRepository:
    """Email Repository tests."""
    
    def test_get_unprocessed_emails(self, db, test_email_account, test_email):
        """Test getting unprocessed emails."""
        # Create unprocessed email
        unprocessed_email = Email(
            email_account_id=test_email_account.id,
            provider_message_id="msg-123",
            subject="Unprocessed Email",
            sender="sender@example.com",
            recipient="recipient@example.com",
            email_date=datetime.now(),
            is_processed=False,
            status=EmailStatus.PENDING,
            is_deleted=False
        )
        db.add(unprocessed_email)
        db.commit()
        
        repo = EmailRepository(db)
        emails = repo.get_unprocessed_emails()
        
        assert len(emails) >= 1
        assert any(e.id == unprocessed_email.id for e in emails)
        assert all(e.is_processed == False for e in emails)
        assert all(e.status == EmailStatus.PENDING for e in emails)
        assert all(e.is_deleted == False for e in emails)
    
    def test_get_unprocessed_emails_with_account_filter(self, db, test_email_account):
        """Test getting unprocessed emails filtered by account."""
        # Create unprocessed email for the account
        unprocessed_email = Email(
            email_account_id=test_email_account.id,
            provider_message_id="msg-123",
            subject="Unprocessed Email",
            sender="sender@example.com",
            recipient="recipient@example.com",
            email_date=datetime.now(),
            is_processed=False,
            status=EmailStatus.PENDING,
            is_deleted=False
        )
        db.add(unprocessed_email)
        db.commit()
        
        repo = EmailRepository(db)
        emails = repo.get_unprocessed_emails(account_id=test_email_account.id)
        
        assert len(emails) >= 1
        assert all(e.email_account_id == test_email_account.id for e in emails)
    
    def test_get_emails_pagination(self, db, test_user, test_email_account):
        """Test getting emails with pagination."""
        # Create multiple emails
        for i in range(5):
            email = Email(
                email_account_id=test_email_account.id,
                provider_message_id=f"msg-{i}",
                subject=f"Email {i}",
                sender="sender@example.com",
                recipient="recipient@example.com",
                email_date=datetime.now(),
                is_deleted=False
            )
            db.add(email)
        db.commit()
        
        repo = EmailRepository(db)
        emails, total = repo.get_emails(user_id=test_user.id, page=1, page_size=2)
        
        assert len(emails) == 2
        assert total >= 5
    
    def test_get_emails_with_filters(self, db, test_user, test_email_account):
        """Test getting emails with various filters."""
        # Create emails with different properties
        important_email = Email(
            email_account_id=test_email_account.id,
            provider_message_id="msg-important",
            subject="Important Email",
            sender="sender@example.com",
            recipient="recipient@example.com",
            email_date=datetime.now(),
            is_important=True,
            is_deleted=False
        )
        read_email = Email(
            email_account_id=test_email_account.id,
            provider_message_id="msg-read",
            subject="Read Email",
            sender="sender@example.com",
            recipient="recipient@example.com",
            email_date=datetime.now(),
            is_read=True,
            is_deleted=False
        )
        db.add(important_email)
        db.add(read_email)
        db.commit()
        
        repo = EmailRepository(db)
        
        # Test is_important filter
        emails, _ = repo.get_emails(user_id=test_user.id, is_important=True)
        assert any(e.id == important_email.id for e in emails)
        assert all(e.is_important == True for e in emails)
        
        # Test is_read filter
        emails, _ = repo.get_emails(user_id=test_user.id, is_read=True)
        assert any(e.id == read_email.id for e in emails)
        assert all(e.is_read == True for e in emails)
    
    def test_get_emails_with_search(self, db, test_user, test_email_account):
        """Test getting emails with search."""
        email = Email(
            email_account_id=test_email_account.id,
            provider_message_id="msg-search",
            subject="Test Search Email",
            sender="sender@example.com",
            recipient="recipient@example.com",
            body_text="This is a test email",
            email_date=datetime.now(),
            is_deleted=False
        )
        db.add(email)
        db.commit()
        
        repo = EmailRepository(db)
        emails, _ = repo.get_emails(user_id=test_user.id, search="Test")
        
        assert len(emails) >= 1
        assert any("Test" in e.subject or "Test" in e.body_text for e in emails)
    
    def test_get_email_by_id(self, db, test_user, test_email_account, test_email):
        """Test getting email by ID."""
        repo = EmailRepository(db)
        email = repo.get_email_by_id(test_email.id, user_id=test_user.id)
        
        assert email is not None
        assert email.id == test_email.id
        assert hasattr(email, 'email_account')  # Should be eagerly loaded
    
    def test_get_email_by_id_not_found(self, db, test_user):
        """Test getting non-existent email."""
        repo = EmailRepository(db)
        email = repo.get_email_by_id(99999, user_id=test_user.id)
        
        assert email is None
    
    def test_get_email_by_id_include_deleted(self, db, test_user, test_email_account):
        """Test getting deleted email with include_deleted=True."""
        deleted_email = Email(
            email_account_id=test_email_account.id,
            provider_message_id="msg-deleted",
            subject="Deleted Email",
            sender="sender@example.com",
            recipient="recipient@example.com",
            email_date=datetime.now(),
            is_deleted=True
        )
        db.add(deleted_email)
        db.commit()
        
        repo = EmailRepository(db)
        
        # Should not find deleted email by default
        email = repo.get_email_by_id(deleted_email.id, user_id=test_user.id)
        assert email is None
        
        # Should find with include_deleted=True
        email = repo.get_email_by_id(deleted_email.id, user_id=test_user.id, include_deleted=True)
        assert email is not None
        assert email.id == deleted_email.id
    
    def test_create_email(self, db, test_email_account):
        """Test creating email."""
        repo = EmailRepository(db)
        email_data = {
            "email_account_id": test_email_account.id,
            "provider_message_id": "msg-new",
            "subject": "New Email",
            "sender": "sender@example.com",
            "recipient": "recipient@example.com",
            "email_date": datetime.now()
        }
        email = repo.create_email(email_data)
        
        assert email.id is not None
        assert email.subject == "New Email"
        assert email.email_account_id == test_email_account.id
    
    def test_update_email(self, db, test_email):
        """Test updating email."""
        repo = EmailRepository(db)
        updated_email = repo.update_email(
            test_email,
            subject="Updated Subject",
            is_read=True
        )
        
        assert updated_email.subject == "Updated Subject"
        assert updated_email.is_read is True
    
    def test_mark_as_read(self, db, test_user, test_email_account):
        """Test marking email as read."""
        email = Email(
            email_account_id=test_email_account.id,
            provider_message_id="msg-read",
            subject="Test Email",
            sender="sender@example.com",
            recipient="recipient@example.com",
            email_date=datetime.now(),
            is_read=False,
            is_deleted=False
        )
        db.add(email)
        db.commit()
        
        repo = EmailRepository(db)
        updated_email = repo.mark_as_read(email.id, test_user.id, read=True)
        
        assert updated_email is not None
        assert updated_email.is_read is True
    
    def test_mark_as_important(self, db, test_user, test_email_account):
        """Test marking email as important."""
        email = Email(
            email_account_id=test_email_account.id,
            provider_message_id="msg-important",
            subject="Test Email",
            sender="sender@example.com",
            recipient="recipient@example.com",
            email_date=datetime.now(),
            is_important=False,
            is_deleted=False
        )
        db.add(email)
        db.commit()
        
        repo = EmailRepository(db)
        updated_email = repo.mark_as_important(email.id, test_user.id, important=True)
        
        assert updated_email is not None
        assert updated_email.is_important is True
    
    def test_archive_email(self, db, test_user, test_email_account):
        """Test archiving email."""
        email = Email(
            email_account_id=test_email_account.id,
            provider_message_id="msg-archive",
            subject="Test Email",
            sender="sender@example.com",
            recipient="recipient@example.com",
            email_date=datetime.now(),
            is_archived=False,
            is_deleted=False
        )
        db.add(email)
        db.commit()
        
        repo = EmailRepository(db)
        updated_email = repo.archive_email(email.id, test_user.id, archived=True)
        
        assert updated_email is not None
        assert updated_email.is_archived is True
    
    def test_delete_email(self, db, test_user, test_email_account):
        """Test soft deleting email."""
        email = Email(
            email_account_id=test_email_account.id,
            provider_message_id="msg-delete",
            subject="Test Email",
            sender="sender@example.com",
            recipient="recipient@example.com",
            email_date=datetime.now(),
            is_deleted=False
        )
        db.add(email)
        db.commit()
        
        repo = EmailRepository(db)
        result = repo.delete_email(email.id, test_user.id)
        
        assert result is True
        db.refresh(email)
        assert email.is_deleted is True
    
    def test_mark_as_processed(self, db, test_email_account):
        """Test marking email as processed."""
        email = Email(
            email_account_id=test_email_account.id,
            provider_message_id="msg-process",
            subject="Test Email",
            sender="sender@example.com",
            recipient="recipient@example.com",
            email_date=datetime.now(),
            is_processed=False,
            status=EmailStatus.PENDING
        )
        db.add(email)
        db.commit()
        
        repo = EmailRepository(db)
        updated_email = repo.mark_as_processed(email.id)
        
        assert updated_email is not None
        assert updated_email.is_processed is True
        assert updated_email.status == EmailStatus.PROCESSED
        assert updated_email.processed_at is not None

