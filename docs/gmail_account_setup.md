# Gmail 계정 등록 가이드

## 개요

Gmail 계정을 등록하여 이메일을 자동으로 수집할 수 있습니다. OAuth 2.0을 사용하여 안전하게 Gmail API 접근 권한을 획득합니다.

## 사전 요구사항

1. **사용자 로그인 완료**: 먼저 Google SSO로 사용자 로그인이 완료되어야 합니다.
   - `/api/v1/auth/google/login`으로 로그인
   - JWT 토큰 획득

2. **Google Cloud Console 설정**: Gmail API 접근을 위한 OAuth 클라이언트 설정
   - Gmail API 스코프 추가 필요
   - 리디렉션 URI 등록

## 단계별 가이드

### 1. Google Cloud Console에서 Gmail API 스코프 추가

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 프로젝트 선택
3. **"API 및 서비스" > "OAuth 동의 화면"** 이동
4. **"범위"** 섹션에서 다음 스코프 추가:
   - `https://www.googleapis.com/auth/gmail.readonly` - 이메일 읽기
   - `https://www.googleapis.com/auth/gmail.metadata` - 메타데이터 접근
5. **"저장"** 클릭

### 2. 리디렉션 URI 등록

1. **"API 및 서비스" > "사용자 인증 정보"** 이동
2. OAuth 2.0 클라이언트 ID 선택
3. **"승인된 리디렉션 URI"**에 추가:
   ```
   http://localhost:8000/api/v1/auth/email-accounts/gmail/callback
   ```
   (프로덕션에서는 실제 도메인으로 변경)

### 3. Gmail 계정 연결 API 호출

#### 방법 1: 브라우저에서 직접 접속

```
GET http://localhost:8000/api/v1/auth/email-accounts/gmail/connect?user_id={user_id}
```

**예시:**
```bash
# user_id는 로그인 시 받은 JWT 토큰에서 확인하거나, 
# 사용자 정보 조회 API로 확인
curl "http://localhost:8000/api/v1/auth/email-accounts/gmail/connect?user_id=1"
```

#### 방법 2: 프론트엔드에서 구현

```javascript
// React/Next.js 예시
const connectGmail = async (userId) => {
  const response = await fetch(
    `http://localhost:8000/api/v1/auth/email-accounts/gmail/connect?user_id=${userId}`
  );
  
  // 리다이렉트 URL로 이동
  if (response.redirected) {
    window.location.href = response.url;
  }
};
```

### 4. OAuth 인증 완료

1. 위 API 호출 시 Google OAuth 인증 화면으로 리다이렉트됩니다
2. Gmail 계정 선택 및 권한 승인
3. 자동으로 콜백 URL로 리다이렉트되며 계정이 등록됩니다

### 5. 등록 확인

#### API 응답 확인

콜백 후 다음과 같은 JSON 응답을 받습니다:

```json
{
  "email_account_id": 1,
  "email": "user@gmail.com",
  "message": "Gmail account connected successfully"
}
```

#### 데이터베이스 확인

```sql
-- MySQL에서 확인
SELECT * FROM email_accounts WHERE provider_type = 'gmail';
```

## API 엔드포인트

### Gmail 계정 연결 시작

```
GET /api/v1/auth/email-accounts/gmail/connect?user_id={user_id}
```

**파라미터:**
- `user_id` (required): 사용자 ID

**응답:**
- Google OAuth 인증 URL로 리다이렉트

### Gmail 계정 연결 콜백

```
GET /api/v1/auth/email-accounts/gmail/callback?code={code}&state={user_id}
```

**파라미터:**
- `code` (required): OAuth 인증 코드
- `state` (required): 사용자 ID

**응답:**
```json
{
  "email_account_id": 1,
  "email": "user@gmail.com",
  "message": "Gmail account connected successfully"
}
```

## 문제 해결

### 1. "redirect_uri_mismatch" 오류

**원인**: Google Cloud Console의 리디렉션 URI와 설정이 일치하지 않음

**해결**:
- Google Cloud Console에서 정확한 URI 확인
- `.env`의 `API_BASE_URL` 확인
- 정확한 형식: `http://localhost:8000/api/v1/auth/email-accounts/gmail/callback`

### 2. "access_denied" 오류

**원인**: 사용자가 권한 승인을 거부했거나, 테스트 사용자로 등록되지 않음

**해결**:
- OAuth 동의 화면에서 테스트 사용자 추가 확인
- 사용자가 올바른 Google 계정으로 로그인했는지 확인

### 3. "invalid_grant" 오류

**원인**: 인증 코드가 만료되었거나 이미 사용됨

**해결**:
- 다시 연결 프로세스 시작
- 인증 코드는 한 번만 사용 가능

### 4. 계정이 등록되지 않음

**원인**: 데이터베이스 연결 문제 또는 사용자 ID 오류

**해결**:
- 데이터베이스 연결 확인
- 사용자 ID가 올바른지 확인
- 로그 확인: `logs/app_*.log`

## 테스트

### 1. 수동 테스트

```bash
# 1. 사용자 로그인 (JWT 토큰 획득)
curl "http://localhost:8000/api/v1/auth/google/login"

# 2. Gmail 계정 연결 시작
curl "http://localhost:8000/api/v1/auth/email-accounts/gmail/connect?user_id=1"

# 3. 브라우저에서 Google 인증 완료 후 콜백 확인
```

### 2. Celery Task로 이메일 가져오기 테스트

```python
from app.tasks.email_tasks import fetch_emails_for_account

# 등록된 Gmail 계정 ID로 이메일 가져오기
result = fetch_emails_for_account.delay(account_id=1)
print(result.get())
```

## 다음 단계

계정이 등록되면:

1. **자동 수집 설정**: Celery Beat 스케줄러가 주기적으로 이메일을 가져옵니다
2. **수동 수집**: `fetch_emails_for_account.delay(account_id)` 호출
3. **모든 계정 수집**: `fetch_all_accounts_emails.delay()` 호출

## 보안 주의사항

1. **프로덕션 환경**:
   - HTTPS 필수
   - OAuth 토큰 암호화 저장 권장
   - 리디렉션 URI를 실제 도메인으로 변경

2. **토큰 관리**:
   - 토큰은 자동으로 갱신됩니다
   - 만료된 토큰은 자동으로 refresh token으로 갱신

3. **권한**:
   - Gmail 읽기 전용 권한만 요청 (`gmail.readonly`)
   - 이메일 삭제/수정 권한은 요청하지 않음

