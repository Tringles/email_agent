# Email Processing Workflow

## 개요

이메일이 `PENDING` 상태일 때부터 `PROCESSED` 상태가 될 때까지의 전체 워크플로우를 설명합니다.

## 상태 전이

```
PENDING → PROCESSING → PROCESSED
              ↓
           FAILED
```

### 상태 설명

- **PENDING**: 이메일이 수집되었지만 아직 AI Agent에 의해 처리되지 않음
- **PROCESSING**: 현재 AI Agent가 처리 중
- **PROCESSED**: AI Agent 처리가 완료됨
- **FAILED**: 처리 중 오류 발생

## 전체 워크플로우

### 1. 이메일 수집 (Email Ingestion)

```
Celery Task (fetch_emails_for_account)
  ↓
Gmail API에서 이메일 가져오기
  ↓
DB에 저장 (status = PENDING, is_processed = False)
```

**위치**: `app/tasks/email_tasks.py`

### 2. PENDING 이메일 조회

```python
# PENDING 상태의 이메일 조회
email_repo = EmailRepository(db)
unprocessed_emails = email_repo.get_unprocessed_emails(limit=100)
```

**위치**: `app/db/repositories/email_repo.py::get_unprocessed_emails()`

**조건**:
- `status == PENDING`
- `is_processed == False`

### 3. AI Agent 처리 파이프라인 (LangGraph)

PENDING 이메일이 발견되면 LangGraph 파이프라인을 실행합니다.

#### 3.1 상태 업데이트: PENDING → PROCESSING

```python
email.status = EmailStatus.PROCESSING
email.is_processed = False  # 아직 처리 중
db.commit()
```

#### 3.2 LangGraph 노드 실행 순서

```
1. Summarize Node
   ↓
2. Classify Node (중요도 평가)
   ↓
3. Vector Search Node (유사 이메일 검색)
   ↓
4. Rule Engine Node (자동 액션 결정)
   ↓
5. 상태 업데이트: PROCESSING → PROCESSED
```

#### 3.3 각 노드 상세

**Summarize Node** (`app/langgraph/nodes/summarize.py`)
- 입력: 이메일 본문 (body_text, body_html)
- 처리: LLM을 사용하여 이메일 요약 생성
- 출력: `summary` 필드에 저장

**Classify Node** (`app/langgraph/nodes/classify.py`)
- 입력: 이메일 내용, 제목, 발신자
- 처리: 중요도 평가 (LOW, MEDIUM, HIGH, URGENT)
- 출력: 
  - `importance_level`
  - `importance_score` (0.0 - 1.0)
  - `classification` (카테고리, 태그 등)

**Vector Search Node** (`app/langgraph/nodes/vector_search.py`)
- 입력: 이메일 내용
- 처리: 
  - 이메일을 임베딩으로 변환
  - VectorDB (Qdrant)에 저장
  - 유사한 과거 이메일 검색
- 출력:
  - `vector_db_id`
  - `embedding_model`
  - 유사 이메일 목록 (컨텍스트로 사용)

**Rule Engine Node** (`app/langgraph/nodes/rule_engine.py`)
- 입력: 요약, 중요도, 유사 이메일, 사용자 규칙
- 처리: 자동 액션 결정
  - 삭제 (스팸, 광고 등)
  - 아카이브 (중요하지 않은 이메일)
  - 태그 추가
  - 폴더 이동
- 출력:
  - `rule_applied`
  - `auto_action`
  - 필요시 이메일 상태 변경 (is_deleted, is_archived 등)

#### 3.4 최종 상태 업데이트: PROCESSING → PROCESSED

```python
email.status = EmailStatus.PROCESSED
email.is_processed = True
email.processed_at = datetime.now()
db.commit()
```

## 실행 방법

### 방법 1: API를 통한 실행

```bash
# 특정 이메일 처리
POST /api/v1/agent/run?email_id=1

# 모든 PENDING 이메일 처리 (미구현)
POST /api/v1/agent/run
```

### 방법 2: Celery Task로 실행 (권장)

```python
from app.tasks.agent_tasks import process_pending_emails

# 모든 PENDING 이메일 처리
process_pending_emails.delay()

# 특정 이메일 처리
process_pending_emails.delay(email_id=1)
```

### 방법 3: 수동 실행

```python
from app.db.session import SessionLocal
from app.db.repositories.email_repo import EmailRepository
from app.services.agent_service import AgentService

db = SessionLocal()
try:
    email_repo = EmailRepository(db)
    unprocessed = email_repo.get_unprocessed_emails(limit=10)
    
    agent_service = AgentService()
    for email in unprocessed:
        result = await agent_service.process_email(email.id, db)
        print(f"Email {email.id}: {result}")
finally:
    db.close()
```

## 현재 구현 상태

### ✅ 구현 완료
- 이메일 수집 및 DB 저장 (PENDING 상태)
- PENDING 이메일 조회 (`get_unprocessed_emails`)
- 상태 업데이트 메서드 (`mark_as_processed`)

### 🚧 구현 필요
- LangGraph 파이프라인 구현 (`app/langgraph/graph.py`)
- 각 노드 구현 (summarize, classify, vector_search, rule_engine)
- Agent Service 구현 (`app/services/agent_service.py`)
- Celery Task 구현 (`app/tasks/agent_tasks.py`)
- API 엔드포인트 구현 (`app/api/agent.py`)

## 다음 단계

1. **LangGraph 그래프 정의**
   - `app/langgraph/graph.py`에 파이프라인 정의
   - 노드 간 연결 및 상태 전이 정의

2. **각 노드 구현**
   - Summarize: LLM을 사용한 요약
   - Classify: 중요도 분류
   - Vector Search: 임베딩 및 검색
   - Rule Engine: 자동 액션 결정

3. **Agent Service 구현**
   - LangGraph 실행 래퍼
   - 에러 처리 및 재시도 로직

4. **Celery Task 구현**
   - 주기적으로 PENDING 이메일 처리
   - 또는 이메일 수집 후 자동 트리거

## 데이터베이스 필드 업데이트

처리 완료 후 업데이트되는 필드:

```python
{
    "status": "processed",
    "is_processed": True,
    "processed_at": datetime.now(),
    "summary": "이메일 요약 내용",
    "importance_score": 0.85,
    "importance_level": "high",
    "classification": {"category": "work", "tags": ["urgent"]},
    "vector_db_id": "qdrant_doc_id",
    "embedding_model": "text-embedding-3-small",
    "rule_applied": "auto_archive_low_importance",
    "auto_action": "archive"
}
```

