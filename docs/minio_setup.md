# MinIO 설정 가이드

MinIO는 S3 호환 오브젝트 스토리지로, 이메일 원본 MIME 파일을 저장하는 데 사용됩니다.

## 1. MinIO 설치 및 실행

### 방법 1: Docker를 사용한 MinIO 실행 (권장)

```bash
# MinIO 서버 실행
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin123" \
  -v /path/to/minio/data:/data \
  minio/minio server /data --console-address ":9001"
```

**접속 정보:**
- **API 엔드포인트**: `http://localhost:9000`
- **콘솔 UI**: `http://localhost:9001`
- **기본 사용자명**: `minioadmin`
- **기본 비밀번호**: `minioadmin123`

### 방법 2: Docker Compose 사용

`docker-compose.yaml`에 추가:

```yaml
services:
  minio:
    image: minio/minio
    container_name: minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

volumes:
  minio_data:
```

실행:
```bash
docker-compose up -d minio
```

### 방법 3: 직접 설치 (macOS)

```bash
# Homebrew로 설치
brew install minio/stable/minio

# MinIO 서버 실행 (백그라운드)
# 방법 1: nohup 사용
nohup minio server /path/to/data --console-address ":9001" > minio.log 2>&1 &

# 방법 2: launchd 사용 (macOS 서비스로 등록)
# ~/Library/LaunchAgents/com.minio.server.plist 파일 생성
cat > ~/Library/LaunchAgents/com.minio.server.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.minio.server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/minio</string>
        <string>server</string>
        <string>/path/to/minio/data</string>
        <string>--console-address</string>
        <string>:9001</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/minio.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/minio.error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>MINIO_ROOT_USER</key>
        <string>your-root-user</string>
        <key>MINIO_ROOT_PASSWORD</key>
        <string>your-root-password</string>
    </dict>
</dict>
</plist>
EOF

# 서비스 로드 및 시작
launchctl load ~/Library/LaunchAgents/com.minio.server.plist
launchctl start com.minio.server

# 서비스 중지
# launchctl stop com.minio.server
# launchctl unload ~/Library/LaunchAgents/com.minio.server.plist
```

**백그라운드 실행 방법 요약:**

1. **nohup 사용** (간단한 방법):
   ```bash
   nohup minio server /path/to/data --console-address ":9001" > minio.log 2>&1 &
   ```

2. **tmux/screen 사용**:
   ```bash
   # tmux 세션 생성
   tmux new -s minio
   minio server /path/to/data --console-address ":9001"
   # Ctrl+B, D로 detach
   
   # 다시 접속
   tmux attach -t minio
   ```

3. **launchd 사용** (macOS 서비스, 권장):
   - 위의 plist 파일 생성 후 `launchctl load` 실행
   - 시스템 재시작 후에도 자동 실행

## 2. MinIO 콘솔에서 버킷 생성

1. 브라우저에서 `http://localhost:9001` 접속
2. `minioadmin` / `minioadmin123` 로그인
3. **Buckets** 메뉴 클릭
4. **Create Bucket** 클릭
5. 버킷 이름 입력: `email-mime` (또는 원하는 이름)
6. **Create Bucket** 클릭

## 3. Python 클라이언트 설정

### 패키지 설치

`requirements.txt`에 추가:

```txt
boto3  # AWS S3 호환 클라이언트 (MinIO와 호환)
# 또는
minio  # MinIO 전용 클라이언트
```

설치:
```bash
conda run -n ai pip install boto3
# 또는
conda run -n ai pip install minio
```

### 환경 변수 설정

`.env` 파일에 추가:

```env
# MinIO / S3 Storage
STORAGE_TYPE=minio  # 또는 's3' for AWS S3
STORAGE_ENDPOINT=http://localhost:9000
STORAGE_ACCESS_KEY=minioadmin
STORAGE_SECRET_KEY=minioadmin123
STORAGE_BUCKET=email-mime
STORAGE_REGION=us-east-1  # MinIO는 기본값 사용
STORAGE_USE_SSL=false  # 로컬 개발 시 false
```

## 4. Python 코드에서 MinIO 사용

### 방법 1: boto3 사용 (S3 호환)

`app/core/storage.py` 생성:

