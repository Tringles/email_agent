"""Pytest configuration and shared fixtures."""

import pytest
from typing import Generator
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Import models FIRST to ensure they're registered with Base.metadata
# This must happen before importing app.main (which uses app.models)
from app.models import User, EmailAccount, Email, UserRule  # noqa: F401
import app.models.user  # noqa: F401
import app.models.email_account  # noqa: F401
import app.models.email  # noqa: F401
import app.models.user_rule  # noqa: F401

# Now import app.main (app is FastAPI instance, not module)
from app.main import app
from app.db.session import Base, get_db
from app.models.user import User
from app.models.email import Email
from app.models.email_account import EmailAccount
from app.models.user_rule import UserRule, RuleType, RuleAction
from app.core.security import create_user_token


# Test database URL (use temporary file for testing to ensure tables persist)
import tempfile
import os

# Create a temporary database file
_test_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
_test_db_file.close()
TEST_DATABASE_URL = f"sqlite:///{_test_db_file.name}"

# Create test engine and session
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Cleanup function to remove temp file
def _cleanup_test_db():
    """Remove temporary test database file."""
    try:
        if os.path.exists(_test_db_file.name):
            os.unlink(_test_db_file.name)
    except Exception:
        pass

# Register cleanup at module level
import atexit
atexit.register(_cleanup_test_db)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a test database session."""
    # All models are already imported at module level
    # Ensure all models are registered before creating tables
    # Drop all tables first to ensure clean state
    Base.metadata.drop_all(bind=test_engine, checkfirst=True)
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up: drop all tables after test
        Base.metadata.drop_all(bind=test_engine, checkfirst=True)


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    # Clear all overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        id=1,
        oauth_provider="google",
        oauth_provider_user_id="google-user-123",  # Required field
        oauth_email="test@example.com",
        display_name="Test User",
        profile_image_url="https://example.com/avatar.jpg",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_token(test_user: User) -> str:
    """Create a JWT token for test user."""
    return create_user_token(
        user_id=test_user.id,
        email=test_user.oauth_email,
        provider=test_user.oauth_provider
    )


@pytest.fixture
def authenticated_client(client: TestClient, test_user: User, test_user_token: str, db: Session) -> TestClient:
    """Create an authenticated test client."""
    from app.core.security import get_current_user
    
    def override_get_current_user():
        return test_user
    
    # Override get_current_user dependency
    app.dependency_overrides[get_current_user] = override_get_current_user
    client.headers.update({"Authorization": f"Bearer {test_user_token}"})
    
    yield client
    
    # Cleanup is handled by client fixture


@pytest.fixture
def test_email_account(db: Session, test_user: User) -> EmailAccount:
    """Create a test email account."""
    account = EmailAccount(
        id=1,
        user_id=test_user.id,
        provider_type="gmail",
        email_address="test@gmail.com",
        is_active=True,
        credentials={"access_token": "test-token", "refresh_token": "test-refresh"}  # Required field
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def test_email(db: Session, test_user: User, test_email_account: EmailAccount) -> Email:
    """Create a test email."""
    from datetime import datetime
    from app.models.email import EmailStatus
    
    email = Email(
        id=1,
        email_account_id=test_email_account.id,
        subject="Test Email",
        sender="sender@example.com",
        sender_name="Test Sender",
        recipient="test@example.com",
        recipient_name="Test User",
        body_text="This is a test email body.",
        body_html="<p>This is a test email body.</p>",
        preview="This is a test email body.",
        email_date=datetime.now(),
        received_date=datetime.now(),
        status=EmailStatus.PROCESSED,
        is_read=False,
        is_important=False,
        is_archived=False,
        is_deleted=False,
        is_processed=True,
        vector_db_id="test-vector-id-123",
        has_attachments=False,
        attachment_count=0,
        provider_message_id="test-msg-123",
        provider_thread_id="test-thread-123"
    )
    db.add(email)
    db.flush()  # Flush to get the email ID
    # Ensure email_account_id is set
    email.email_account_id = test_email_account.id
    # Set relationship manually for test
    email.email_account = test_email_account
    db.commit()
    db.refresh(email)
    # Refresh email_account relationship to ensure it's loaded
    if email.email_account:
        db.refresh(email.email_account)
    return email


@pytest.fixture
def test_user_rule(db: Session, test_user: User, test_email: Email) -> UserRule:
    """Create a test user rule."""
    rule = UserRule(
        id=1,
        user_id=test_user.id,
        rule_name="Test Rule",
        description="Test rule description",
        rule_type=RuleType.SIMILARITY_BASED,
        action=RuleAction.DELETE,
        is_active=True,
        priority=100,
        reference_email_id=test_email.id,
        similarity_threshold=0.8
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@pytest.fixture
def mock_agent_service():
    """Mock AgentService."""
    with patch('app.services.agent_service.AgentService') as mock:
        service_instance = MagicMock()
        mock.return_value = service_instance
        service_instance.process_email = MagicMock(return_value={
            "success": True,
            "completed_nodes": ["load_email", "preprocess_html", "summarize", "classify"],
            "errors": [],
            "summary": "Test summary",
            "importance_level": "medium",
            "classification": {"category": "work", "tags": ["test"]}
        })
        yield service_instance


@pytest.fixture
def mock_auth_service():
    """Mock AuthService."""
    with patch('app.services.auth_service.AuthService') as mock:
        service_instance = MagicMock()
        mock.return_value = service_instance
        service_instance.get_google_auth_url = MagicMock(return_value="https://accounts.google.com/oauth")
        service_instance.handle_google_callback = MagicMock(return_value=Mock(
            id=1,
            oauth_provider="google",
            oauth_email="test@example.com"
        ))
        yield service_instance

