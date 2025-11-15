# 이메일 가져오기 테스트 가이드

## 저장 흐름 확인

Celery task 실행 시 다음 순서로 DB에 저장됩니다:

1. **`fetch_emails_for_account(account_id)`** 호출
   - DB에서 EmailAccount 조회
   - credentials 파싱
   - `fetch_emails_task` 호출

2. **`fetch_emails_task`** 실행
   - Gmail API로 이메일 가져오기
   - 각 이메일에 대해 중복 체크 (`provider_message_id`)
   - `email_repo.create_email()` 호출 → **DB에 저장**
   - `db.commit()` → **트랜잭션 커밋**

3. **`last_fetch_at` 업데이트**
   - 성공 시 `last_fetch_at` 업데이트
   - 실패 시 `last_fetch_error`에 에러 메시지 저장

## 테스트 방법

### 1. 사전 준비

#### Gmail 계정 등록 확인
```sql
-- MySQL에서 등록된 계정 확인
SELECT id, email_address, provider_type, is_active, last_fetch_at 
FROM email_accounts 
WHERE provider_type = 'gmail';
```

#### Celery Worker 실행
```bash
# Celery worker 실행
conda run -n ai celery -A app.workers.email_worker worker --loglevel=info
```

### 2. Task 실행

#### 방법 1: Python 스크립트로 실행
```python
from app.tasks.email_tasks import fetch_emails_for_account

# 등록된 Gmail 계정 ID로 실행
result = fetch_emails_for_account.delay(account_id=1)
print(result.get())  # 결과 확인
```

#### 방법 2: Celery CLI로 실행
```bash
conda run -n ai celery -A app.workers.email_worker call app.tasks.email_tasks.fetch_emails_for_account --args='[1]'
```

#### 방법 3: Python 인터프리터에서 직접 실행
```python
from app.tasks.email_tasks import fetch_emails_for_account
import asyncio

# 동기적으로 실행 (테스트용)
result = fetch_emails_for_account(account_id=1)
print(result)
```

### 3. 결과 확인

#### Task 결과 확인
```python
result = {
    "account_id": 1,
    "fetched_count": 10,      # 가져온 이메일 수
    "saved_count": 8,          # DB에 저장된 이메일 수
    "skipped_count": 2,        # 중복으로 건너뛴 이메일 수
    "status": "success"
}
```

#### DB에서 이메일 확인
```sql
-- 저장된 이메일 확인
SELECT 
    id,
    email_account_id,
    subject,
    sender,
    email_date,
    status,
    is_processed,
    created_at
FROM emails
WHERE email_account_id = 1
ORDER BY email_date DESC
LIMIT 10;
```

#### 로그 확인
```bash
# Celery worker 로그에서 확인
# 성공 시:
# INFO: Successfully fetched 8 emails for account 1 (user@gmail.com)
# INFO: Saved 8 new emails, skipped 2 duplicates for account 1

# 실패 시:
# ERROR: Failed to fetch emails for account 1: [에러 메시지]
```

## 문제 해결

### 1. "Email account not found" 오류

**원인**: account_id가 잘못되었거나 계정이 등록되지 않음

**해결**:
```sql
-- 등록된 계정 확인
SELECT * FROM email_accounts;
```

### 2. "Gmail connection error" 오류

**원인**: OAuth 토큰이 만료되었거나 credentials 형식 오류

**해결**:
- Gmail 계정을 다시 연결
- credentials 형식 확인

### 3. 이메일이 저장되지 않음

**확인 사항**:
1. Celery worker가 실행 중인지 확인
2. DB 연결 확인
3. 로그에서 에러 메시지 확인
4. `saved_count`가 0인지 확인 (중복일 수 있음)

### 4. 중복 이메일이 저장됨

**원인**: `provider_message_id`가 중복 체크에 사용되는데, 값이 없거나 잘못됨

**해결**:
```sql
-- 중복 확인
SELECT provider_message_id, COUNT(*) as count
FROM emails
WHERE email_account_id = 1
GROUP BY provider_message_id
HAVING count > 1;
```

## 자동 스케줄링 테스트

### Celery Beat 실행
```bash
# 별도 터미널에서 실행
conda run -n ai celery -A app.workers.email_worker beat --loglevel=info
```

### 스케줄 확인
```python
from app.core.celery_app import celery_app

# 스케줄된 task 확인
print(celery_app.conf.beat_schedule)
```

### 모든 계정 이메일 가져오기
```python
from app.tasks.email_tasks import fetch_all_accounts_emails

# 모든 활성 계정에 대해 이메일 가져오기
result = fetch_all_accounts_emails.delay()
print(result.get())
```

## 성능 확인

### 대량 이메일 처리
```python
# 많은 이메일이 있는 경우
result = fetch_emails_for_account.delay(account_id=1)
# 시간이 걸릴 수 있음
```

### 비동기 처리 확인
```python
# Task ID로 상태 확인
task = fetch_emails_for_account.delay(account_id=1)
print(f"Task ID: {task.id}")
print(f"Status: {task.status}")  # PENDING, SUCCESS, FAILURE
print(f"Result: {task.get()}")   # 결과 대기
```