```python
"""Storage utilities for MinIO/S3."""

import boto3
from botocore.exceptions import ClientError
from loguru import logger
from typing import Optional, BinaryIO

from app.core.config import settings


class StorageClient:
    """Storage client for MinIO/S3."""

    def __init__(self):
        """Initialize storage client."""
        self.client = boto3.client(
            's3',
            endpoint_url=settings.STORAGE_ENDPOINT,
            aws_access_key_id=settings.STORAGE_ACCESS_KEY,
            aws_secret_access_key=settings.STORAGE_SECRET_KEY,
            region_name=settings.STORAGE_REGION,
            use_ssl=settings.STORAGE_USE_SSL,
        )
        self.bucket = settings.STORAGE_BUCKET

    def upload_file(
        self,
        file_data: bytes,
        object_key: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload file to storage.

        Args:
            file_data: File data as bytes
            object_key: Object key (path) in bucket
            content_type: Content type (MIME type)

        Returns:
            Object URL
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            self.client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=file_data,
                **extra_args
            )

            # Return object URL
            url = f"{settings.STORAGE_ENDPOINT}/{self.bucket}/{object_key}"
            logger.info(f"Uploaded file to storage: {object_key}")
            return url

        except ClientError as e:
            logger.error(f"Failed to upload file to storage: {e}")
            raise

    def download_file(self, object_key: str) -> bytes:
        """
        Download file from storage.

        Args:
            object_key: Object key (path) in bucket

        Returns:
            File data as bytes
        """
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=object_key
            )
            return response['Body'].read()

        except ClientError as e:
            logger.error(f"Failed to download file from storage: {e}")
            raise

    def delete_file(self, object_key: str) -> bool:
        """
        Delete file from storage.

        Args:
            object_key: Object key (path) in bucket

        Returns:
            True if deleted, False otherwise
        """
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=object_key
            )
            logger.info(f"Deleted file from storage: {object_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete file from storage: {e}")
            return False

    def file_exists(self, object_key: str) -> bool:
        """
        Check if file exists in storage.

        Args:
            object_key: Object key (path) in bucket

        Returns:
            True if exists, False otherwise
        """
        try:
            self.client.head_object(
                Bucket=self.bucket,
                Key=object_key
            )
            return True

        except ClientError:
            return False


# Global instance
_storage_client: Optional[StorageClient] = None


def get_storage_client() -> StorageClient:
    """Get global storage client instance."""
    global _storage_client
    if _storage_client is None:
        _storage_client = StorageClient()
    return _storage_client
```

### 방법 2: minio 라이브러리 사용

```python
"""Storage utilities using MinIO library."""

from minio import Minio
from minio.error import S3Error
from loguru import logger
from typing import Optional
from urllib.parse import urlparse

from app.core.config import settings


class StorageClient:
    """Storage client using MinIO library."""

    def __init__(self):
        """Initialize MinIO client."""
        endpoint = urlparse(settings.STORAGE_ENDPOINT)
        self.client = Minio(
            endpoint.netloc,
            access_key=settings.STORAGE_ACCESS_KEY,
            secret_key=settings.STORAGE_SECRET_KEY,
            secure=settings.STORAGE_USE_SSL,
        )
        self.bucket = settings.STORAGE_BUCKET
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure bucket exists, create if not."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created bucket: {self.bucket}")
        except S3Error as e:
            logger.error(f"Failed to create bucket: {e}")
            raise

    def upload_file(
        self,
        file_data: bytes,
        object_key: str,
        content_type: Optional[str] = None
    ) -> str:
        """Upload file to MinIO."""
        from io import BytesIO

        try:
            self.client.put_object(
                self.bucket,
                object_key,
                BytesIO(file_data),
                length=len(file_data),
                content_type=content_type or 'application/octet-stream'
            )

            url = f"{settings.STORAGE_ENDPOINT}/{self.bucket}/{object_key}"
            logger.info(f"Uploaded file to MinIO: {object_key}")
            return url

        except S3Error as e:
            logger.error(f"Failed to upload file to MinIO: {e}")
            raise

    def download_file(self, object_key: str) -> bytes:
        """Download file from MinIO."""
        try:
            response = self.client.get_object(self.bucket, object_key)
            data = response.read()
            response.close()
            response.release_conn()
            return data

        except S3Error as e:
            logger.error(f"Failed to download file from MinIO: {e}")
            raise

    def delete_file(self, object_key: str) -> bool:
        """Delete file from MinIO."""
        try:
            self.client.remove_object(self.bucket, object_key)
            logger.info(f"Deleted file from MinIO: {object_key}")
            return True

        except S3Error as e:
            logger.error(f"Failed to delete file from MinIO: {e}")
            return False

    def file_exists(self, object_key: str) -> bool:
        """Check if file exists in MinIO."""
        try:
            self.client.stat_object(self.bucket, object_key)
            return True
        except S3Error:
            return False
```

