# 서버 실행 전 체크리스트

## ✅ 수정 완료된 사항

1. ✅ **EmailRepository 구현** - DB 저장 로직 추가
2. ✅ **Celery Task DB Session 수정** - 독립적인 DB session 사용
3. ✅ **FastAPI lifespan 적용** - deprecated `on_event` 대신 사용
4. ✅ **MCP Server 기본 구현** - 기본 구조 추가
5. ✅ **Logging 설정 수정** - property 접근 문제 해결

## ⚠️ 실행 전 필수 확인 사항

### 1. 환경 변수 설정 (.env 파일)

```env
# 필수 설정
ENVIRONMENT=dev
DEBUG=true

# MySQL (로컬)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=email_agent

# Redis (Celery)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# OAuth (Google)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# LLM (선택)
OPENAI_API_KEY=your_api_key
```

### 2. 데이터베이스 초기화

```bash
# MySQL 데이터베이스 생성
mysql -u root -p -e "CREATE DATABASE email_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Alembic 마이그레이션 실행 (아직 설정 안됨)
# alembic upgrade head
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 서비스 실행 순서

#### 1단계: MySQL 실행
```bash
# macOS
brew services start mysql

# 또는
mysql.server start
```

#### 2단계: Redis 실행
```bash
# macOS
brew services start redis

# 또는
redis-server
```

#### 3단계: FastAPI 서버 실행
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 4단계: Celery Worker 실행 (별도 터미널)
```bash
celery -A app.workers.email_worker worker --loglevel=info
```

#### 5단계: Celery Beat 실행 (별도 터미널)
```bash
celery -A app.workers.email_worker beat --loglevel=info
```

#### 6단계: MCP Server 실행 (별도 터미널, 선택사항)
```bash
python app/mcp/server.py
```

## 🔍 예상되는 문제점

### 1. 데이터베이스 테이블 미생성
- **문제**: Alembic 마이그레이션이 설정되지 않음
- **해결**: `scripts/init_db.py`를 실행하거나 Alembic 설정 필요

### 2. OAuth 리다이렉트 URL 설정
- **문제**: Google OAuth 콜백 URL이 Google Console에 등록되어야 함
- **해결**: `http://localhost:8000/api/auth/google/callback` 등록 필요

### 3. Celery Task 실행 오류
- **문제**: `fetch_all_accounts_emails`가 아직 구현되지 않음 (pass만 있음)
- **해결**: 실제 구현 필요

### 4. EmailAccount 조회 로직
- **문제**: `fetch_emails_for_account`에서 DB에서 계정 정보를 가져오는 로직이 TODO
- **해결**: Repository 패턴으로 구현 필요

## 🚀 빠른 테스트

### 1. FastAPI 서버만 테스트
```bash
uvicorn app.main:app --reload
# http://localhost:8000 접속
# http://localhost:8000/docs 접속 (Swagger UI)
```

### 2. Health Check 테스트
```bash
curl http://localhost:8000/api/health
```

### 3. 데이터베이스 연결 테스트
```bash
python -c "from app.db.session import SessionLocal; db = SessionLocal(); print('DB connected!')"
```

## 📝 TODO (아직 구현 안된 부분)

1. **Alembic 마이그레이션 설정** - DB 스키마 자동 생성
2. **EmailAccount Repository** - 계정 조회 로직
3. **fetch_all_accounts_emails 구현** - 모든 계정 이메일 수집
4. **S3/MinIO 저장 로직** - Raw MIME 저장
5. **LangGraph 그래프 구현** - AI Agent 파이프라인
6. **MCP Tools 실제 구현** - summarize, classify 등

## ✅ 정상 작동 확인

서버가 정상적으로 실행되면:
- `http://localhost:8000` 접속 시 JSON 응답
- `http://localhost:8000/docs` 접속 시 Swagger UI 표시
- `http://localhost:8000/api/health` 접속 시 `{"status": "healthy"}` 응답

