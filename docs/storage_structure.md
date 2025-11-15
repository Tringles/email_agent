# MinIO Storage 디렉토리 구조

## 디렉토리 구조

```
email_agent/
├── users/
│   └── {user_id}/
│       └── emails/
│           └── {email_id}/
│               ├── raw.mime                    # 원본 MIME 파일
│               └── attachments/
│                   ├── 0_{sanitized_filename}  # 첨부파일 1
│                   ├── 1_{sanitized_filename}  # 첨부파일 2
│                   └── ...
```

### 예시

```
email_agent/
├── users/
│   └── 1/                    # user_id = 1
│       └── emails/
│           ├── 100/          # email_id = 100
│           │   ├── raw.mime
│           │   └── attachments/
│           │       ├── 0_report.pdf
│           │       └── 1_image.jpg
│           └── 101/          # email_id = 101
│               ├── raw.mime
│               └── attachments/
│                   └── 0_document.docx
```

## 경로 생성 규칙

### 원본 MIME 파일

```
users/{user_id}/emails/{email_id}/raw.mime
```

**예시:**
- `users/1/emails/100/raw.mime`
- `users/2/emails/250/raw.mime`

### 첨부파일

```
users/{user_id}/emails/{email_id}/attachments/{index}_{sanitized_filename}
```

**예시:**
- `users/1/emails/100/attachments/0_report.pdf`
- `users/1/emails/100/attachments/1_image.jpg`
- `users/2/emails/250/attachments/0_document.docx`

### 경로 구성 요소

- `{user_id}`: 사용자 ID (integer)
- `{email_id}`: 이메일 ID (integer)
- `{index}`: 첨부파일 순서 (0부터 시작)
- `{sanitized_filename}`: 안전하게 처리된 파일명

## 파일명 Sanitization

### 규칙

1. **경로 분리자 제거**: `/`, `\` → `_`로 치환
2. **특수문자 제거**: `<`, `>`, `:`, `"`, `|`, `?`, `*` → `_`로 치환
3. **길이 제한**: 최대 200자 (확장자 포함)
4. **인덱스 추가**: 중복 파일명 구분을 위해 `{index}_` 접두사 사용

### 구현 예시

```python
import re
import os

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
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
```

### 예시

| 원본 파일명 | Sanitized 파일명 |
|------------|-----------------|
| `report.pdf` | `report.pdf` |
| `document/file.docx` | `document_file.docx` |
| `image:test.jpg` | `image_test.jpg` |
| `very_long_filename_that_exceeds_200_characters_and_needs_to_be_truncated.pdf` | `very_long_filename_that_exceeds_200_characters_and_needs_to_be_truncated.pdf` (200자로 제한) |

## 경로 생성 함수

### Python 구현 예시

```python
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
```

## 데이터베이스 스키마

### Email 모델 필드

```python
# Storage paths
raw_mime_storage_path = Column(String(512), nullable=True)  # 원본 MIME 경로
attachment_storage_paths = Column(JSON, nullable=True)  # 첨부파일 경로 리스트
```

### Attachment 메타데이터 구조

```python
{
    "attachment_id": "gmail_attachment_id",  # Provider별 ID (Gmail: attachmentId)
    "filename": "report.pdf",
    "mime_type": "application/pdf",
    "size": 1024000,  # bytes
    "storage_path": "users/1/emails/100/attachments/0_report.pdf",  # MinIO 경로
    "index": 0  # 첨부파일 순서
}
```

### 저장 예시

```python
# Email 저장 시
email_data = {
    "email_account_id": account_id,
    "provider_message_id": message_id,
    # ... other fields ...
    "raw_mime_storage_path": "users/1/emails/100/raw.mime",
    "attachments": [
        {
            "attachment_id": "gmail_123",
            "filename": "report.pdf",
            "mime_type": "application/pdf",
            "size": 1024000,
            "storage_path": "users/1/emails/100/attachments/0_report.pdf",
            "index": 0
        },
        {
            "attachment_id": "gmail_124",
            "filename": "image.jpg",
            "mime_type": "image/jpeg",
            "size": 512000,
            "storage_path": "users/1/emails/100/attachments/1_image.jpg",
            "index": 1
        }
    ]
}
```

## 삭제 전략

### 이메일 삭제

#### Soft Delete (DB만 삭제 표시)
```python
email.is_deleted = True
# MinIO 데이터는 유지 (복구 가능)
```

#### Hard Delete (MinIO에서도 삭제)
```python
# 이메일 디렉토리 전체 삭제
storage_path = get_email_storage_path(user_id, email_id)
storage.delete_directory(storage_path)  # users/{user_id}/emails/{email_id} 전체 삭제
```

### 사용자 삭제

```python
# 사용자의 모든 이메일 데이터 삭제
storage.delete_directory(f"users/{user_id}")  # users/{user_id} 전체 삭제
```

### 첨부파일만 삭제

```python
# 특정 첨부파일만 삭제
attachment_path = "users/1/emails/100/attachments/0_report.pdf"
storage.delete_file(attachment_path)
```

## 장점

1. **보안**: 사용자별 데이터 분리로 권한 관리 용이
2. **관리**: 사용자별 백업/삭제/마이그레이션 용이
3. **확장성**: 사용자별 스토리지 사용량 추적 가능
4. **구조화**: 명확한 디렉토리 구조로 유지보수 용이
5. **성능**: 사용자별로 분산되어 성능 저하 최소화

## 주의사항

1. **파일명 길이**: MinIO/S3는 object key 길이 제한이 있음 (일반적으로 1024자)
2. **특수문자**: URL 인코딩이 필요한 경우 고려
3. **중복 파일명**: 인덱스를 사용하여 구분
4. **대소문자**: MinIO는 대소문자를 구분하므로 일관성 유지 필요

## 참고

- MinIO object key는 `/`를 경로 구분자로 사용
- 경로는 항상 `users/`로 시작
- 각 이메일은 독립적인 디렉토리를 가짐
- 첨부파일은 `attachments/` 하위에 저장