## 5. 이메일 원본 MIME 저장 예시

`app/tasks/email_tasks.py`에서 사용:

```python
from app.core.storage import get_storage_client

# 이메일 저장 시
def save_email_mime(email_id: int, raw_mime: bytes):
    """Save email raw MIME to storage."""
    storage = get_storage_client()
    
    # Object key: emails/{email_id}/raw.mime
    object_key = f"emails/{email_id}/raw.mime"
    
    # Upload to MinIO
    url = storage.upload_file(
        file_data=raw_mime,
        object_key=object_key,
        content_type="message/rfc822"
    )
    
    # Update email record with storage path
    email.raw_mime_storage_path = object_key
    db.commit()
    
    return url
```

## 6. config.py에 설정 추가

`app/core/config.py`에 추가:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Storage (MinIO/S3)
    STORAGE_TYPE: str = "minio"  # 'minio' or 's3'
    STORAGE_ENDPOINT: str = "http://localhost:9000"
    STORAGE_ACCESS_KEY: str = "minioadmin"
    STORAGE_SECRET_KEY: str = "minioadmin123"
    STORAGE_BUCKET: str = "email-mime"
    STORAGE_REGION: str = "us-east-1"
    STORAGE_USE_SSL: bool = False
```

## 7. 테스트

### MinIO 연결 테스트

```python
from app.core.storage import get_storage_client

# 테스트
storage = get_storage_client()

# 파일 업로드 테스트
test_data = b"test email content"
url = storage.upload_file(
    file_data=test_data,
    object_key="test/email.mime",
    content_type="message/rfc822"
)
print(f"Uploaded to: {url}")

# 파일 다운로드 테스트
downloaded = storage.download_file("test/email.mime")
print(f"Downloaded: {downloaded}")

# 파일 존재 확인
exists = storage.file_exists("test/email.mime")
print(f"File exists: {exists}")

# 파일 삭제
deleted = storage.delete_file("test/email.mime")
print(f"Deleted: {deleted}")
```

## 8. 프로덕션 설정

프로덕션 환경에서는:

1. **보안 강화**:
   - 강력한 `MINIO_ROOT_PASSWORD` 사용
   - IAM 정책 설정
   - HTTPS 사용 (`STORAGE_USE_SSL=true`)

2. **AWS S3 사용**:
   ```env
   STORAGE_TYPE=s3
   STORAGE_ENDPOINT=https://s3.amazonaws.com
   STORAGE_ACCESS_KEY=<AWS_ACCESS_KEY>
   STORAGE_SECRET_KEY=<AWS_SECRET_KEY>
   STORAGE_BUCKET=email-mime-prod
   STORAGE_REGION=ap-northeast-2
   STORAGE_USE_SSL=true
   ```

3. **백업 전략**:
   - 버킷 버전 관리 활성화
   - 크로스 리전 복제 설정
   - 정기적인 백업 스케줄

## 9. 문제 해결

### 연결 오류
- MinIO 서버가 실행 중인지 확인: `docker ps | grep minio`
- 포트가 올바른지 확인: `http://localhost:9000`
- 방화벽 설정 확인

### 인증 오류
- `STORAGE_ACCESS_KEY`와 `STORAGE_SECRET_KEY` 확인
- MinIO 콘솔에서 사용자 정보 확인

### 버킷 없음 오류
- MinIO 콘솔에서 버킷 생성 확인
- 코드에서 자동 생성 로직 추가 (minio 라이브러리 사용 시)

## 참고 자료

- [MinIO 공식 문서](https://min.io/docs/)
- [boto3 문서](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [MinIO Python SDK](https://min.io/docs/minio/linux/developers/python/API.html)

