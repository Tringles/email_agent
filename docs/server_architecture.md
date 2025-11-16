# 서버 아키텍처

## 시스템 구성

이 프로젝트는 다음 컴포넌트로 구성됩니다:

1. **FastAPI 서버** - REST API 제공
2. **Celery Worker** - 백그라운드 작업 처리
3. **Celery Beat** - 주기적 작업 스케줄링

## 컴포넌트별 역할

### FastAPI 서버

**주요 기능:**
- OAuth 인증 (Google, Naver)
- 이메일 계정 연결 및 관리
- 이메일 조회 API
- LangGraph Agent 실행 API
- Health Check

**실행:**
```bash
uvicorn app.main:app --reload
```

### Celery Worker

**주요 기능:**
- 이메일 수집 (Gmail, Naver)
- LangGraph AI 처리 파이프라인 실행
- 백그라운드 작업 처리

**실행:**
```bash
celery -A app.workers.email_worker worker --loglevel=info
```

### Celery Beat

**주요 기능:**
- 주기적 이메일 수집 (5분마다)
- 주기적 AI 처리 (5분마다)

**실행:**
```bash
celery -A app.workers.email_worker beat --loglevel=info
```

## 시스템 아키텍처 다이어그램

```
┌─────────────────┐
│  FastAPI Server │  ← REST API, OAuth
└────────┬────────┘
         │
         ├──────────────┐
         │              │
┌────────▼────────┐  ┌──▼──────────────┐
│  Celery Worker  │  │  Celery Beat    │
│  (이메일 수집)   │  │  (스케줄링)      │
│  (AI 처리)      │  │                 │
└────────┬────────┘  └─────────────────┘
         │
         ├──────────────┬──────────────┐
         │              │              │
┌────────▼────────┐ ┌──▼──────────┐ ┌─▼──────────┐
│     MySQL       │ │   Redis     │ │  Qdrant    │
│   (메타데이터)   │ │  (Celery)   │ │ (VectorDB) │
└─────────────────┘ └─────────────┘ └────────────┘
```

## 데이터 흐름

1. **이메일 수집**: Celery Beat → Celery Worker → 이메일 Provider → MySQL
2. **AI 처리**: Celery Beat → Celery Worker → LangGraph → MySQL
3. **API 조회**: FastAPI → MySQL → 사용자

