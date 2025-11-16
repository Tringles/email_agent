# GitHub Actions Workflows

## CI Tests (`ci.yml`)

자동화된 테스트 실행 워크플로우입니다.

### 트리거 조건

- `develop` 또는 `main` 브랜치에 push
- `develop` 또는 `main` 브랜치로의 Pull Request

### 실행 내용

1. **환경 설정**
   - Python 3.11 설치
   - MySQL 8.0 서비스 시작
   - Redis 7 서비스 시작
   - 의존성 패키지 설치

2. **테스트 실행**
   - API 테스트
   - Service 테스트
   - Repository 테스트
   - 코드 커버리지 측정

3. **결과 보고**
   - 테스트 결과 표시
   - 코드 커버리지 리포트 생성 (선택적 Codecov 업로드)

### 환경 변수

테스트 실행에 필요한 환경 변수는 워크플로우에서 자동으로 설정됩니다:
- 데이터베이스 연결 정보
- Redis 연결 정보
- OpenAI API 키 (테스트용)
- OAuth 클라이언트 정보 (테스트용)
- JWT 시크릿 키 (테스트용)

### 주의사항

- 실제 서비스는 MySQL을 사용하지만, 테스트는 SQLite를 사용합니다.
- Codecov 토큰은 선택사항이며, 없어도 테스트는 정상 실행됩니다.

