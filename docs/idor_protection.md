# IDOR 공격 방지 (ID 인코딩)

## 개요

IDOR (Insecure Direct Object Reference) 공격을 방지하기 위해 URL에 노출되는 ID를 base62 인코딩합니다.

## 구현 방법

### 1. Base62 인코딩 사용

- **Base62**: 0-9, a-z, A-Z를 사용하는 62진법 인코딩
- 리소스 타입 prefix를 추가하여 타입 안전성 보장
- URL-safe하며 추가 키 관리 불필요

### 2. 인코딩 형식

각 리소스 타입에 따라 prefix를 사용:

- `e` + base62(id): Email ID
- `a` + base62(id): Account ID
- `u` + base62(id): User ID

예시:
```
원본 ID: 123
인코딩된 ID: e1Z (email ID인 경우)
```

### 3. 사용 예시

#### 백엔드 API 엔드포인트

```python
from app.core.id_encryption import decrypt_email_id, encrypt_email_id

@router.get("/{encoded_email_id}")
async def get_email(
    encoded_email_id: str,  # base62 인코딩된 ID
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # 인코딩된 ID를 디코딩
        email_id = decrypt_email_id(encoded_email_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid email ID")
    
    # 기존 로직...
    email = email_repo.get_email_by_id(email_id, current_user.id)
    
    # 응답에서 ID를 인코딩해서 반환
    return {
        "id": encrypt_email_id(email.id),
        # ... 기타 필드
    }
```

#### 프론트엔드

```typescript
// API 응답에서 인코딩된 ID 사용
const emailId = email.id; // 이미 인코딩된 ID

// API 호출 시 인코딩된 ID 사용
await emailApi.getEmailById(emailId);
```

## 적용 대상

다음 리소스의 ID를 인코딩합니다:

1. **Email ID** (`/api/v1/email/{email_id}`)
2. **Email Account ID** (`/api/v1/auth/email-accounts`, query params)
3. **User ID** (필요시)

## 보안 고려사항

1. **인코딩의 한계**
   - Base62는 암호화가 아닌 인코딩이므로, 역산 가능
   - 순차적 ID 공격을 어렵게 만들지만 완전한 보안은 아님
   - 추가 보안 레이어로 권한 체크 필수

2. **추가 보안 레이어**
   - ID 인코딩은 추가 보안 레이어일 뿐
   - 여전히 `get_current_user`로 권한 체크 필요
   - 인코딩된 ID가 유출되어도 권한 체크로 보호됨

3. **성능**
   - Base62 인코딩/디코딩은 매우 빠름
   - 추가 오버헤드 최소

## 마이그레이션 전략

기존 integer ID를 인코딩된 ID로 전환:

1. **단계적 적용**
   - 새 엔드포인트부터 인코딩된 ID 사용
   - 기존 엔드포인트는 호환성 유지 (양쪽 지원)

2. **응답 변환**
   - API 응답에서 모든 ID를 인코딩해서 반환
   - 프론트엔드는 인코딩된 ID를 그대로 사용

3. **URL 파라미터**
   - 경로 파라미터: `/{encoded_id}`
   - 쿼리 파라미터: `?account_id={encoded_id}`

## 예시: 인코딩된 ID

```
원본 ID: 123
인코딩된 ID: e1Z (email ID인 경우)

원본 ID: 456
인코딩된 ID: a7k (account ID인 경우)
```

인코딩된 ID는 짧고 읽기 쉬우며, 순차적 ID 공격을 어렵게 만듭니다.
