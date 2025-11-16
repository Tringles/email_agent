# Email AI Aggregator - 프로젝트 개요

## 📋 프로젝트 소개

Gmail / Naver 등 여러 이메일을 한 곳에 모으고, LangGraph 기반 AI Agent가 이메일을 요약하고 중요도를 판단하며 자동 삭제/태깅/정리까지 수행하는 이메일 자동화 시스템입니다.

## 🏗 기술 스택

- **Backend:** FastAPI
- **AI Orchestrator:** LangGraph
- **Tools:** FastMCP
- **DB:** MySQL + VectorDB (Qdrant)
- **Storage:** S3/MinIO
- **Task Queue:** Celery + Redis
- **LLM:** OpenAI (GPT-4o-mini / GPT-5-nano)
- **Logging:** Loguru

## 🎯 주요 기능

1. **다중 이메일 계정 통합**
   - Gmail, Naver 등 여러 이메일 계정을 한 곳에서 관리
   - OAuth 기반 안전한 계정 연결

2. **AI 기반 이메일 처리**
   - LangGraph를 통한 자동 요약 및 분류
   - 중요도 평가 (low, medium, high, urgent)
   - 벡터 검색을 통한 유사 이메일 추천

3. **자동화 규칙**
   - 스팸/광고 이메일 자동 삭제
   - 중요도에 따른 자동 태깅 및 아카이브
   - 첨부파일 기반 중요도 판단

4. **주기적 자동 처리**
   - Celery를 통한 백그라운드 이메일 수집
   - 주기적인 AI 처리 파이프라인 실행

## 🏛 시스템 아키텍처

### 서버 구성

1. **FastAPI 서버** (REST API)
   - OAuth 인증
   - 이메일 API
   - Agent API
   - Health Check

2. **Celery Worker** (백그라운드 작업)
   - 이메일 수집
   - LangGraph AI 처리

3. **Celery Beat** (스케줄링)
   - 주기적 이메일 수집
   - 주기적 AI 처리

### LangGraph 파이프라인

```
load_email → preprocess_html → summarize → classify → vector_search → rule_engine → save_results
```

각 노드:
- **load_email**: 이메일 데이터 로드 및 검증
- **preprocess_html**: HTML 본문 전처리 (인용문 제거)
- **summarize**: LLM으로 이메일 요약
- **classify**: 중요도 평가 및 분류
- **vector_search**: 벡터 저장 및 유사 이메일 검색
- **rule_engine**: 규칙 평가 및 자동 액션 결정
- **save_results**: 처리 결과 DB 저장

## 📁 프로젝트 구조

```
email_agent/
├── app/
│   ├── api/              # REST API 엔드포인트
│   ├── core/             # 설정, 보안, Celery
│   ├── models/           # 데이터베이스 모델
│   ├── schemas/          # Pydantic 스키마
│   ├── services/         # 비즈니스 로직
│   ├── db/               # 데이터베이스 세션 및 리포지토리
│   ├── langgraph/        # LangGraph 그래프 및 노드
│   ├── tasks/            # Celery 태스크
│   ├── workers/          # Celery 워커
│   └── main.py           # FastAPI 앱 진입점
├── docs/                 # 문서
├── tests/                # 테스트
└── requirements.txt      # 의존성
```

## 🚀 빠른 시작

### 1. 환경 변수 설정

```env
# 데이터베이스
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=email_agent

# LLM
OPENAI_API_KEY=

# JWT
JWT_SECRET_KEY=
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 데이터베이스 마이그레이션

```bash
alembic upgrade head
```

### 4. 서비스 실행

```bash
# FastAPI 서버
uvicorn app.main:app --reload

# Celery Worker
celery -A app.workers.email_worker worker --loglevel=info

# Celery Beat
celery -A app.workers.email_worker beat --loglevel=info
```

## 📚 주요 문서

- [서버 아키텍처](./server_architecture.md) - 시스템 구조 및 서버 구성

