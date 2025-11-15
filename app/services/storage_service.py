"""Storage service for MinIO/S3 using boto3."""

import os
import re
from io import BytesIO
from typing import BinaryIO, List, Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from loguru import logger

from app.core.config import settings


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    if not filename:
        return "attachment"
    
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # Remove or replace special characters
    filename = re.sub(r'[<>:"|?*]', '_', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Limit length (preserve extension)
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        max_name_length = 200 - len(ext)
        filename = name[:max_name_length] + ext
    
    # Ensure filename is not empty
    if not filename:
        filename = "attachment"
    
    return filename


def get_email_storage_path(user_id: int, email_id: int) -> str:
    """
    Get base storage path for email.
    
    Args:
        user_id: User ID
        email_id: Email ID
        
    Returns:
        Base path: users/{user_id}/emails/{email_id}
    """
    return f"users/{user_id}/emails/{email_id}"


def get_raw_mime_path(user_id: int, email_id: int) -> str:
    """
    Get storage path for raw MIME file.
    
    Args:
        user_id: User ID
        email_id: Email ID
        
    Returns:
        Full path: users/{user_id}/emails/{email_id}/raw.mime
    """
    return f"{get_email_storage_path(user_id, email_id)}/raw.mime"


def get_attachment_path(
    user_id: int, 
    email_id: int, 
    index: int, 
    filename: str
) -> str:
    """
    Get storage path for attachment.
    
    Args:
        user_id: User ID
        email_id: Email ID
        index: Attachment index (0-based)
        filename: Original filename
        
    Returns:
        Full path: users/{user_id}/emails/{email_id}/attachments/{index}_{filename}
    """
    sanitized = sanitize_filename(filename)
    base_path = get_email_storage_path(user_id, email_id)
    return f"{base_path}/attachments/{index}_{sanitized}"


class StorageService:
    """Storage service for MinIO/S3 using boto3."""
    
    def __init__(self):
        """Initialize storage service with boto3 client."""
        self.bucket_name = settings.AWS_S3_BUCKET or "email-agent"
        
        # Determine if using MinIO or AWS S3
        if settings.MINIO_ENDPOINT:
            # MinIO configuration
            # Ensure endpoint doesn't have trailing slash and uses API port (9000)
            endpoint = settings.MINIO_ENDPOINT.rstrip('/')
            # Validate endpoint format
            if not endpoint.startswith(('http://', 'https://')):
                logger.warning(f"MinIO endpoint should start with http:// or https://, got: {endpoint}")
                endpoint = f"http://{endpoint}"
            
            # Warn if using console port (9001) instead of API port (9000)
            if ':9001' in endpoint:
                logger.warning(
                    f"MinIO endpoint uses console port (9001). "
                    f"S3 API requests must use API port (9000). "
                    f"Current endpoint: {endpoint}"
                )
            
            self.s3_client = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=settings.MINIO_ACCESS_KEY or settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.MINIO_SECRET_KEY or settings.AWS_SECRET_ACCESS_KEY,
                region_name='ap-northeast-2',  # Default region
                use_ssl=settings.MINIO_USE_SSL
            )
        else:
            # AWS S3 configuration
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name='ap-northeast-2',
            )
        
        # Don't check bucket existence on init - do it lazily when needed
        # This prevents Connection refused errors if MinIO is not running
        self._bucket_checked = False
    
    def _ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, create if it doesn't."""
        # Skip if already checked
        if self._bucket_checked:
            return
        
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.debug(f"Bucket '{self.bucket_name}' already exists")
            self._bucket_checked = True
        except (ClientError, BotoCoreError) as e:
            # Check if it's a connection error
            error_str = str(e).lower()
            if 'connection refused' in error_str or 'connection' in error_str:
                logger.warning(
                    f"Cannot connect to MinIO/S3 at {settings.MINIO_ENDPOINT or 'AWS S3'}. "
                    f"Storage operations will fail. Please ensure MinIO is running."
                )
                # Don't raise - allow the service to continue (storage operations will fail gracefully)
                return
            
            error_code = e.response.get('Error', {}).get('Code', '') if hasattr(e, 'response') else ''
            error_message = str(e).lower()
            
            # Check for common MinIO errors
            if 'bad request' in error_message or '400' in error_message or error_code == '400':
                logger.error(
                    f"MinIO Bad Request error when checking bucket '{self.bucket_name}'. Please check:\n"
                    f"  1. MinIO endpoint is correct: {settings.MINIO_ENDPOINT}\n"
                    f"  2. Endpoint uses API port (9000), not console port (9001)\n"
                    f"  3. MinIO server is running and accessible\n"
                    f"  4. Credentials are correct (MINIO_ACCESS_KEY, MINIO_SECRET_KEY)"
                )
                return
            
            if 'invalidargument' in error_message or 'api port' in error_message:
                logger.error(
                    f"MinIO API port error: {e}\n"
                    f"Please ensure MINIO_ENDPOINT uses API port (9000), not console port (9001).\n"
                    f"Current endpoint: {settings.MINIO_ENDPOINT}"
                )
                return
            
            if error_code == '404' or 'notfound' in error_message:
                # Bucket doesn't exist, create it
                try:
                    if settings.MINIO_ENDPOINT:
                        # MinIO: create bucket (no region needed)
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        # AWS S3: create bucket with region
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': 'ap-northeast-2'}
                        )
                    logger.info(f"Created bucket '{self.bucket_name}'")
                    self._bucket_checked = True
                except (ClientError, BotoCoreError) as create_error:
                    logger.error(f"Failed to create bucket '{self.bucket_name}': {create_error}")
                    # Don't raise - allow the service to continue
                    return
            else:
                logger.error(
                    f"Error checking bucket '{self.bucket_name}': {e}\n"
                    f"Error code: {error_code}\n"
                    f"Please verify MinIO is running at {settings.MINIO_ENDPOINT}"
                )
                # Don't raise - allow the service to continue
                return
    
    def upload_file(
        self, 
        file_path: str, 
        file_data: bytes | BinaryIO,
        content_type: Optional[str] = None
    ) -> bool:
        """
        Upload a file to storage.
        
        Args:
            file_path: Storage path (e.g., users/1/emails/100/raw.mime)
            file_data: File data as bytes or file-like object
            content_type: MIME type of the file
            
        Returns:
            True if successful, False otherwise
        """
        # Ensure bucket exists before upload
        self._ensure_bucket_exists()
        
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            if isinstance(file_data, bytes):
                file_obj = BytesIO(file_data)
            else:
                file_obj = file_data
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                file_path,
                ExtraArgs=extra_args
            )
            logger.debug(f"Uploaded file to '{file_path}'")
            return True
        except (ClientError, BotoCoreError) as e:
            error_str = str(e).lower()
            error_code = e.response.get('Error', {}).get('Code', '') if hasattr(e, 'response') else ''
            
            if 'connection refused' in error_str or 'connection' in error_str:
                logger.warning(
                    f"Cannot upload file '{file_path}': MinIO/S3 connection failed. "
                    f"Please ensure MinIO is running at {settings.MINIO_ENDPOINT or 'AWS S3'}"
                )
            elif 'invalidargument' in error_str or 'api port' in error_str:
                logger.error(
                    f"MinIO API port error when uploading '{file_path}': {e}\n"
                    f"Please ensure MINIO_ENDPOINT uses API port (9000), not console port (9001).\n"
                    f"Current endpoint: {settings.MINIO_ENDPOINT}"
                )
            elif 'bad request' in error_str or error_code == '400':
                logger.error(
                    f"MinIO Bad Request when uploading '{file_path}': {e}\n"
                    f"Please check MinIO endpoint and credentials."
                )
            else:
                logger.error(f"Failed to upload file '{file_path}': {e}")
            return False
    
    def download_file(self, file_path: str) -> Optional[bytes]:
        """
        Download a file from storage.
        
        Args:
            file_path: Storage path
            
        Returns:
            File data as bytes, or None if error
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            return response['Body'].read()
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                logger.warning(f"File not found: '{file_path}'")
            else:
                logger.error(f"Failed to download file '{file_path}': {e}")
            return None
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_path: Storage path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            logger.debug(f"Deleted file '{file_path}'")
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to delete file '{file_path}': {e}")
            return False
    
    def delete_directory(self, directory_path: str) -> bool:
        """
        Delete a directory and all its contents from storage.
        
        Args:
            directory_path: Directory path (e.g., users/1/emails/100)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory path ends with /
            if not directory_path.endswith('/'):
                directory_path += '/'
            
            # List all objects with this prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=directory_path)
            
            deleted_count = 0
            for page in pages:
                if 'Contents' in page:
                    objects = [{'Key': obj['Key']} for obj in page['Contents']]
                    if objects:
                        self.s3_client.delete_objects(
                            Bucket=self.bucket_name,
                            Delete={'Objects': objects}
                        )
                        deleted_count += len(objects)
            
            logger.info(f"Deleted directory '{directory_path}' ({deleted_count} objects)")
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to delete directory '{directory_path}': {e}")
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            file_path: Storage path
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                return False
            logger.error(f"Error checking file existence '{file_path}': {e}")
            return False
    
    def list_files(self, prefix: str) -> List[str]:
        """
        List all files with the given prefix.
        
        Args:
            prefix: Path prefix (e.g., users/1/emails/)
            
        Returns:
            List of file paths
        """
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            files = []
            for page in pages:
                if 'Contents' in page:
                    files.extend([obj['Key'] for obj in page['Contents']])
            
            return files
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to list files with prefix '{prefix}': {e}")
            return []
    
    # Convenience methods for email storage
    
    def save_raw_mime(
        self, 
        user_id: int, 
        email_id: int, 
        mime_data: bytes
    ) -> Optional[str]:
        """
        Save raw MIME file for an email.
        
        Args:
            user_id: User ID
            email_id: Email ID
            mime_data: Raw MIME data as bytes
            
        Returns:
            Storage path if successful, None otherwise
        """
        path = get_raw_mime_path(user_id, email_id)
        if self.upload_file(path, mime_data, content_type='message/rfc822'):
            return path
        return None
    
    def save_attachment(
        self,
        user_id: int,
        email_id: int,
        index: int,
        filename: str,
        attachment_data: bytes,
        content_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Save an attachment file.
        
        Args:
            user_id: User ID
            email_id: Email ID
            index: Attachment index (0-based)
            filename: Original filename
            attachment_data: Attachment data as bytes
            content_type: MIME type of the attachment
            
        Returns:
            Storage path if successful, None otherwise
        """
        path = get_attachment_path(user_id, email_id, index, filename)
        if self.upload_file(path, attachment_data, content_type=content_type):
            return path
        return None
    
    def get_raw_mime(self, user_id: int, email_id: int) -> Optional[bytes]:
        """
        Get raw MIME file for an email.
        
        Args:
            user_id: User ID
            email_id: Email ID
            
        Returns:
            Raw MIME data as bytes, or None if not found
        """
        path = get_raw_mime_path(user_id, email_id)
        return self.download_file(path)
    
    def get_attachment(
        self,
        user_id: int,
        email_id: int,
        index: int,
        filename: str
    ) -> Optional[bytes]:
        """
        Get an attachment file.
        
        Args:
            user_id: User ID
            email_id: Email ID
            index: Attachment index (0-based)
            filename: Original filename
            
        Returns:
            Attachment data as bytes, or None if not found
        """
        path = get_attachment_path(user_id, email_id, index, filename)
        return self.download_file(path)
    
    def delete_email_directory(self, user_id: int, email_id: int) -> bool:
        """
        Delete all files for an email (raw MIME and attachments).
        
        Args:
            user_id: User ID
            email_id: Email ID
            
        Returns:
            True if successful, False otherwise
        """
        path = get_email_storage_path(user_id, email_id)
        return self.delete_directory(path)
    
    def delete_user_directory(self, user_id: int) -> bool:
        """
        Delete all files for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        path = f"users/{user_id}"
        return self.delete_directory(path)


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get singleton instance of StorageService."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service

