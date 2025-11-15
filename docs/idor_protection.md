# IDOR 공격 방지 (ID 암호화)

## 개요

IDOR (Insecure Direct Object Reference) 공격을 방지하기 위해 URL에 노출되는 ID를 암호화합니다.

## 구현 방법

### 1. Fernet 대칭 암호화 사용

- **Fernet**: AES 128 CBC + HMAC SHA256 기반의 안전한 대칭 암호화
- 리소스 타입과 ID를 함께 암호화하여 타입 안전성 보장
- URL-safe base64 인코딩으로 URL에 직접 사용 가능

### 2. 암호화 키 설정

`.env` 파일에 다음 중 하나를 설정:

```bash
# 방법 1: 별도의 암호화 키 설정 (권장)
ID_ENCRYPTION_KEY=<base64-encoded-32-byte-key>

# 방법 2: JWT_SECRET_KEY에서 자동 생성 (기본값)
JWT_SECRET_KEY=<your-secret-key>
```

**Fernet 키 생성 방법:**

터미널에서 다음 명령어 중 하나를 실행:

```bash
# 방법 1: Makefile 사용 (권장)
make generate-id-key

# 방법 2: conda 환경에서 직접 실행
conda run -n ai python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 방법 3: 일반 Python 환경
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

생성된 키를 `.env` 파일의 `ID_ENCRYPTION_KEY`에 설정:
```bash
ID_ENCRYPTION_KEY=<생성된-키>
```

### 3. 사용 예시

#### 백엔드 API 엔드포인트

```python
from app.core.id_encryption import decrypt_email_id, encrypt_email_id

@router.get("/{encrypted_email_id}")
async def get_email(
    encrypted_email_id: str,  # 암호화된 ID
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # 암호화된 ID를 복호화
        email_id = decrypt_email_id(encrypted_email_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid email ID")
    
    # 기존 로직...
    email = email_repo.get_email_by_id(email_id, current_user.id)
    
    # 응답에서 ID를 암호화해서 반환
    return {
        "id": encrypt_email_id(email.id),
        # ... 기타 필드
    }
```

#### 프론트엔드

```typescript
// API 응답에서 암호화된 ID 사용
const emailId = email.id; // 이미 암호화된 ID

// API 호출 시 암호화된 ID 사용
await emailApi.getEmailById(emailId);
```

## 적용 대상

다음 리소스의 ID를 암호화해야 합니다:

1. **Email ID** (`/api/v1/email/{email_id}`)
2. **Email Account ID** (`/api/v1/auth/email-accounts`, query params)
3. **User ID** (필요시)

## 보안 고려사항

1. **암호화 키 관리**
   - 프로덕션에서는 반드시 `ID_ENCRYPTION_KEY`를 별도로 설정
   - 키는 안전하게 보관하고 정기적으로 로테이션

2. **추가 보안 레이어**
   - ID 암호화는 추가 보안 레이어일 뿐
   - 여전히 `get_current_user`로 권한 체크 필요
   - 암호화된 ID가 유출되어도 권한 체크로 보호됨

3. **성능**
   - 암호화/복호화는 빠르지만, 대량 처리 시 고려 필요
   - 필요시 캐싱 고려

## 마이그레이션 전략

기존 integer ID를 암호화된 ID로 전환:

1. **단계적 적용**
   - 새 엔드포인트부터 암호화된 ID 사용
   - 기존 엔드포인트는 호환성 유지 (양쪽 지원)

2. **응답 변환**
   - API 응답에서 모든 ID를 암호화해서 반환
   - 프론트엔드는 암호화된 ID를 그대로 사용

3. **URL 파라미터**
   - 경로 파라미터: `/{encrypted_id}`
   - 쿼리 파라미터: `?account_id={encrypted_id}`

## 예시: 암호화된 ID

```
원본 ID: 123
암호화된 ID: gAAAAABl... (URL-safe base64, 약 44-88자)
```

암호화된 ID는 예측 불가능하며, 순차적 ID 공격을 방지합니다.

