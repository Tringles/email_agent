# Celery Beat 실행 가이드

## 개요

Celery Beat는 스케줄된 작업을 실행하는 스케줄러입니다. 현재 설정된 스케줄:
- **`fetch_all_accounts_emails`**: 5분마다 실행 (모든 활성 계정의 이메일 가져오기)

## 실행 방법

### 1. 기본 실행

```bash
# conda 환경에서 실행
conda run -n ai celery -A app.workers.email_worker beat --loglevel=info
```

### 2. 프로젝트 디렉토리에서 실행

```bash
cd /Users/tringles/Desktop/L/code/email_agent
conda run -n ai celery -A app.workers.email_worker beat --loglevel=info
```

### 3. 백그라운드 실행

```bash
# 백그라운드로 실행
conda run -n ai celery -A app.workers.email_worker beat --loglevel=info &

# 프로세스 확인
ps aux | grep celery
```

### 4. 로그 파일로 출력

```bash
conda run -n ai celery -A app.workers.email_worker beat --loglevel=info > logs/celery_beat.log 2>&1 &
```

## 현재 스케줄 설정

```python
# app/core/celery_app.py
celery_app.conf.beat_schedule = {
    "fetch-all-accounts-emails": {
        "task": "fetch_all_accounts_emails",
        "schedule": 300.0,  # 5분마다 (초 단위)
    },
}
```

## 실행 전 확인사항

### 1. Redis 실행 확인

```bash
# Redis가 실행 중인지 확인
redis-cli ping
# 응답: PONG

# 또는
ps aux | grep redis
```

### 2. Celery Worker 실행 확인

Celery Beat는 task를 스케줄만 하고, 실제 실행은 Worker가 합니다.

```bash
# Worker 실행 (별도 터미널)
conda run -n ai celery -A app.workers.email_worker worker --loglevel=info
```

### 3. 데이터베이스 연결 확인

```bash
# MySQL 연결 확인
mysql -u email_agent -pemail_agent_password email_agent -e "SELECT 1;"
```

## 실행 순서

### 개발 환경

1. **Redis 시작** (필요시)
   ```bash
   redis-server
   ```

2. **Celery Worker 시작** (터미널 1)
   ```bash
   conda run -n ai celery -A app.workers.email_worker worker --loglevel=info
   ```

3. **Celery Beat 시작** (터미널 2)
   ```bash
   conda run -n ai celery -A app.workers.email_worker beat --loglevel=info
   ```

4. **FastAPI 서버 시작** (터미널 3, 선택사항)
   ```bash
   conda run -n ai uvicorn app.main:app --reload
   ```

## 스케줄 확인

### 실행 중인 스케줄 확인

```python
from app.core.celery_app import celery_app

# 스케줄 확인
print(celery_app.conf.beat_schedule)
```

### 로그에서 확인

Celery Beat 실행 시 다음과 같은 로그가 출력됩니다:

```
[2025-11-15 17:00:00,000: INFO/MainProcess] beat: Starting...
[2025-11-15 17:00:00,100: INFO/MainProcess] Scheduler: Sending due task fetch-all-accounts-emails
[2025-11-15 17:05:00,000: INFO/MainProcess] Scheduler: Sending due task fetch-all-accounts-emails
```

## 스케줄 변경

### 간격 변경

`app/core/celery_app.py`에서 수정:

```python
celery_app.conf.beat_schedule = {
    "fetch-all-accounts-emails": {
        "task": "fetch_all_accounts_emails",
        "schedule": 60.0,  # 1분마다 (초 단위)
        # 또는
        # "schedule": crontab(minute='*/5'),  # 5분마다
    },
}
```

### 새 스케줄 추가

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "fetch-all-accounts-emails": {
        "task": "fetch_all_accounts_emails",
        "schedule": 300.0,  # 5분마다
    },
    "daily-email-summary": {
        "task": "send_daily_summary",
        "schedule": crontab(hour=9, minute=0),  # 매일 오전 9시
    },
}
```

## 문제 해결

### 1. "No module named 'celery'" 오류

```bash
# 패키지 설치
conda run -n ai pip install celery redis
```

### 2. "Connection refused" 오류

Redis가 실행되지 않았습니다:

```bash
# Redis 시작
redis-server

# 또는 macOS에서
brew services start redis
```

### 3. Task가 실행되지 않음

- Celery Worker가 실행 중인지 확인
- Worker 로그에서 에러 확인
- Beat 로그에서 task 전송 확인

### 4. 중복 실행 방지

Beat는 한 번에 하나만 실행되어야 합니다:

```bash
# 실행 중인 Beat 프로세스 확인
ps aux | grep "celery.*beat"

# 기존 프로세스 종료
pkill -f "celery.*beat"
```

## 프로덕션 환경

### systemd 서비스로 등록 (Linux)

```ini
# /etc/systemd/system/celery-beat.service
[Unit]
Description=Celery Beat Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/email_agent
Environment="PATH=/path/to/conda/envs/ai/bin"
ExecStart=/path/to/conda/envs/ai/bin/celery -A app.workers.email_worker beat --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker Compose 사용

```yaml
# docker-compose.yaml
services:
  celery-beat:
    build: .
    command: celery -A app.workers.email_worker beat --loglevel=info
    volumes:
      - .:/app
    depends_on:
      - redis
      - mysql
```

## 모니터링

### Flower 사용 (선택사항)

```bash
# Flower 설치
conda run -n ai pip install flower

# 실행
conda run -n ai celery -A app.workers.email_worker flower

# 브라우저에서 접속
# http://localhost:5555
```

Flower에서:
- 실행 중인 task 확인
- 스케줄된 task 확인
- Worker 상태 확인
- Task 히스토리 확인

