# LangGraph State & Graph 설계 문서

## 📋 목차
1. [State 구조 설계](#state-구조-설계)
2. [Graph 구조 설계](#graph-구조-설계)
3. [노드 간 데이터 흐름](#노드-간-데이터-흐름)
4. [에러 처리 전략](#에러-처리-전략)
5. [구현 순서](#구현-순서)

---

## State 구조 설계

### 1. State 클래스 정의

LangGraph의 State는 `TypedDict` 또는 `Annotated`를 사용하여 정의합니다. 이메일 처리 파이프라인에 필요한 모든 데이터를 포함합니다.

```python
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langgraph.graph.message import add_messages
from datetime import datetime

class EmailProcessingState(TypedDict):
    """이메일 처리 파이프라인의 상태를 관리하는 State"""
    
    # === 입력 데이터 ===
    email_id: int  # 처리할 이메일 ID
    user_id: int   # 사용자 ID (인증/인가용)
    
    # === 이메일 원본 데이터 ===
    email_data: Dict[str, Any]  # DB에서 가져온 이메일 데이터
    # 포함 필드 (중요도 평가 및 VectorDB 저장에 사용):
    # - 기본 정보: subject, sender, sender_name, recipient, recipient_name
    # - 본문: body_text, body_html
    # - 날짜: email_date, received_date
    # - 폴더/라벨: folder, labels
    # - 참조: cc, bcc, reply_to
    # - 첨부파일: attachments (전체 메타데이터), attachment_count, has_attachments, attachment_names (파일 이름 리스트)
    # - 기타: preview, headers, provider_metadata, provider_message_id, provider_thread_id
    
    # === 처리 결과 (각 노드에서 업데이트) ===
    processed_body_html: Optional[str]  # Preprocess Node 결과 (HTML 전처리된 텍스트)
    summary: Optional[str]  # Summarize Node 결과
    importance_score: Optional[float]  # Classify Node 결과 (0.0-1.0)
    importance_level: Optional[str]  # "low", "medium", "high", "urgent"
    classification: Optional[Dict[str, Any]]  # 카테고리, 태그 등
    
    # === VectorDB 관련 ===
    vector_db_id: Optional[str]  # Vector Search Node 결과
    embedding_model: Optional[str]  # 사용한 임베딩 모델
    similar_emails: Optional[List[Dict[str, Any]]]  # 유사 이메일 목록
    vector_metadata: Optional[Dict[str, Any]]  # VectorDB에 저장된 메타데이터 (이메일 메타데이터 포함)
    
    # === Rule Engine 결과 ===
    rule_applied: Optional[str]  # 적용된 규칙 이름
    auto_action: Optional[str]  # "delete", "archive", "tag", "move", "none"
    action_details: Optional[Dict[str, Any]]  # 액션 상세 정보
    
    # === 처리 상태 관리 ===
    current_node: Optional[str]  # 현재 실행 중인 노드 이름
    completed_nodes: List[str]  # 완료된 노드 목록
    errors: List[Dict[str, Any]]  # 에러 정보 (노드명, 에러 메시지, 타임스탬프)
    
    # === 컨텍스트 데이터 ===
    user_rules: Optional[List[Dict[str, Any]]]  # 사용자 정의 규칙
    db_session: Any  # SQLAlchemy 세션 (노드에서 DB 업데이트용)
    
    # === 메타데이터 ===
    started_at: Optional[datetime]  # 처리 시작 시간
    completed_at: Optional[datetime]  # 처리 완료 시간
```

### 2. State 초기화

State는 Agent Service에서 초기화되며, DB에서 이메일 데이터를 로드하여 채웁니다.

```python
def initialize_state(
    email_id: int,
    user_id: int,
    db: Session
) -> EmailProcessingState:
    """State를 초기화하고 이메일 데이터를 로드"""
    from app.db.repositories.email_repo import EmailRepository
    
    email_repo = EmailRepository(db)
    email = email_repo.get_email_by_id(email_id)
    
    if not email:
        raise ValueError(f"Email {email_id} not found")
    
    return EmailProcessingState(
        email_id=email_id,
        user_id=user_id,
        email_data={
            # 기본 정보
            "subject": email.subject,
            "sender": email.sender,
            "sender_name": email.sender_name,
            "recipient": email.recipient,
            "recipient_name": email.recipient_name,
            # 본문
            "body_text": email.body_text,
            "body_html": email.body_html,
            # 날짜
            "email_date": email.email_date.isoformat() if email.email_date else None,
            "received_date": email.received_date.isoformat() if email.received_date else None,
            # 폴더/라벨
            "folder": email.folder,
            "labels": email.labels,
            # 참조
            "cc": email.cc,
            "bcc": email.bcc,
            "reply_to": email.reply_to,
            # 첨부파일
            "attachments": email.attachments,  # 전체 첨부파일 메타데이터 리스트
            "attachment_count": email.attachment_count,
            "has_attachments": email.has_attachments,
            "attachment_names": [
                att.get("filename", "") for att in (email.attachments or [])
                if att.get("filename")
            ],  # 첨부파일 이름 리스트 (중요도 판별 및 VectorDB 저장용)
            # 기타
            "preview": email.preview,
            "headers": email.headers,
            "provider_metadata": email.provider_metadata,
            "provider_message_id": email.provider_message_id,
            "provider_thread_id": email.provider_thread_id,
        },
        processed_body_html=None,
        summary=None,
        importance_score=None,
        importance_level=None,
        classification=None,
        vector_db_id=None,
        vector_metadata=None,
        embedding_model=None,
        similar_emails=None,
        rule_applied=None,
        auto_action=None,
        action_details=None,
        current_node=None,
        completed_nodes=[],
        errors=[],
        user_rules=None,  # 추후 구현
        db_session=db,
        started_at=datetime.now(),
        completed_at=None,
    )
```

### 3. State 업데이트 패턴

각 노드는 State를 받아서 업데이트된 State를 반환합니다.

```python
def summarize_node(state: EmailProcessingState) -> EmailProcessingState:
    """요약 노드: State를 업데이트하여 반환"""
    # 처리 로직
    summary = generate_summary(state["email_data"])
    
    # State 업데이트
    state["summary"] = summary
    state["current_node"] = "summarize"
    state["completed_nodes"].append("summarize")
    
    return state
```

---

## Graph 구조 설계

### 1. 그래프 플로우

```
START
  ↓
[Load Email Data] (Entry Node)
  ↓
[Preprocess HTML] (HTML 전처리)
  ↓
[Summarize Node]
  ↓
[Classify Node] (메타데이터 우선순위 적용)
  ↓
[Vector Search Node] (메타데이터 포함 저장)
  ↓
[Rule Engine Node]
  ↓
[Save Results] (Exit Node)
  ↓
END
```

### 2. 노드 구성

#### 2.1 Entry Node: `load_email`
- **역할**: DB에서 이메일 데이터를 로드하고 State 초기화
- **입력**: `email_id`, `user_id`
- **출력**: State에 `email_data` 채움
- **에러 처리**: 이메일이 없거나 권한이 없으면 FAILED 상태로 전이

#### 2.2 Preprocess HTML Node: `preprocess_html`
- **역할**: HTML 본문을 요약에 용이한 순수 텍스트로 전처리
- **입력**: `email_data["body_html"]`
- **출력**: `processed_body_html` (HTML 태그 제거, 텍스트 추출, 정리)
- **처리 내용**:
  - HTML 태그 제거 (`<p>`, `<div>`, `<br>` 등)
  - 스타일/스크립트 태그 제거 (`<style>`, `<script>`)
  - HTML 엔티티 디코딩 (`&nbsp;`, `&amp;` 등)
  - 링크 URL 추출 및 정리
  - 이미지 alt 텍스트 추출
  - 불필요한 공백/줄바꿈 정리
  - 인코딩 문제 해결
- **에러 처리**: 실패 시 원본 `body_html` 사용 또는 `body_text` 사용
- **라이브러리**: `beautifulsoup4`, `html2text` 등 활용 가능

#### 2.3 Summarize Node: `summarize`
- **역할**: 이메일 본문을 LLM으로 요약
- **입력**: `email_data["body_text"]`, `processed_body_html` (우선 사용)
- **출력**: `summary`
- **에러 처리**: 실패 시 에러를 기록하고 다음 노드로 진행 (요약은 선택적)

#### 2.4 Classify Node: `classify`
- **역할**: 중요도 평가 및 분류 (메타데이터 우선순위 적용)
- **입력**: 
  - `email_data` (모든 메타데이터)
  - `summary`
  - 메타데이터 우선순위 설정
- **출력**: `importance_score`, `importance_level`, `classification`
- **메타데이터 우선순위**:
  - **High Priority**: `subject`, `sender`, `labels`, `folder`, `attachment_names` (첨부파일 이름)
  - **Medium Priority**: `cc`, `bcc`, `reply_to`, `email_date`, `attachment_count`
  - **Low Priority**: `recipient`, `preview`, `headers`, `provider_metadata`
- **에러 처리**: 실패 시 기본값 설정 (importance_level="medium")

#### 2.5 Vector Search Node: `vector_search`
- **역할**: 임베딩 생성, VectorDB 저장 (메타데이터 포함), 유사 이메일 검색
- **입력**: 
  - `email_data` (모든 메타데이터)
  - `summary`
  - `importance_level`, `classification`
- **출력**: 
  - `vector_db_id`, `embedding_model`, `similar_emails`
  - `vector_metadata` (VectorDB에 저장된 메타데이터)
- **VectorDB 저장 데이터**:
  - **텍스트 (임베딩용)**: `summary` + `processed_body_html` (또는 `body_text`) + `attachment_names` (첨부파일 이름도 포함하여 검색 정확도 향상)
  - **메타데이터 (필터링/검색용)**:
    - 기본 정보: `subject`, `sender`, `recipient`, `email_date`, `folder`
    - 분류 정보: `importance_level`, `classification`, `labels`
    - 첨부파일: `attachment_count`, `has_attachments`, `attachment_names` (파일 이름 리스트)
    - 기타: `cc`, `bcc`, `reply_to`
  - **저장 형식**: Qdrant의 payload에 메타데이터 저장, 벡터는 텍스트 임베딩
  - **검색 활용**: 유사도 검색 시 메타데이터 필터링 가능 (예: 특정 발신자, 중요도 레벨 등)
- **에러 처리**: VectorDB 연결 실패 시 스킵 (선택적 기능)

#### 2.6 Rule Engine Node: `rule_engine`
- **역할**: 규칙 평가 및 자동 액션 결정
- **입력**: `summary`, `importance_level`, `classification`, `similar_emails`, `email_data`
- **출력**: `rule_applied`, `auto_action`, `action_details`
- **에러 처리**: 실패 시 `auto_action="none"`으로 설정

#### 2.7 Exit Node: `save_results`
- **역할**: 처리 결과를 DB에 저장하고 상태 업데이트
- **입력**: State의 모든 처리 결과
- **출력**: DB 업데이트 완료
- **에러 처리**: 실패 시 이메일 상태를 FAILED로 변경

### 3. 그래프 정의 구조

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

def create_email_processing_graph() -> StateGraph:
    """이메일 처리 그래프 생성"""
    
    # 그래프 생성
    workflow = StateGraph(EmailProcessingState)
    
    # 노드 추가
    workflow.add_node("load_email", load_email_node)
    workflow.add_node("preprocess_html", preprocess_html_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("classify", classify_node)
    workflow.add_node("vector_search", vector_search_node)
    workflow.add_node("rule_engine", rule_engine_node)
    workflow.add_node("save_results", save_results_node)
    
    # 엣지 정의 (순차 실행)
    workflow.set_entry_point("load_email")
    workflow.add_edge("load_email", "preprocess_html")
    workflow.add_edge("preprocess_html", "summarize")
    workflow.add_edge("summarize", "classify")
    workflow.add_edge("classify", "vector_search")
    workflow.add_edge("vector_search", "rule_engine")
    workflow.add_edge("rule_engine", "save_results")
    workflow.add_edge("save_results", END)
    
    # 체크포인트 설정 (선택적, 재시도/복구용)
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app
```

### 4. 조건부 라우팅 (선택적)

나중에 확장 가능한 구조:

```python
def should_skip_vector_search(state: EmailProcessingState) -> str:
    """VectorDB가 설정되지 않았으면 스킵"""
    if not settings.VECTOR_DB_URL:
        return "skip_vector_search"
    return "vector_search"

workflow.add_conditional_edges(
    "classify",
    should_skip_vector_search,
    {
        "vector_search": "vector_search",
        "skip_vector_search": "rule_engine"
    }
)
```

---

## 노드 간 데이터 흐름

### 1. 데이터 흐름 다이어그램

```
[Load Email]
  ↓ email_data
[Preprocess HTML]
  ↓ processed_body_html
[Summarize]
  ↓ summary
[Classify]
  ↓ importance_score, importance_level, classification
  (메타데이터 우선순위 적용)
[Vector Search]
  ↓ vector_db_id, similar_emails, vector_metadata
  (메타데이터 포함 저장)
[Rule Engine]
  ↓ rule_applied, auto_action
[Save Results]
  ↓ DB 업데이트
```

### 2. 각 노드의 의존성

- **Preprocess HTML**: `email_data["body_html"]` 필요
- **Summarize**: `email_data`, `processed_body_html` 사용
- **Classify**: `email_data` (모든 메타데이터, 특히 `attachment_names`), `summary` 사용 (summary가 없어도 동작)
- **Vector Search**: `email_data`, `summary`, `importance_level`, `classification` 사용
- **Rule Engine**: `summary`, `importance_level`, `classification`, `similar_emails`, `email_data` 사용
- **Save Results**: 모든 처리 결과 사용

### 3. 병렬 처리 가능성 (향후 확장)

일부 노드는 병렬로 실행 가능:
- `preprocess_html`는 독립적
- `summarize`와 `classify`는 독립적이지만, `classify`가 `summary`를 사용하면 더 정확함
- `vector_search`는 다른 노드와 독립적이지만, `summary`와 `classification`을 사용하면 더 정확함

현재는 순차 실행으로 설계 (단순성과 안정성 우선)

### 4. 메타데이터 우선순위 설정

중요도 평가 시 메타데이터의 우선순위를 설정하여 더 정확한 평가를 수행합니다.

```python
METADATA_PRIORITY = {
    "high": [
        "subject",          # 제목이 가장 중요
        "sender",           # 발신자 (중요한 사람인지 판단)
        "labels",           # 라벨 (중요 표시 등)
        "folder",           # 폴더 (INBOX vs 기타)
        "attachment_names", # 첨부파일 이름 (중요한 문서인지 판단)
    ],
    "medium": [
        "cc",               # 참조인
        "bcc",              # 숨은 참조인
        "reply_to",         # 회신 주소
        "email_date",       # 이메일 날짜 (최근일수록 중요할 수 있음)
        "attachment_count", # 첨부파일 개수
        "has_attachments",  # 첨부파일 존재 여부
    ],
    "low": [
        "recipient",        # 수신인 (보통 자신)
        "preview",          # 미리보기
        "headers",          # 헤더 정보
        "provider_metadata", # 프로바이더 메타데이터
    ]
}
```

이 우선순위는 Classify Node에서 LLM 프롬프트에 포함되어 중요도 평가에 반영됩니다.

#### 우선순위 적용 방법

1. **High Priority 메타데이터**: LLM 프롬프트에서 강조하여 중요도 평가에 큰 영향을 미침
2. **Medium Priority 메타데이터**: 보조적으로 고려
3. **Low Priority 메타데이터**: 참고용으로만 사용

예시 프롬프트 구조:
```
이메일의 중요도를 평가하세요. 다음 메타데이터를 우선순위에 따라 고려하세요:

[High Priority]
- 제목: {subject}
- 발신자: {sender}
- 라벨: {labels}
- 폴더: {folder}
- 첨부파일 이름: {attachment_names}  # 예: ["report.pdf", "invoice.xlsx"]

[Medium Priority]
- 참조인: {cc}
- 날짜: {email_date}
- 첨부파일 개수: {attachment_count}개

[Low Priority]
- 수신인: {recipient}
- 미리보기: {preview}

이메일 내용 요약:
{summary}
```

이렇게 우선순위를 명시하여 LLM이 더 정확한 중요도 평가를 수행할 수 있습니다.

---

## 에러 처리 전략

### 1. 노드 레벨 에러 처리

각 노드는 try-except로 감싸서 에러를 State에 기록:

```python
def summarize_node(state: EmailProcessingState) -> EmailProcessingState:
    try:
        summary = generate_summary(state["email_data"])
        state["summary"] = summary
        state["completed_nodes"].append("summarize")
    except Exception as e:
        logger.error(f"Summarize node failed: {e}")
        state["errors"].append({
            "node": "summarize",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
        # 요약 실패해도 다음 노드로 진행
    finally:
        state["current_node"] = "summarize"
    return state
```

### 2. 치명적 에러 처리

치명적 에러가 발생하면 그래프를 중단:

```python
def load_email_node(state: EmailProcessingState) -> EmailProcessingState:
    try:
        # 이메일 로드
        email = load_email_from_db(state["email_id"])
        if not email:
            raise ValueError("Email not found")
        state["email_data"] = email
    except Exception as e:
        logger.error(f"Failed to load email: {e}")
        state["errors"].append({
            "node": "load_email",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
        # 치명적 에러: 그래프 중단
        raise
    return state
```

### 3. 최종 에러 처리

`save_results` 노드에서 에러가 발생하면 이메일 상태를 FAILED로 변경:

```python
def save_results_node(state: EmailProcessingState) -> EmailProcessingState:
    try:
        # DB에 결과 저장
        update_email_in_db(state)
        state["completed_at"] = datetime.now()
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        # 이메일 상태를 FAILED로 변경
        mark_email_as_failed(state["email_id"], state["db_session"])
        raise
    return state
```

---

## 구현 순서

### Phase 1: 기본 구조 (우선순위 1)
1. ✅ `state.py`: State 클래스 정의
2. ✅ `graph.py`: 기본 그래프 구조 (노드 연결만)
3. ✅ `agent_service.py`: 그래프 실행 래퍼

### Phase 2: 핵심 노드 구현 (우선순위 2)
1. ✅ `nodes/preprocess_html.py`: HTML 전처리 노드
2. ✅ `nodes/summarize.py`: 요약 노드
3. ✅ `nodes/classify.py`: 분류 노드 (메타데이터 우선순위 적용)
4. ✅ `nodes/vector_search.py`: 벡터 검색 노드 (메타데이터 포함 저장)
5. ✅ `nodes/rule_engine.py`: 규칙 엔진 노드

### Phase 3: 통합 및 테스트 (우선순위 3)
1. ✅ `nodes/load_email.py`: Entry 노드
2. ✅ `nodes/save_results.py`: Exit 노드
3. ✅ 에러 처리 로직 추가
4. ✅ API 엔드포인트 통합

### Phase 4: 최적화 (우선순위 4)
1. ✅ 배치 처리 지원
2. ✅ 재시도 로직
3. ✅ 성능 모니터링
4. ✅ 조건부 라우팅 (선택적)

---

## 파일 구조

```
app/langgraph/
├── __init__.py
├── state.py              # State 클래스 정의
├── graph.py              # 그래프 정의 및 컴파일
└── nodes/
    ├── __init__.py
    ├── load_email.py     # Entry 노드
    ├── preprocess_html.py  # HTML 전처리 노드
    ├── summarize.py      # 요약 노드
    ├── classify.py       # 분류 노드 (메타데이터 우선순위 포함)
    ├── vector_search.py    # 벡터 검색 노드 (메타데이터 포함 저장)
    ├── rule_engine.py   # 규칙 엔진 노드
    └── save_results.py   # Exit 노드
```

---

## 추가 고려사항

### 1. State 직렬화
- State는 JSON 직렬화 가능해야 함 (체크포인트 저장용)
- `datetime` 객체는 ISO 형식 문자열로 변환
- `db_session`은 직렬화하지 않음 (런타임에만 사용)

### 2. 체크포인트
- LangGraph의 체크포인트 기능을 사용하여 중단된 처리 재개 가능
- 초기에는 MemorySaver 사용, 나중에 Redis/Database로 확장

### 3. 로깅
- 각 노드에서 처리 시작/완료 로깅
- State의 `errors` 필드에 에러 기록
- 처리 시간 측정 (`started_at`, `completed_at`)

### 4. 테스트
- 각 노드를 독립적으로 테스트 가능하도록 설계
- Mock State를 사용한 단위 테스트
- 전체 그래프 통합 테스트

---

## 다음 단계

이 설계를 바탕으로 다음 순서로 구현합니다:

1. **State 정의** (`state.py`)
2. **기본 그래프 구조** (`graph.py`)
3. **각 노드 구현** (`nodes/*.py`)
4. **Agent Service 통합** (`services/agent_service.py`)

