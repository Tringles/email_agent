# 서버 아키텍처 설명

## 서버 구성

이 프로젝트는 **두 개의 독립적인 서버**로 구성됩니다:

1. **FastAPI 서버** (REST API)
2. **MCP 서버** (AI Tools)

---

## 1. FastAPI 서버

### 실행 방법
```bash
uvicorn app.main:app --reload
```

### 노출되는 엔드포인트

FastAPI 서버를 실행하면 다음 엔드포인트들이 노출됩니다:

#### OAuth 인증
- `GET /api/auth/google/login` - Google 로그인
- `GET /api/auth/google/callback` - Google 로그인 콜백
- `GET /api/auth/naver/login` - Naver 로그인
- `GET /api/auth/naver/callback` - Naver 로그인 콜백
- `GET /api/auth/email-accounts/gmail/connect` - Gmail 계정 연결
- `GET /api/auth/email-accounts/gmail/callback` - Gmail 계정 연결 콜백

#### 이메일 API
- `GET /api/email/{id}` - 이메일 조회
- `POST /api/email/ingest` - 이메일 수집 트리거
- `GET /api/email/{id}/summary` - 이메일 요약 조회

#### Agent API
- `POST /api/agent/run` - LangGraph agent 실행

#### Health Check
- `GET /api/health` - 헬스 체크
- `GET /api/health/ready` - 준비 상태 확인

#### 문서
- `GET /docs` - Swagger UI (dev 모드에서만)
- `GET /redoc` - ReDoc (dev 모드에서만)

---

## 2. MCP 서버

### 실행 방법
```bash
python app/mcp/server.py
```

### 역할

MCP 서버는 **AI 도구(Tools)를 제공**하는 별도의 서버입니다:
- LangGraph agent가 사용할 수 있는 도구들을 제공
- FastAPI와는 **독립적으로 실행**됨
- OAuth 엔드포인트는 **노출되지 않음**

### 제공하는 도구들
- `summarize` - 이메일 요약
- `classify` - 중요도 분류
- `vector_search` - 벡터 검색
- 등등...

---

## 중요 사항

### ❌ MCP 서버를 실행해도 OAuth 엔드포인트는 노출되지 않습니다

- **FastAPI 서버**를 실행해야 OAuth 엔드포인트가 노출됩니다
- **MCP 서버**는 AI 도구만 제공하며, REST API는 제공하지 않습니다

### ✅ 두 서버는 독립적으로 실행됩니다

```
┌─────────────────┐         ┌─────────────────┐
│  FastAPI Server │         │   MCP Server    │
│  (REST API)     │         │  (AI Tools)     │
│                 │         │                 │
│  - OAuth        │         │  - summarize    │
│  - Email API    │         │  - classify     │
│  - Agent API    │         │  - vector_search│
│  - Health       │         │                 │
└─────────────────┘         └─────────────────┘
        │                            │
        └────────────┬───────────────┘
                     │
              (공유 DB, Redis 등)
```

### 실행 순서

1. **FastAPI 서버 시작** (OAuth 엔드포인트 노출)
   ```bash
   uvicorn app.main:app --reload
   ```

2. **MCP 서버 시작** (AI 도구 제공)
   ```bash
   python app/mcp/server.py
   ```

3. **Celery Worker 시작** (백그라운드 작업)
   ```bash
   celery -A app.workers.email_worker worker --loglevel=info
   ```

4. **Celery Beat 시작** (스케줄링)
   ```bash
   celery -A app.workers.email_worker beat --loglevel=info
   ```

---

## 보안 고려사항

### Production 환경

1. **CORS 설정**: `app/main.py`에서 `allow_origins`를 실제 프론트엔드 도메인으로 제한
2. **HTTPS**: OAuth 콜백은 HTTPS로만 접근 가능하도록 설정
3. **환경 변수**: `.env` 파일을 `.gitignore`에 추가하고, production에서는 환경 변수로 관리
4. **토큰 암호화**: `oauth_access_token`, `oauth_refresh_token`은 암호화하여 저장

### Dev 환경

- `DEBUG=True`로 설정하면 Swagger UI가 노출됨
- `DEBUG=False`로 설정하면 `/docs`, `/redoc` 접근 불가

