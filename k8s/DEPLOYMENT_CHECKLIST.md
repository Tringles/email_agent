# Kubernetes 배포 체크리스트

## 사전 준비

### 1. Docker 이미지 준비
- [ ] Docker 이미지 빌드 (`docker/Dockerfile.app`, `docker/Dockerfile.worker`, `docker/Dockerfile.beat`)
- [ ] 이미지 레지스트리에 푸시
- [ ] 이미지 태그 버전 관리 전략 수립

### 2. 외부 서비스 설정
- [ ] MySQL/MariaDB 서비스 준비 (클러스터 내부 또는 외부)
- [ ] Redis 서비스 준비 (클러스터 내부 또는 외부)
- [ ] Qdrant 서비스 준비 (클러스터 내부 또는 외부)
- [ ] MinIO/S3 서비스 준비 (클러스터 내부 또는 외부)

### 3. 환경 변수 설정
- [ ] `configmap.yaml` 수정 (서비스 주소, 도메인 등)
- [ ] `secret.yaml` 생성 및 실제 값 입력
- [ ] Secret 파일이 `.gitignore`에 포함되어 있는지 확인

### 4. 네트워크 설정
- [ ] Ingress Controller 설치 확인
- [ ] DNS 설정 (도메인 → Ingress)
- [ ] TLS 인증서 발급 (cert-manager 또는 수동)

## 배포 단계

### 1. 기본 리소스 생성
- [ ] Namespace 생성: `kubectl apply -f k8s/namespace.yaml`
- [ ] ConfigMap 생성: `kubectl apply -f k8s/configmap.yaml`
- [ ] Secret 생성: `kubectl apply -f k8s/secret.yaml`

### 2. 외부 서비스 배포 (선택사항)
- [ ] MySQL 배포: `kubectl apply -f k8s/external-services-example.yaml` (MySQL 부분만)
- [ ] Redis 배포: `kubectl apply -f k8s/external-services-example.yaml` (Redis 부분만)
- [ ] Qdrant 배포: `kubectl apply -f k8s/external-services-example.yaml` (Qdrant 부분만)
- [ ] MinIO 배포: `kubectl apply -f k8s/external-services-example.yaml` (MinIO 부분만)

### 3. 애플리케이션 배포
- [ ] Deployment 이미지 경로 확인 및 수정
- [ ] App Deployment 생성: `kubectl apply -f k8s/deployment-app.yaml`
- [ ] Worker Deployment 생성: `kubectl apply -f k8s/deployment-worker.yaml`
- [ ] Beat Deployment 생성: `kubectl apply -f k8s/deployment-beat.yaml`
- [ ] Service 생성: `kubectl apply -f k8s/service-app.yaml`

### 4. 데이터베이스 마이그레이션
- [ ] Alembic 마이그레이션 실행: `kubectl exec -it -n email-agent deployment/email-agent-app -- alembic upgrade head`

### 5. Ingress 및 네트워크
- [ ] Ingress 생성: `kubectl apply -f k8s/ingress.yaml`
- [ ] TLS 인증서 확인: `kubectl get certificate -n email-agent`

### 6. 오토스케일링 (선택사항)
- [ ] HPA 생성: `kubectl apply -f k8s/hpa-app.yaml`
- [ ] Worker HPA 생성: `kubectl apply -f k8s/hpa-worker.yaml`

## 배포 후 검증

### 1. Pod 상태 확인
- [ ] 모든 Pod가 Running 상태인지 확인: `kubectl get pods -n email-agent`
- [ ] Pod 로그 확인: `kubectl logs -f -n email-agent deployment/email-agent-app`

### 2. 서비스 연결 확인
- [ ] Service 엔드포인트 확인: `kubectl get endpoints -n email-agent`
- [ ] Health check 확인: `curl http://<service-ip>/api/v1/health`

### 3. 외부 접근 확인
- [ ] Ingress 동작 확인: `kubectl describe ingress -n email-agent`
- [ ] 외부 도메인으로 접근 테스트
- [ ] TLS 인증서 확인

### 4. 기능 테스트
- [ ] API 엔드포인트 테스트
- [ ] Celery Worker 작업 처리 확인
- [ ] Celery Beat 스케줄링 확인
- [ ] 데이터베이스 연결 확인
- [ ] Vector DB 연결 확인

## 모니터링 및 로깅

- [ ] Prometheus 메트릭 수집 설정 (필요시)
- [ ] 로그 수집 시스템 연동 (ELK, Loki 등)
- [ ] 알림 설정 (Pod 실패, 리소스 부족 등)

## 보안 검토

- [ ] Secret이 Git에 커밋되지 않았는지 확인
- [ ] RBAC 설정 확인
- [ ] Network Policy 설정 (필요시)
- [ ] 이미지 보안 스캔 실행
- [ ] TLS/SSL 인증서 유효성 확인

## 백업 및 복구

- [ ] 데이터베이스 백업 전략 수립
- [ ] PersistentVolume 백업 설정 (Celery Beat 스케줄)
- [ ] 복구 프로세스 문서화

## 성능 튜닝

- [ ] 리소스 요청/제한 조정
- [ ] HPA 임계값 조정
- [ ] 데이터베이스 연결 풀 설정
- [ ] Celery Worker 수 조정

## 롤백 계획

- [ ] 이전 버전 이미지 태그 확인
- [ ] 롤백 절차 문서화: `kubectl rollout undo deployment/email-agent-app -n email-agent`

