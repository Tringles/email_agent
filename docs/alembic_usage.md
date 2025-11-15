# Alembic 사용 가이드

## Alembic이란?

Alembic은 SQLAlchemy의 데이터베이스 마이그레이션 도구입니다. Python 모델 변경사항을 데이터베이스 스키마 변경으로 자동 변환하고 버전 관리합니다.

## 기본 사용법

### 1. 초기 마이그레이션 생성

모델을 처음 생성하거나 변경했을 때:

```bash
# 자동으로 변경사항 감지하여 마이그레이션 생성
alembic revision --autogenerate -m "Initial migration"

# 또는 메시지와 함께
alembic revision --autogenerate -m "Add email table"
```

### 2. 마이그레이션 적용

생성된 마이그레이션을 데이터베이스에 적용:

```bash
# 최신 버전으로 업그레이드
alembic upgrade head

# 특정 버전으로 업그레이드
alembic upgrade <revision_id>
```

### 3. 마이그레이션 롤백

이전 버전으로 되돌리기:

```bash
# 한 단계 롤백
alembic downgrade -1

# 특정 버전으로 롤백
alembic downgrade <revision_id>

# 모든 마이그레이션 롤백
alembic downgrade base
```

### 4. 마이그레이션 히스토리 확인

```bash
# 마이그레이션 히스토리 보기
alembic history

# 현재 버전 확인
alembic current
```

## Makefile 명령어

```bash
# 마이그레이션 생성
make migration msg="Add new column"

# 마이그레이션 적용
make migrate

# 마이그레이션 롤백
make migrate-down

# 히스토리 확인
make migration-history
```

## 일반적인 워크플로우

### 새 모델 추가 시

1. 모델 파일에 새 클래스 추가 (`app/models/`)
2. 마이그레이션 생성:
   ```bash
   alembic revision --autogenerate -m "Add new model"
   ```
3. 생성된 마이그레이션 파일 확인 (`alembic/versions/`)
4. 마이그레이션 적용:
   ```bash
   alembic upgrade head
   ```

### 컬럼 추가/수정 시

1. 모델 클래스 수정
2. 마이그레이션 생성:
   ```bash
   alembic revision --autogenerate -m "Add column to user"
   ```
3. 마이그레이션 파일 확인 및 수정 (필요시)
4. 적용:
   ```bash
   alembic upgrade head
   ```

## 주의사항

1. **마이그레이션 파일 검토**: `--autogenerate`로 생성된 파일을 항상 확인하세요
2. **데이터 백업**: Production 환경에서는 마이그레이션 전 백업 필수
3. **테스트**: 개발 환경에서 먼저 테스트
4. **순서**: 마이그레이션은 순차적으로 적용되므로 순서가 중요합니다

## 문제 해결

### 마이그레이션 충돌
```bash
# 현재 상태 확인
alembic current

# 충돌 해결 후
alembic upgrade head
```

### 마이그레이션 파일 수정
생성된 마이그레이션 파일을 직접 수정할 수 있습니다:
- `alembic/versions/xxxxx_initial_migration.py`

