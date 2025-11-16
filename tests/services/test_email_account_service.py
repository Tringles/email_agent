"""Email Account Service tests."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from app.services.email_account_service import EmailAccountService
from app.models.email_account import EmailProviderType


class TestEmailAccountService:
    """Email Account Service tests."""
    
    def test_init(self):
        """Test EmailAccountService initialization."""
        with patch('app.services.email_account_service.settings') as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
            mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
            
            service = EmailAccountService()
            
            assert service.google_client_id == "test-client-id"
            assert service.google_client_secret == "test-client-secret"
    
    @patch('app.services.email_account_service.Flow')
    @patch('app.services.email_account_service.settings')
    def test_get_gmail_connect_url(self, mock_settings, mock_flow_class):
        """Test getting Gmail OAuth connection URL."""
        mock_settings.API_BASE_URL = "http://localhost:8000"
        mock_settings.API_V1_STR = "/api/v1"
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
        
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = ("http://gmail.auth.url", "state")
        mock_flow_class.from_client_config.return_value = mock_flow
        
        service = EmailAccountService()
        url = service.get_gmail_connect_url(user_id=1)
        
        assert url == "http://gmail.auth.url"
        mock_flow.authorization_url.assert_called_once_with(
            access_type="offline",
            include_granted_scopes="false",
            prompt="consent",
            state="1"  # user_id as string
        )
    
    @pytest.mark.asyncio
    @patch('app.services.email_account_service.Flow')
    @patch('app.services.email_account_service.build')
    @patch('app.services.email_account_service.settings')
    async def test_handle_gmail_callback_new_account(self, mock_settings, mock_build, mock_flow_class, db, test_user):
        """Test handling Gmail callback to create new account."""
        mock_settings.API_BASE_URL = "http://localhost:8000"
        mock_settings.API_V1_STR = "/api/v1"
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
        
        # Mock Flow
        mock_flow = MagicMock()
        mock_flow.fetch_token = MagicMock()
        mock_flow.credentials = MagicMock()
        mock_flow.credentials.token = "access-token"
        mock_flow.credentials.refresh_token = "refresh-token"
        mock_flow.credentials.token_uri = "https://oauth2.googleapis.com/token"
        mock_flow.credentials.client_id = "test-client-id"
        mock_flow.credentials.client_secret = "test-client-secret"
        mock_flow.credentials.scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
        mock_flow.credentials.expiry = datetime.now() + timedelta(hours=1)
        mock_flow_class.from_client_config.return_value = mock_flow
        
        # Mock Gmail API
        mock_service = MagicMock()
        mock_profile = MagicMock()
        mock_profile.execute.return_value = {"emailAddress": "test@gmail.com"}
        mock_service.users.return_value.getProfile.return_value = mock_profile
        mock_build.return_value = mock_service
        
        service = EmailAccountService()
        account = await service.handle_gmail_callback("test-code", test_user.id, db)
        
        assert account.email_address == "test@gmail.com"
        assert account.provider_type == EmailProviderType.GMAIL
        assert account.user_id == test_user.id
        assert account.is_active is True
        assert "token" in account.credentials
    
    @pytest.mark.asyncio
    @patch('app.services.email_account_service.Flow')
    @patch('app.services.email_account_service.settings')
    async def test_handle_gmail_callback_existing_account(self, mock_settings, mock_flow_class, db, test_user, test_email_account):
        """Test handling Gmail callback to update existing account."""
        mock_settings.API_BASE_URL = "http://localhost:8000"
        mock_settings.API_V1_STR = "/api/v1"
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"
        
        # Set test_email_account to Gmail type
        test_email_account.provider_type = EmailProviderType.GMAIL
        test_email_account.email_address = "test@gmail.com"
        db.commit()
        
        # Mock Flow
        mock_flow = MagicMock()
        mock_flow.fetch_token = MagicMock()
        mock_flow.credentials = MagicMock()
        mock_flow.credentials.token = "new-access-token"
        mock_flow.credentials.refresh_token = "new-refresh-token"
        mock_flow.credentials.token_uri = "https://oauth2.googleapis.com/token"
        mock_flow.credentials.client_id = "test-client-id"
        mock_flow.credentials.client_secret = "test-client-secret"
        mock_flow.credentials.scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
        mock_flow.credentials.expiry = datetime.now() + timedelta(hours=1)
        mock_flow_class.from_client_config.return_value = mock_flow
        
        # Mock Gmail API
        with patch('app.services.email_account_service.build') as mock_build:
            mock_service = MagicMock()
            mock_profile = MagicMock()
            mock_profile.execute.return_value = {"emailAddress": "test@gmail.com"}
            mock_service.users.return_value.getProfile.return_value = mock_profile
            mock_build.return_value = mock_service
            
            service = EmailAccountService()
            account = await service.handle_gmail_callback("test-code", test_user.id, db)
            
            assert account.id == test_email_account.id
            assert account.credentials["token"] == "new-access-token"
    
    @pytest.mark.asyncio
    @patch('app.services.email_account_service.NaverProvider')
    @patch('app.services.email_account_service.settings')
    async def test_connect_naver_account_new(self, mock_settings, mock_naver_provider_class, db, test_user):
        """Test connecting new Naver account."""
        # Mock NaverProvider
        mock_provider = AsyncMock()
        mock_provider.connect = AsyncMock(return_value=True)
        mock_provider.disconnect = AsyncMock()
        mock_naver_provider_class.return_value = mock_provider
        
        service = EmailAccountService()
        account = await service.connect_naver_account(
            user_id=test_user.id,
            email="test@naver.com",
            password="test-password",
            db=db
        )
        
        assert account.email_address == "test@naver.com"
        assert account.provider_type == EmailProviderType.NAVER
        assert account.user_id == test_user.id
        assert account.is_active is True
        assert account.credentials["username"] == "test@naver.com"
        assert account.credentials["server"] == "imap.naver.com"
        assert account.credentials["port"] == 993
    
    @pytest.mark.asyncio
    @patch('app.services.email_account_service.NaverProvider')
    async def test_connect_naver_account_invalid_email(self, mock_naver_provider_class, db, test_user):
        """Test connecting Naver account with invalid email."""
        service = EmailAccountService()
        
        with pytest.raises(ValueError, match="Invalid Naver email address"):
            await service.connect_naver_account(
                user_id=test_user.id,
                email="test@gmail.com",  # Not @naver.com
                password="test-password",
                db=db
            )
    
    @pytest.mark.asyncio
    @patch('app.services.email_account_service.NaverProvider')
    async def test_connect_naver_account_connection_failed(self, mock_naver_provider_class, db, test_user):
        """Test connecting Naver account with failed connection."""
        # Mock NaverProvider to fail connection
        mock_provider = AsyncMock()
        mock_provider.connect = AsyncMock(return_value=False)
        mock_naver_provider_class.return_value = mock_provider
        
        service = EmailAccountService()
        
        with pytest.raises(ValueError, match="Failed to connect"):
            await service.connect_naver_account(
                user_id=test_user.id,
                email="test@naver.com",
                password="wrong-password",
                db=db
            )

