# 보안 감사 보고서

## 최근 커밋된 보안 관련 코드 검토

### ✅ 안전한 부분

1. **환경 변수 사용**
   - 모든 민감한 정보(비밀번호, API 키, 토큰)가 환경 변수에서 로드됨
   - 하드코딩된 비밀번호나 API 키 없음
   - `app/core/config.py`에서 `Optional[str] = None`로 안전하게 처리

2. **JWT 토큰 처리**
   - `JWT_SECRET_KEY`가 환경 변수에서 로드됨
   - 토큰 생성 시 만료 시간(`exp`) 및 발급 시간(`iat`) 포함
   - HS256 알고리즘 사용 (표준)

3. **OAuth 클라이언트 정보**
   - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` 환경 변수 사용
   - 코드에 하드코딩되지 않음

### ⚠️ 주의 필요 사항

1. **OAuth 토큰 저장 (프로덕션)**
   ```python
   # app/services/auth_service.py
   user.oauth_access_token = credentials.token
   user.oauth_refresh_token = credentials.refresh_token
   ```
   - **현재**: DB에 평문으로 저장
   - **권장**: 프로덕션에서는 암호화 저장 필요
   - **위치**: `app/models/user.py`의 `oauth_access_token`, `oauth_refresh_token` 필드

2. **JWT 토큰 만료 시간**
   ```python
   # app/core/config.py
   JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
   ```
   - **현재**: 7일 (매우 길음)
   - **권장**: 프로덕션에서는 더 짧게 설정 (예: 1시간, refresh token으로 갱신)

3. **기본값 설정**
   ```python
   # app/core/config.py
   DB_PASSWORD: str = ""  # 빈 문자열 기본값
   API_BASE_URL: str = "http://localhost:8000"  # HTTP 기본값
   ```
   - **주의**: 프로덕션에서는 반드시 환경 변수로 설정
   - **권장**: 프로덕션에서는 HTTPS 필수

4. **에러 메시지 노출**
   ```python
   # app/api/auth.py
   raise HTTPException(status_code=400, detail=str(e))
   ```
   - **주의**: 상세한 에러 메시지가 클라이언트에 노출될 수 있음
   - **권장**: 프로덕션에서는 일반적인 메시지만 반환

### 🔒 보안 개선 권장사항

#### 1. OAuth 토큰 암호화 (프로덕션)

```python
# app/core/security.py에 추가
from cryptography.fernet import Fernet
import os

def encrypt_token(token: str) -> str:
    """Encrypt OAuth token before storing."""
    key = os.getenv("ENCRYPTION_KEY")
    f = Fernet(key)
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt OAuth token after retrieving."""
    key = os.getenv("ENCRYPTION_KEY")
    f = Fernet(key)
    return f.decrypt(encrypted_token.encode()).decode()
```

#### 2. 환경 변수 검증 강화

```python
# app/core/config.py에 추가
from pydantic import validator

@validator('JWT_SECRET_KEY')
def validate_jwt_secret(cls, v):
    if not v:
        raise ValueError("JWT_SECRET_KEY must be set")
    if len(v) < 32:
        raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
    return v
```

#### 3. 프로덕션 설정 분리

```python
# app/core/config.py
if settings.ENVIRONMENT == "prod":
    if not settings.JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY is required in production")
    if settings.API_BASE_URL.startswith("http://"):
        raise ValueError("HTTPS is required in production")
```

#### 4. 에러 메시지 일반화

```python
# app/api/auth.py
except Exception as e:
    logger.error(f"Google OAuth callback error: {e}")
    if settings.DEBUG:
        raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail="Authentication failed")
```

### 📋 체크리스트

- [x] 하드코딩된 비밀번호 없음
- [x] 환경 변수 사용
- [x] JWT 토큰 만료 시간 설정
- [ ] OAuth 토큰 암호화 (프로덕션)
- [ ] 환경 변수 검증 강화
- [ ] 프로덕션 설정 분리
- [ ] 에러 메시지 일반화
- [ ] HTTPS 강제 (프로덕션)

### 결론

**현재 상태**: 개발 환경에서는 안전함
- 모든 민감한 정보가 환경 변수로 관리됨
- 하드코딩된 비밀번호나 API 키 없음

**프로덕션 배포 전 필수 작업**:
1. OAuth 토큰 암호화 구현
2. JWT 토큰 만료 시간 단축
3. 환경 변수 검증 강화
4. HTTPS 강제
5. 에러 메시지 일반화

