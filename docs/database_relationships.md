# Database Relationships 설명

## 개요

이메일 수집 시스템의 데이터베이스 모델 간 관계를 설명합니다.

## 관계 구조

```
User (1) ────< (N) EmailAccount (1) ────< (N) Email
```

### 1. User ↔ EmailAccount (1:N)

**관계**: 한 사용자는 여러 이메일 계정을 가질 수 있습니다.

**설명**:
- 사용자는 OAuth로 로그인합니다 (Google, Naver 등)
- 각 사용자는 여러 이메일 계정을 연결할 수 있습니다
  - 예: Gmail 계정 1개 + Naver 계정 1개
- 사용자가 삭제되면 연결된 모든 이메일 계정도 자동 삭제됩니다 (CASCADE)

**코드 예시**:
```python
# User에서 EmailAccount 접근
user = session.query(User).first()
email_accounts = user.email_accounts.all()  # 모든 이메일 계정 조회

# EmailAccount에서 User 접근
email_account = session.query(EmailAccount).first()
user = email_account.user  # 소유자 사용자
```

**Foreign Key**:
- `EmailAccount.user_id` → `User.id`
- `ondelete="CASCADE"`: User 삭제 시 EmailAccount도 삭제

---

### 2. EmailAccount ↔ Email (1:N)

**관계**: 한 이메일 계정에서 여러 이메일을 수집할 수 있습니다.

**설명**:
- 각 이메일 계정(Gmail, Naver 등)에서 수집된 이메일들을 저장합니다
- 이메일 계정이 삭제되면 해당 계정의 모든 이메일도 자동 삭제됩니다 (CASCADE)
- 각 이메일은 어떤 계정에서 수집되었는지 추적합니다

**코드 예시**:
```python
# EmailAccount에서 Email 접근
email_account = session.query(EmailAccount).first()
emails = email_account.emails.all()  # 모든 이메일 조회
unprocessed_emails = email_account.emails.filter(Email.is_processed == False).all()

# Email에서 EmailAccount 접근
email = session.query(Email).first()
email_account = email.email_account  # 수집된 계정
user = email.email_account.user  # 최종 소유자
```

**Foreign Key**:
- `Email.email_account_id` → `EmailAccount.id`
- `ondelete="CASCADE"`: EmailAccount 삭제 시 Email도 삭제

---

## 전체 관계 체인

```
User (id=1)
  └── EmailAccount (id=1, user_id=1, email="user@gmail.com")
      ├── Email (id=1, email_account_id=1, subject="Hello")
      ├── Email (id=2, email_account_id=1, subject="World")
      └── Email (id=3, email_account_id=1, subject="Test")
  
  └── EmailAccount (id=2, user_id=1, email="user@naver.com")
      ├── Email (id=4, email_account_id=2, subject="안녕")
      └── Email (id=5, email_account_id=2, subject="하세요")
```

## 주요 쿼리 패턴

### 1. 사용자의 모든 이메일 조회
```python
user = session.query(User).filter(User.id == user_id).first()
all_emails = []
for account in user.email_accounts:
    all_emails.extend(account.emails.all())
```

### 2. 특정 계정의 미처리 이메일 조회 (AI Agent용)
```python
account = session.query(EmailAccount).filter(EmailAccount.id == account_id).first()
unprocessed = account.emails.filter(
    Email.is_processed == False,
    Email.status == EmailStatus.PENDING
).all()
```

### 3. 사용자의 모든 계정에서 미처리 이메일 조회
```python
user = session.query(User).filter(User.id == user_id).first()
unprocessed_emails = []
for account in user.email_accounts:
    unprocessed = account.emails.filter(
        Email.is_processed == False
    ).all()
    unprocessed_emails.extend(unprocessed)
```

### 4. 이메일에서 사용자까지 역방향 조회
```python
email = session.query(Email).filter(Email.id == email_id).first()
user = email.email_account.user  # 이메일 → 계정 → 사용자
```

## CASCADE 동작

### User 삭제 시
1. User 삭제
2. → 연결된 모든 EmailAccount 자동 삭제 (CASCADE)
3. → 각 EmailAccount의 모든 Email 자동 삭제 (CASCADE)

### EmailAccount 삭제 시
1. EmailAccount 삭제
2. → 해당 계정의 모든 Email 자동 삭제 (CASCADE)
3. → User는 유지됨

## 인덱스 최적화

성능 최적화를 위한 인덱스:
- `users.id` (Primary Key)
- `email_accounts.user_id` (Foreign Key)
- `email_accounts.id` (Primary Key)
- `emails.email_account_id` (Foreign Key)
- `emails.is_processed` (AI Agent 쿼리용)
- `emails.status` (상태별 조회용)

## 주의사항

1. **Lazy Loading**: 관계는 `lazy="dynamic"`으로 설정되어 있어, 실제 접근 시에만 쿼리가 실행됩니다.
2. **N+1 문제**: 여러 계정의 이메일을 조회할 때는 `joinedload` 또는 `selectinload`를 사용하세요.
3. **CASCADE**: User 삭제 시 모든 관련 데이터가 삭제되므로 주의하세요.

