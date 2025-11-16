"""Storage Service tests."""

import pytest
from unittest.mock import patch, MagicMock, Mock
from io import BytesIO

from app.services.storage_service import (
    StorageService,
    sanitize_filename,
    get_email_storage_path,
    get_raw_mime_path,
    get_attachment_path
)


class TestStorageServiceHelpers:
    """Tests for storage service helper functions."""
    
    def test_sanitize_filename_normal(self):
        """Test sanitizing normal filename."""
        result = sanitize_filename("test_file.pdf")
        assert result == "test_file.pdf"
    
    def test_sanitize_filename_with_path(self):
        """Test sanitizing filename with path separators."""
        result = sanitize_filename("path/to/file.pdf")
        assert result == "path_to_file.pdf"
    
    def test_sanitize_filename_special_chars(self):
        """Test sanitizing filename with special characters."""
        result = sanitize_filename("file<>:\"|?*.pdf")
        assert result == "file_______.pdf"
    
    def test_sanitize_filename_empty(self):
        """Test sanitizing empty filename."""
        result = sanitize_filename("")
        assert result == "attachment"
    
    def test_sanitize_filename_too_long(self):
        """Test sanitizing very long filename."""
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name)
        assert len(result) <= 200
        assert result.endswith(".pdf")
    
    def test_get_email_storage_path(self):
        """Test getting email storage path."""
        result = get_email_storage_path(user_id=1, email_id=100)
        assert result == "users/1/emails/100"
    
    def test_get_raw_mime_path(self):
        """Test getting raw MIME path."""
        result = get_raw_mime_path(user_id=1, email_id=100)
        assert result == "users/1/emails/100/raw.mime"
    
    def test_get_attachment_path(self):
        """Test getting attachment path."""
        result = get_attachment_path(
            user_id=1,
            email_id=100,
            index=0,
            filename="test.pdf"
        )
        assert result == "users/1/emails/100/attachments/0_test.pdf"
        assert "test.pdf" in result


