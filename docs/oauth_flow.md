# OAuth 인증 플로우 설명

## 개요

이 시스템은 두 가지 레벨의 OAuth 인증을 사용합니다:

1. **User 레벨 OAuth**: 사용자 로그인 (Google, Naver 등)
2. **EmailAccount 레벨 OAuth**: 이메일 계정 연결 (Gmail API 접근 권한)

## 1. User 레벨 OAuth (사용자 로그인)

### 플로우

```
1. 사용자가 "Google로 로그인" 버튼 클릭
   ↓
2. GET /api/auth/google/login
   → Google OAuth URL로 리다이렉트
   ↓
3. 사용자가 Google에서 권한 승인
   ↓
4. GET /api/auth/google/callback?code=xxx
   → code를 access_token으로 교환
   → 사용자 정보 조회
   → DB에 User 저장/업데이트
   → JWT 토큰 발급 (선택)
   ↓
5. 프론트엔드로 리다이렉트 (토큰 포함)
```

### 언제 실행되는가?

- **초기 로그인 시**: 사용자가 처음 앱에 접속할 때
- **토큰 만료 시**: refresh_token으로 갱신
- **재로그인 시**: 사용자가 로그아웃 후 다시 로그인할 때

### 저장되는 정보

- `User` 테이블에 저장:
  - `oauth_provider`: "google"
  - `oauth_provider_user_id`: Google의 사용자 ID
  - `oauth_email`: Google 계정 이메일
  - `oauth_access_token`: Access token
  - `oauth_refresh_token`: Refresh token
  - `oauth_token_expires_at`: 만료 시간
  - `display_name`, `profile_image_url` 등

---

## 2. EmailAccount 레벨 OAuth (이메일 계정 연결)

### 플로우

```
1. 사용자가 "Gmail 계정 추가" 버튼 클릭
   ↓
2. GET /api/auth/email-accounts/gmail/connect
   → Gmail API OAuth URL로 리다이렉트
   (Gmail 읽기 권한 요청)
   ↓
3. 사용자가 Gmail 권한 승인
   ↓
4. GET /api/auth/email-accounts/gmail/callback?code=xxx
   → code를 access_token으로 교환
   → Gmail 계정 정보 조회
   → EmailAccount 생성 및 credentials 저장
   ↓
5. 프론트엔드로 리다이렉트
```

### 언제 실행되는가?

- **이메일 계정 추가 시**: 사용자가 새로운 이메일 계정을 연결할 때
- **토큰 갱신 시**: Gmail API 토큰이 만료되어 갱신이 필요할 때

### 저장되는 정보

- `EmailAccount` 테이블에 저장:
  - `user_id`: 연결된 User ID
  - `email_address`: Gmail 주소
  - `provider_type`: "gmail"
  - `credentials`: JSON 형태로 저장
    ```json
    {
      "access_token": "...",
      "refresh_token": "...",
      "token_expires_at": "2024-01-01T00:00:00Z",
      "token_uri": "https://oauth2.googleapis.com/token",
      "client_id": "...",
      "client_secret": "..."
    }
    ```

---

## Naver의 경우

Naver는 OAuth 2.0을 지원하지만, 이메일 수집은 **IMAP**을 사용합니다.

### User 레벨 (Naver 로그인)
- OAuth 2.0으로 사용자 로그인
- User 테이블에 저장

### EmailAccount 레벨 (Naver 이메일 연결)
- **IMAP 방식**: 사용자가 직접 ID/PW 입력
- 또는 Naver OAuth로 이메일 접근 권한 획득 (Naver API 지원 시)

---

## 구현 위치

### API 엔드포인트
- `app/api/auth.py`: OAuth 인증 엔드포인트
  - `/auth/google/login`
  - `/auth/google/callback`
  - `/auth/naver/login`
  - `/auth/naver/callback`
  - `/auth/email-accounts/gmail/connect`
  - `/auth/email-accounts/gmail/callback`

### 서비스 로직
- `app/services/auth_service.py`: OAuth 토큰 교환, 사용자 정보 조회
- `app/services/email_account_service.py`: EmailAccount 생성/업데이트

### 보안
- `app/core/security.py`: JWT 토큰 발급, 토큰 암호화

---

## 토큰 갱신

### User 레벨 토큰 갱신
- `oauth_refresh_token`을 사용하여 자동 갱신
- 만료 전에 백그라운드에서 갱신

### EmailAccount 레벨 토큰 갱신
- Gmail API 토큰 만료 시 자동 갱신
- Celery task에서 이메일 수집 전에 토큰 확인 및 갱신

