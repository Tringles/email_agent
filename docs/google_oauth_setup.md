# Google OAuth 2.0 설정 가이드

## 1. Google Cloud Console 설정

### 1.1 프로젝트 생성

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 상단 프로젝트 선택 드롭다운 클릭
3. "새 프로젝트" 클릭
4. 프로젝트 이름 입력 (예: `email-agent`)
5. "만들기" 클릭

### 1.2 OAuth 동의 화면 설정

1. 좌측 메뉴에서 **"API 및 서비스" > "OAuth 동의 화면"** 선택
2. **사용자 유형** 선택:
   - **외부**: 일반 사용자용 (권장)
   - **내부**: Google Workspace 조직 내부용
3. **앱 정보** 입력:
   - 앱 이름: `Email AI Aggregator`
   - 사용자 지원 이메일: 본인 이메일
   - 앱 로고: 선택사항
   - 앱 도메인: 선택사항
   - 개발자 연락처 정보: 본인 이메일
4. **범위** 설정:
   - "범위 추가 또는 삭제" 클릭
   - 다음 범위 추가:
     - `openid`
     - `https://www.googleapis.com/auth/userinfo.email`
     - `https://www.googleapis.com/auth/userinfo.profile`
   - "업데이트" 클릭
5. **테스트 사용자** 추가 (외부 앱인 경우):
   - "테스트 사용자" 섹션에서 "사용자 추가"
   - 로그인할 Google 계정 이메일 추가
6. "저장 후 계속" 클릭하여 완료

### 1.3 OAuth 2.0 클라이언트 ID 생성

1. 좌측 메뉴에서 **"API 및 서비스" > "사용자 인증 정보"** 선택
2. 상단 **"+ 사용자 인증 정보 만들기" > "OAuth 클라이언트 ID"** 선택
3. **애플리케이션 유형**: "웹 애플리케이션" 선택
4. **이름**: `Email Agent Web Client` (또는 원하는 이름)
5. **승인된 리디렉션 URI** 추가:
   - 개발 환경: `http://localhost:8000/api/v1/auth/google/callback`
   - 프로덕션 환경: `https://yourdomain.com/api/v1/auth/google/callback`
   - 여러 개 추가 가능
6. **"만들기"** 클릭
7. **클라이언트 ID**와 **클라이언트 보안 비밀번호** 복사 (한 번만 표시됨!)

## 2. 환경 변수 설정

`.env` 파일에 다음 값 추가:

```env
# Google OAuth
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here

# API Base URL (OAuth redirect용)
API_BASE_URL=http://localhost:8000

# JWT Secret Key (랜덤 문자열 생성)
JWT_SECRET_KEY=your_random_secret_key_here_min_32_chars
```

### JWT Secret Key 생성 방법

```bash
# Python으로 생성
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 또는 OpenSSL로 생성
openssl rand -hex 32
```

## 3. 테스트

### 3.1 서버 실행

```bash
uvicorn app.main:app --reload
```

### 3.2 로그인 테스트

1. 브라우저에서 접속:
   ```
   http://localhost:8000/api/v1/auth/google/login
   ```

2. Google 로그인 화면으로 리다이렉트됨

3. Google 계정으로 로그인 및 권한 승인

4. 콜백 URL로 리다이렉트되며 JSON 응답 확인:
   ```json
   {
     "access_token": "eyJ...",
     "token_type": "bearer",
     "user": {
       "id": 1,
       "email": "user@gmail.com",
       "provider": "google",
       "display_name": "User Name",
       "profile_image_url": "https://..."
     },
     "message": "Login successful"
   }
   ```

## 4. 문제 해결

### 4.1 "redirect_uri_mismatch" 오류

- Google Cloud Console의 "승인된 리디렉션 URI"와 `.env`의 `API_BASE_URL`이 일치하는지 확인
- 정확한 URL 형식: `http://localhost:8000/api/v1/auth/google/callback`

### 4.2 "access_denied" 오류

- OAuth 동의 화면에서 테스트 사용자로 등록했는지 확인
- 외부 앱인 경우 테스트 사용자 추가 필수

### 4.3 "invalid_client" 오류

- `GOOGLE_CLIENT_ID`와 `GOOGLE_CLIENT_SECRET`이 올바른지 확인
- 공백이나 따옴표가 포함되지 않았는지 확인

### 4.4 JWT 토큰 오류

- `JWT_SECRET_KEY`가 설정되었는지 확인
- 최소 32자 이상의 랜덤 문자열인지 확인

## 5. 프로덕션 배포 시 주의사항

1. **OAuth 동의 화면 검토 요청**: 외부 앱은 Google 검토 필요
2. **HTTPS 필수**: 프로덕션에서는 반드시 HTTPS 사용
3. **리디렉션 URI**: 프로덕션 도메인으로 업데이트
4. **보안**: `JWT_SECRET_KEY`는 환경 변수로 관리, 절대 코드에 하드코딩 금지
5. **토큰 암호화**: 프로덕션에서는 OAuth 토큰 암호화 저장 권장

