# Docker 빌드 가이드

이 디렉토리에는 Email AI Aggregator 프로젝트의 Docker 이미지 빌드를 위한 파일들이 포함되어 있습니다.

## Dockerfile 개요

### 주요 개선사항

1. **멀티 스테이지 빌드**: 빌드 의존성과 런타임을 분리하여 이미지 크기 최적화
2. **Non-root 사용자**: 보안을 위해 `appuser` 사용자로 실행
3. **레이블 추가**: OCI 표준 레이블로 이미지 메타데이터 관리
4. **Health check**: Kubernetes와 호환되는 헬스체크 설정
5. **프로덕션 최적화**: Uvicorn workers, Celery concurrency 등 최적화

### Dockerfile 종류

- **Dockerfile.app**: FastAPI 애플리케이션
- **Dockerfile.worker**: Celery Worker
- **Dockerfile.beat**: Celery Beat 스케줄러
- **Dockerfile.base**: 공통 베이스 이미지 (선택사항)

## 빌드 방법

### 방법 1: 빌드 스크립트 사용 (권장)

```bash
# 기본 빌드 (로컬)
./docker/docker-build.sh

# 레지스트리 지정
./docker/docker-build.sh -r docker.io/your-username

# 버전 태그 지정
./docker/docker-build.sh -r docker.io/your-username -v v1.0.0

# 도움말
./docker/docker-build.sh --help
```

### 방법 2: 직접 빌드

```bash
# App 이미지
docker build -f docker/Dockerfile.app \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg VERSION=latest \
  -t email-agent:latest .

# Worker 이미지
docker build -f docker/Dockerfile.worker \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg VERSION=latest \
  -t email-agent-worker:latest .

# Beat 이미지
docker build -f docker/Dockerfile.beat \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg VERSION=latest \
  -t email-agent-beat:latest .
```

## 이미지 푸시

```bash
# 레지스트리에 로그인
docker login your-registry.com

# 이미지 태그 지정
docker tag email-agent:latest your-registry.com/email-agent:v1.0.0
docker tag email-agent-worker:latest your-registry.com/email-agent-worker:v1.0.0
docker tag email-agent-beat:latest your-registry.com/email-agent-beat:v1.0.0

# 푸시
docker push your-registry.com/email-agent:v1.0.0
docker push your-registry.com/email-agent-worker:v1.0.0
docker push your-registry.com/email-agent-beat:v1.0.0
```

## 이미지 최적화 팁

### 1. 빌드 캐시 활용

`.dockerignore` 파일을 사용하여 불필요한 파일을 제외하면 빌드 속도가 향상됩니다.

### 2. 레이어 최적화

- `requirements.txt`를 먼저 복사하여 의존성 변경 시에만 재빌드
- 애플리케이션 코드는 마지막에 복사

### 3. 멀티 스테이지 빌드

빌드 도구(gcc, g++ 등)는 빌드 스테이지에만 포함되고 최종 이미지에는 포함되지 않습니다.

## 보안 고려사항

1. **Non-root 사용자**: 모든 컨테이너는 `appuser` 사용자로 실행됩니다.
2. **최소 권한**: 필요한 패키지만 설치합니다.
3. **의존성 업데이트**: 정기적으로 베이스 이미지와 패키지를 업데이트하세요.

## 프로덕션 설정

### Uvicorn Workers

`Dockerfile.app`에서 기본적으로 4개의 worker를 사용합니다. 리소스에 따라 조정하세요:

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Celery Concurrency

`Dockerfile.worker`에서 기본적으로 4개의 동시 작업을 처리합니다:

```dockerfile
CMD ["celery", "-A", "app.workers.email_worker", "worker", "--concurrency=4"]
```

## Health Check

모든 이미지는 헬스체크를 포함합니다:

- **App**: `http://localhost:8000/api/v1/health`
- **Worker/Beat**: Celery 자체 헬스체크 메커니즘 사용

## 트러블슈팅

### 빌드 실패: MySQL 클라이언트 라이브러리

```bash
# 시스템 패키지 업데이트
apt-get update && apt-get install -y default-libmysqlclient-dev
```

### 이미지 크기가 큰 경우

- 멀티 스테이지 빌드 사용 확인
- `.dockerignore` 파일 확인
- 불필요한 패키지 제거

### 권한 오류

- Non-root 사용자로 실행되므로 파일 권한 확인
- 로그 디렉토리 권한 확인

## CI/CD 통합

### GitHub Actions 예시

```yaml
- name: Build and push Docker images
  run: |
    ./docker/docker-build.sh \
      -r ghcr.io/${{ github.repository_owner }} \
      -v ${{ github.sha }}
```

### GitLab CI 예시

```yaml
build:
  script:
    - ./docker/docker-build.sh -r $CI_REGISTRY_IMAGE -v $CI_COMMIT_SHA
```
