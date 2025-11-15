# Docker Compose 설정

이 디렉토리에는 Email AI Aggregator 프로젝트의 Docker Compose 설정이 포함되어 있습니다.

## 서비스 구성

- **app**: FastAPI 백엔드 서버
- **celery-worker**: Celery 워커 (이메일 수집 작업)
- **celery-beat**: Celery Beat (스케줄링)
- **mysql**: MySQL 데이터베이스
- **redis**: Redis (Celery broker 및 결과 저장)
- **minio**: MinIO 오브젝트 스토리지
- **qdrant**: Qdrant 벡터 데이터베이스

## 사용 방법

### 1. 환경 변수 설정

프로젝트 루트에 `.env` 파일 생성 (`.env.example` 참고):

```bash
# docker/.env.example을 프로젝트 루트로 복사
cp docker/.env.example ../.env
```

또는 직접 `.env` 파일 생성:

```env
# Environment
ENVIRONMENT=dev
DEBUG=true

# Database - MySQL
DB_HOST=localhost
DB_PORT=3306
DB_USER=email_agent
DB_PASSWORD=email_agent_password
DB_NAME=email_agent

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123

# API URLs
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# JWT
JWT_SECRET_KEY=your-jwt-secret-key
ID_ENCRYPTION_KEY=your-encryption-key

# OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# LLM
OPENAI_API_KEY=your-openai-api-key
```

**중요**: Docker Compose는 프로젝트 루트의 `.env` 파일을 자동으로 읽어서 `${VARIABLE_NAME}` 형태로 참조할 수 있습니다.

### 2. Docker Compose 실행

```bash
# 모든 서비스 시작
cd docker
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 특정 서비스만 시작
docker-compose up -d mysql redis minio qdrant
docker-compose up -d app celery-worker celery-beat
```

### 3. 데이터베이스 마이그레이션

```bash
# Alembic 마이그레이션 실행
docker-compose exec app alembic upgrade head
```

### 4. MinIO 버킷 생성

1. 브라우저에서 `http://localhost:9001` 접속
2. 로그인: `minioadmin` / `minioadmin123`
3. 버킷 생성: `email-mime`

### 5. 서비스 접속 정보

- **FastAPI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **MySQL**: localhost:3306
- **Redis**: localhost:6379

## 개발 모드

개발 중에는 코드 변경사항이 자동으로 반영되도록 볼륨 마운트를 사용합니다.

```bash
# 개발 모드로 실행 (코드 변경 시 자동 재시작)
docker-compose up
```

## 프로덕션 배포

프로덕션 환경에서는:

1. 환경 변수 설정 확인
2. 보안 강화 (강력한 비밀번호, SSL 등)
3. 리소스 제한 설정
4. 로그 관리 설정

```bash
# 프로덕션 모드
ENVIRONMENT=prod DEBUG=false docker-compose up -d
```

## 문제 해결

### 서비스가 시작되지 않는 경우

```bash
# 로그 확인
docker-compose logs [service-name]

# 서비스 상태 확인
docker-compose ps

# 서비스 재시작
docker-compose restart [service-name]
```

### 데이터베이스 연결 오류

```bash
# MySQL 컨테이너 상태 확인
docker-compose exec mysql mysqladmin ping -h localhost -u root -prootpassword

# 데이터베이스 생성 확인
docker-compose exec mysql mysql -u root -prootpassword -e "SHOW DATABASES;"
```

### 볼륨 데이터 삭제

```bash
# 모든 볼륨 삭제 (주의: 데이터 손실)
docker-compose down -v
```

## 빌드 및 푸시

```bash
# 이미지 빌드
docker-compose build

# 특정 서비스만 빌드
docker-compose build app

# 이미지 태그 및 푸시
docker tag email_agent_app:latest your-registry/email_agent_app:latest
docker push your-registry/email_agent_app:latest
```

