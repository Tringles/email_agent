# API 테스트 가이드

이 디렉토리에는 FastAPI 엔드포인트에 대한 테스트 코드가 포함되어 있습니다.

## 테스트 구조

```
tests/
├── conftest.py              # 공통 fixture 및 설정
├── api/
│   ├── test_health.py      # Health check 엔드포인트 테스트
│   ├── test_auth.py         # 인증 엔드포인트 테스트
│   ├── test_email.py       # 이메일 CRUD 엔드포인트 테스트
│   ├── test_agent.py       # AI Agent 처리 엔드포인트 테스트
│   └── test_rules.py       # 규칙 관리 엔드포인트 테스트
```

## 테스트 실행

### 모든 API 테스트 실행
```bash
pytest tests/api/
```

### 특정 테스트 파일 실행
```bash
pytest tests/api/test_health.py
```

### 특정 테스트 클래스 실행
```bash
pytest tests/api/test_email.py::TestEmailAPI
```

### 특정 테스트 메서드 실행
```bash
pytest tests/api/test_email.py::TestEmailAPI::test_get_emails_success
```

### 커버리지 포함 실행
```bash
pytest tests/api/ --cov=app.api --cov-report=html
```

## Fixture 설명

### `db`
- 테스트용 데이터베이스 세션
- 각 테스트마다 새로운 인메모리 SQLite 데이터베이스 생성

### `client`
- FastAPI TestClient 인스턴스
- 데이터베이스 의존성 오버라이드 포함

### `test_user`
- 테스트용 사용자 객체
- 데이터베이스에 저장됨

### `test_user_token`
- 테스트 사용자용 JWT 토큰

### `authenticated_client`
- 인증된 TestClient
- Authorization 헤더 포함
- `get_current_user` 의존성 오버라이드

### `test_email_account`
- 테스트용 이메일 계정

### `test_email`
- 테스트용 이메일 객체

### `test_user_rule`
- 테스트용 사용자 규칙

## 테스트 작성 가이드

### 1. 기본 테스트 구조
```python
class TestMyAPI:
    """API 엔드포인트 테스트"""
    
    def test_endpoint_success(self, authenticated_client: TestClient):
        """성공 케이스 테스트"""
        response = authenticated_client.get("/api/v1/endpoint")
        assert response.status_code == 200
    
    def test_endpoint_unauthorized(self, client: TestClient):
        """인증 없이 접근 시도"""
        response = client.get("/api/v1/endpoint")
        assert response.status_code == 401
```

### 2. Mock 사용
```python
@patch('app.api.module.Service')
def test_with_mock(self, mock_service, authenticated_client):
    mock_service.return_value.method.return_value = "result"
    # 테스트 실행
```

### 3. 데이터베이스 사용
```python
def test_with_db(self, authenticated_client, db, test_user):
    # db 세션 사용
    # test_user fixture 사용
    pass
```

## 주의사항

1. **인증이 필요한 엔드포인트**: `authenticated_client` fixture 사용
2. **인증이 필요 없는 엔드포인트**: `client` fixture 사용
3. **Mock 사용**: 외부 서비스 호출은 mock으로 처리
4. **데이터 격리**: 각 테스트는 독립적으로 실행되어야 함

## 테스트 커버리지 목표

- Health check: 100%
- Auth: 주요 플로우 80%+
- Email: CRUD 작업 90%+
- Agent: 주요 처리 플로우 80%+
- Rules: CRUD 및 검증 90%+