class TestStorageService:
    """Storage Service tests."""
    
    @patch('app.services.storage_service.boto3.client')
    @patch('app.services.storage_service.settings')
    def test_init(self, mock_settings, mock_boto_client):
        """Test StorageService initialization."""
        mock_settings.MINIO_ENDPOINT = None
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        mock_settings.MINIO_ACCESS_KEY = None
        mock_settings.MINIO_SECRET_KEY = None
        mock_settings.MINIO_USE_SSL = False
        
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        
        service = StorageService()
        
        assert service.bucket_name == "test-bucket"
        mock_boto_client.assert_called_once()
    
    @patch('app.services.storage_service.boto3.client')
    @patch('app.services.storage_service.settings')
    def test_upload_file_success(self, mock_settings, mock_boto_client):
        """Test successful file upload."""
        mock_settings.MINIO_ENDPOINT = None
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        mock_settings.MINIO_ACCESS_KEY = None
        mock_settings.MINIO_SECRET_KEY = None
        mock_settings.MINIO_USE_SSL = False
        
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        
        service = StorageService()
        service._bucket_checked = True  # Skip bucket check
        
        file_content = BytesIO(b"test file content")
        result = service.upload_file(
            file_path="test/path/file.txt",
            file_data=file_content,
            content_type="text/plain"
        )
        
        assert result is True
        mock_s3_client.upload_fileobj.assert_called_once()
    
    @patch('app.services.storage_service.boto3.client')
    @patch('app.services.storage_service.settings')
    def test_upload_file_error(self, mock_settings, mock_boto_client):
        """Test file upload with error."""
        mock_settings.MINIO_ENDPOINT = None
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        mock_settings.MINIO_ACCESS_KEY = None
        mock_settings.MINIO_SECRET_KEY = None
        mock_settings.MINIO_USE_SSL = False
        
        from botocore.exceptions import ClientError
        
        mock_s3_client = MagicMock()
        error_response = {'Error': {'Code': '500', 'Message': 'Upload error'}}
        mock_s3_client.upload_fileobj.side_effect = ClientError(error_response, 'UploadObject')
        mock_boto_client.return_value = mock_s3_client
        
        service = StorageService()
        service._bucket_checked = True  # Skip bucket check
        
        file_content = BytesIO(b"test file content")
        result = service.upload_file(
            file_path="test/path/file.txt",
            file_data=file_content
        )
        
        assert result is False
    
    @patch('app.services.storage_service.boto3.client')
    @patch('app.services.storage_service.settings')
    def test_download_file_success(self, mock_settings, mock_boto_client):
        """Test successful file download."""
        mock_settings.MINIO_ENDPOINT = None
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        mock_settings.MINIO_ACCESS_KEY = None
        mock_settings.MINIO_SECRET_KEY = None
        mock_settings.MINIO_USE_SSL = False
        
        mock_s3_client = MagicMock()
        mock_response = {
            'Body': BytesIO(b"file content")
        }
        mock_s3_client.get_object.return_value = mock_response
        mock_boto_client.return_value = mock_s3_client
        
        service = StorageService()
        result = service.download_file("test/path/file.txt")
        
        assert result is not None
        assert result == b"file content"  # download_file returns bytes, not BytesIO
        call_kwargs = mock_s3_client.get_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "test/path/file.txt"
    
    @patch('app.services.storage_service.boto3.client')
    @patch('app.services.storage_service.settings')
    def test_download_file_not_found(self, mock_settings, mock_boto_client):
        """Test downloading non-existent file."""
        from botocore.exceptions import ClientError
        
        mock_settings.S3_ENDPOINT_URL = "http://localhost:9000"
        mock_settings.S3_ACCESS_KEY = "test-access-key"
        mock_settings.S3_SECRET_KEY = "test-secret-key"
        mock_settings.S3_BUCKET_NAME = "test-bucket"
        mock_settings.S3_REGION = "us-east-1"
        mock_settings.S3_USE_SSL = False
        
        mock_s3_client = MagicMock()
        error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'Not found'}}
        mock_s3_client.get_object.side_effect = ClientError(error_response, 'GetObject')
        mock_boto_client.return_value = mock_s3_client
        
        service = StorageService()
        result = service.download_file("test/path/nonexistent.txt")
        
        assert result is None
    
    @patch('app.services.storage_service.boto3.client')
    @patch('app.services.storage_service.settings')
    def test_delete_file_success(self, mock_settings, mock_boto_client):
        """Test successful file deletion."""
        mock_settings.MINIO_ENDPOINT = None
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        mock_settings.MINIO_ACCESS_KEY = None
        mock_settings.MINIO_SECRET_KEY = None
        mock_settings.MINIO_USE_SSL = False
        
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        
        service = StorageService()
        result = service.delete_file("test/path/file.txt")
        
        assert result is True
        call_kwargs = mock_s3_client.delete_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "test/path/file.txt"
    
    @patch('app.services.storage_service.boto3.client')
    @patch('app.services.storage_service.settings')
    def test_file_exists_true(self, mock_settings, mock_boto_client):
        """Test checking if file exists (exists)."""
        mock_settings.MINIO_ENDPOINT = None
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        mock_settings.MINIO_ACCESS_KEY = None
        mock_settings.MINIO_SECRET_KEY = None
        mock_settings.MINIO_USE_SSL = False
        
        mock_s3_client = MagicMock()
        mock_s3_client.head_object.return_value = {}  # File exists
        mock_boto_client.return_value = mock_s3_client
        
        service = StorageService()
        result = service.file_exists("test/path/file.txt")
        
        assert result is True
        call_kwargs = mock_s3_client.head_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "test/path/file.txt"
    
    @patch('app.services.storage_service.boto3.client')
    @patch('app.services.storage_service.settings')
    def test_file_exists_false(self, mock_settings, mock_boto_client):
        """Test checking if file exists (doesn't exist)."""
        from botocore.exceptions import ClientError
        
        mock_settings.MINIO_ENDPOINT = None
        mock_settings.AWS_S3_BUCKET = "test-bucket"
        mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        mock_settings.MINIO_ACCESS_KEY = None
        mock_settings.MINIO_SECRET_KEY = None
        mock_settings.MINIO_USE_SSL = False
        
        mock_s3_client = MagicMock()
        error_response = {'Error': {'Code': '404', 'Message': 'Not found'}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, 'HeadObject')
        mock_boto_client.return_value = mock_s3_client
        
        service = StorageService()
        result = service.file_exists("test/path/nonexistent.txt")
        
        assert result is False

