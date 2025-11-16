# Kubernetes 배포 가이드

이 디렉토리에는 Email AI Aggregator를 Kubernetes에 배포하기 위한 매니페스트 파일들이 포함되어 있습니다.

## 사전 요구사항

1. **Kubernetes 클러스터** (v1.20 이상)
2. **kubectl** 설치 및 클러스터 접근 권한
3. **Docker 이미지** 빌드 및 레지스트리 푸시
4. **외부 서비스** (또는 클러스터 내 배포):
   - MySQL/MariaDB
   - Redis
   - Qdrant (Vector Database)
   - MinIO/S3 (Object Storage)

## 배포 순서

### 1. Docker 이미지 빌드 및 푸시

```bash
# 이미지 빌드
docker build -f docker/Dockerfile.app -t your-registry/email-agent:latest .
docker build -f docker/Dockerfile.worker -t your-registry/email-agent-worker:latest .
docker build -f docker/Dockerfile.beat -t your-registry/email-agent-beat:latest .

# 레지스트리에 푸시
docker push your-registry/email-agent:latest
docker push your-registry/email-agent-worker:latest
docker push your-registry/email-agent-beat:latest
```

### 2. Secret 생성

```bash
# secret.yaml.template을 복사하여 실제 값으로 수정
cp k8s/secret.yaml.template k8s/secret.yaml

# secret.yaml 파일을 편집하여 실제 값 입력
# 그 다음 Secret 생성
kubectl apply -f k8s/secret.yaml
```

**중요**: `secret.yaml` 파일은 Git에 커밋하지 마세요. `.gitignore`에 추가하세요.

### 3. ConfigMap 수정

`k8s/configmap.yaml` 파일을 열어서 다음 항목들을 실제 환경에 맞게 수정:

- `DB_HOST`: MySQL 서비스 주소
- `CELERY_BROKER_URL`: Redis 서비스 주소
- `VECTOR_DB_URL`: Qdrant 서비스 주소
- `MINIO_ENDPOINT`: MinIO/S3 서비스 주소
- `API_BASE_URL`: 실제 API 도메인
- `FRONTEND_URL`: 실제 프론트엔드 도메인

### 4. Deployment 이미지 경로 수정

`deployment-app.yaml`, `deployment-worker.yaml`, `deployment-beat.yaml` 파일에서 이미지 경로를 실제 레지스트리 경로로 변경:

```yaml
image: your-registry/email-agent:latest
image: your-registry/email-agent-worker:latest
image: your-registry/email-agent-beat:latest
```

### 5. 배포 실행

```bash
# Namespace 생성
kubectl apply -f k8s/namespace.yaml

# ConfigMap 생성
kubectl apply -f k8s/configmap.yaml

# Secret 생성 (이미 생성했다면 생략)
kubectl apply -f k8s/secret.yaml

# Deployments 생성
kubectl apply -f k8s/deployment-app.yaml
kubectl apply -f k8s/deployment-worker.yaml
kubectl apply -f k8s/deployment-beat.yaml

# Service 생성
kubectl apply -f k8s/service-app.yaml

# Ingress 생성 (선택사항)
kubectl apply -f k8s/ingress.yaml
```

### 6. 데이터베이스 마이그레이션

```bash
# App Pod에 접속하여 마이그레이션 실행
kubectl exec -it -n email-agent deployment/email-agent-app -- alembic upgrade head
```

### 7. 배포 상태 확인

```bash
# Pod 상태 확인
kubectl get pods -n email-agent

# 로그 확인
kubectl logs -f -n email-agent deployment/email-agent-app
kubectl logs -f -n email-agent deployment/email-agent-worker
kubectl logs -f -n email-agent deployment/email-agent-beat

# Service 확인
kubectl get svc -n email-agent

# Ingress 확인
kubectl get ingress -n email-agent
```

## 외부 서비스 설정

### 옵션 1: 클러스터 내부에 배포

MySQL, Redis, Qdrant, MinIO를 클러스터 내부에 StatefulSet으로 배포할 수 있습니다. 각 서비스에 대한 매니페스트 파일을 별도로 생성하세요.

### 옵션 2: 관리형 서비스 사용

- **MySQL**: AWS RDS, Google Cloud SQL, Azure Database 등
- **Redis**: AWS ElastiCache, Google Cloud Memorystore, Azure Cache 등
- **Qdrant**: 클라우드 Qdrant 서비스 또는 자체 호스팅
- **MinIO**: 클러스터 내부 배포 또는 AWS S3, Google Cloud Storage 등

외부 서비스를 사용하는 경우, `configmap.yaml`의 호스트 주소를 외부 서비스 엔드포인트로 변경하세요.

## 리소스 조정

초기 배포 후 모니터링을 통해 리소스 요청/제한을 조정하세요:

```bash
# 리소스 사용량 확인
kubectl top pods -n email-agent

# HPA (Horizontal Pod Autoscaler) 설정 예시
kubectl autoscale deployment email-agent-app -n email-agent --cpu-percent=70 --min=2 --max=10
```

## PersistentVolume 사용 (Celery Beat)

Celery Beat의 스케줄 파일을 영구 저장하려면 `persistent-volume-beat.yaml`을 사용하세요:

```bash
kubectl apply -f k8s/persistent-volume-beat.yaml
```

## 트러블슈팅

### Pod가 시작되지 않는 경우

```bash
# Pod 이벤트 확인
kubectl describe pod <pod-name> -n email-agent

# Pod 로그 확인
kubectl logs <pod-name> -n email-agent
```

### 데이터베이스 연결 실패

- ConfigMap의 `DB_HOST`가 올바른지 확인
- Secret의 `DB_PASSWORD`가 올바른지 확인
- 네트워크 정책이 데이터베이스 접근을 허용하는지 확인

### 이미지 Pull 실패

- 이미지 레지스트리 인증 설정 확인
- `imagePullSecrets` 추가 필요 여부 확인

## 보안 고려사항

1. **Secret 관리**: 민감한 정보는 Kubernetes Secret으로 관리하고, Git에 커밋하지 마세요.
2. **RBAC**: 적절한 Role-Based Access Control 설정
3. **Network Policies**: 네트워크 정책으로 트래픽 제한
4. **TLS/SSL**: Ingress에서 TLS 인증서 사용
5. **이미지 스캔**: 컨테이너 이미지 보안 스캔

## 업데이트 및 롤백

```bash
# 이미지 업데이트 후 배포
kubectl set image deployment/email-agent-app app=your-registry/email-agent:v1.1.0 -n email-agent

# 롤백
kubectl rollout undo deployment/email-agent-app -n email-agent

# 배포 히스토리 확인
kubectl rollout history deployment/email-agent-app -n email-agent
```

