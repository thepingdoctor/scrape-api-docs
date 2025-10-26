# Deployment Architecture
## Infrastructure, Scalability, and Operations

**Version:** 2.0.0
**Date:** 2025-10-26
**Status:** Design Phase

---

## Overview

This document outlines the deployment architecture for the Documentation Scraper system across multiple environments, from development to enterprise-scale production deployments.

---

## Deployment Models

### 1. Standalone (Development/Personal Use)

**Target Audience**: Individual developers, small projects

**Architecture**:
```
┌─────────────────────────────┐
│    Local Machine            │
│  ┌───────────────────────┐  │
│  │  Python Application   │  │
│  │  - CLI/API/UI         │  │
│  │  - SQLite cache       │  │
│  │  - Local filesystem   │  │
│  │  - Single process     │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

**Components**:
- Single Python process
- SQLite for caching
- Local filesystem for storage
- No external dependencies

**Resource Requirements**:
- CPU: 2 cores
- Memory: 1-2 GB
- Disk: 10 GB
- Suitable for: <100 pages/day

**Deployment**:
```bash
# Install via pip
pip install scrape-api-docs

# Or run from source
poetry install
poetry run scrape-docs https://docs.example.com
```

---

### 2. Single Server (Small Production)

**Target Audience**: Small teams, moderate workloads

**Architecture**:
```
┌────────────────────────────────────────────┐
│           Single Server (4-8 GB RAM)       │
│  ┌──────────────────────────────────────┐  │
│  │        Nginx (Reverse Proxy)         │  │
│  └────────────────┬─────────────────────┘  │
│                   │                         │
│  ┌────────────────▼─────────────────────┐  │
│  │    Gunicorn/Uvicorn Workers (4)      │  │
│  │    - FastAPI application             │  │
│  └────────────────┬─────────────────────┘  │
│                   │                         │
│  ┌────────────────▼─────────────────────┐  │
│  │        Redis (Cache + Queue)         │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │    PostgreSQL (Metadata + Jobs)      │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │    Local/S3 Storage (Exports)        │  │
│  └──────────────────────────────────────┘  │
└────────────────────────────────────────────┘
```

**Components**:
- **Nginx**: SSL termination, load balancing, static file serving
- **Uvicorn Workers**: 4-8 async workers for API
- **Redis**: Caching layer and job queue
- **PostgreSQL**: Job metadata and user management
- **S3/Local**: Export file storage

**Resource Requirements**:
- CPU: 4-8 cores
- Memory: 8-16 GB
- Disk: 100 GB (+ S3 for exports)
- Network: 100 Mbps
- Suitable for: 1,000-10,000 pages/day

**Deployment (Docker)**:
```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    image: scraper-api:latest
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/scraper
      - REDIS_URL=redis://redis:6379
      - S3_BUCKET=exports
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis

  worker:
    image: scraper-api:latest
    command: celery -A app.worker worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/scraper
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=scraper
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
```

---

### 3. Distributed (Enterprise Production)

**Target Audience**: Large organizations, high throughput

**Architecture**:
```
                    Internet
                       │
         ┌─────────────▼──────────────┐
         │   Load Balancer (AWS ELB)  │
         └─────────────┬──────────────┘
                       │
      ┌────────────────┴────────────────┐
      │                                 │
┌─────▼──────┐                  ┌──────▼──────┐
│  API Tier  │                  │  API Tier   │
│ (3+ nodes) │                  │ (3+ nodes)  │
└─────┬──────┘                  └──────┬──────┘
      │                                │
      └────────────────┬───────────────┘
                       │
         ┌─────────────▼──────────────┐
         │    Redis Cluster           │
         │    (Cache + Queue)         │
         └────────────────────────────┘
                       │
      ┌────────────────┴───────────────┐
      │                                │
┌─────▼──────┐                 ┌──────▼──────┐
│  Worker    │                 │   Worker    │
│  Pool      │                 │   Pool      │
│ (5+ nodes) │                 │  (5+ nodes) │
└─────┬──────┘                 └──────┬──────┘
      │                               │
      └────────────────┬──────────────┘
                       │
         ┌─────────────▼──────────────┐
         │  PostgreSQL (RDS/Managed)  │
         │  - Primary + Read Replicas │
         └────────────────────────────┘
                       │
         ┌─────────────▼──────────────┐
         │  S3 / Object Storage       │
         │  - Export artifacts        │
         │  - Multi-region replication│
         └────────────────────────────┘
```

**Components**:
- **Load Balancer**: AWS ELB, GCP Load Balancer, or HAProxy
- **API Tier**: Auto-scaling group of API servers (3-20 nodes)
- **Worker Tier**: Auto-scaling group of worker processes (5-50 nodes)
- **Redis Cluster**: High-availability Redis with Sentinel/Cluster mode
- **Managed PostgreSQL**: AWS RDS, GCP Cloud SQL, or Azure Database
- **Object Storage**: S3, GCS, or Azure Blob Storage

**Resource Requirements (per environment)**:
- **API Nodes**: 2-4 vCPU, 4-8 GB RAM each
- **Worker Nodes**: 4-8 vCPU, 8-16 GB RAM each
- **Database**: db.r5.xlarge or equivalent
- **Redis**: cache.r5.large or equivalent
- Suitable for: 100,000+ pages/day

---

## Kubernetes Deployment

### Kubernetes Architecture

```
┌──────────────────────────────────────────────┐
│           Kubernetes Cluster                 │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │         Ingress Controller             │  │
│  │         (nginx-ingress)                │  │
│  └──────────────┬─────────────────────────┘  │
│                 │                             │
│  ┌──────────────▼─────────────────────────┐  │
│  │    API Deployment (3 replicas)         │  │
│  │    - HPA enabled (2-10 pods)           │  │
│  │    - Resource limits: 2 CPU, 4GB       │  │
│  └──────────────┬─────────────────────────┘  │
│                 │                             │
│  ┌──────────────▼─────────────────────────┐  │
│  │    Worker Deployment (5 replicas)      │  │
│  │    - HPA enabled (3-20 pods)           │  │
│  │    - Resource limits: 4 CPU, 8GB       │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │    Redis StatefulSet                   │  │
│  │    - 3 replicas (Sentinel)             │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │    PostgreSQL (External/Operator)      │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

### Kubernetes Manifests

**api-deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scraper-api
  labels:
    app: scraper-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: scraper-api
  template:
    metadata:
      labels:
        app: scraper-api
    spec:
      containers:
      - name: api
        image: scraper-api:2.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: scraper-secrets
              key: database-url
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: S3_BUCKET
          value: "scraper-exports"
        resources:
          requests:
            cpu: "1000m"
            memory: "2Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"
        livenessProbe:
          httpGet:
            path: /api/v1/system/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/system/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: scraper-api-service
spec:
  selector:
    app: scraper-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: scraper-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: scraper-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**worker-deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scraper-worker
  labels:
    app: scraper-worker
spec:
  replicas: 5
  selector:
    matchLabels:
      app: scraper-worker
  template:
    metadata:
      labels:
        app: scraper-worker
    spec:
      containers:
      - name: worker
        image: scraper-api:2.0.0
        command: ["celery", "-A", "app.worker", "worker"]
        args: ["--loglevel=info", "--concurrency=4"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: scraper-secrets
              key: database-url
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            cpu: "2000m"
            memory: "4Gi"
          limits:
            cpu: "4000m"
            memory: "8Gi"
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: scraper-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: scraper-worker
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**ingress.yaml**:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: scraper-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - api.scraper.example.com
    secretName: scraper-tls
  rules:
  - host: api.scraper.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: scraper-api-service
            port:
              number: 80
```

---

## Monitoring & Observability

### Metrics Collection (Prometheus)

**prometheus-config.yaml**:
```yaml
scrape_configs:
  - job_name: 'scraper-api'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: scraper-api
    metrics_path: /metrics

  - job_name: 'scraper-worker'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: scraper-worker
```

### Key Metrics to Monitor

**Application Metrics**:
- `scraper_jobs_total{status="completed|failed|running"}` - Job counts by status
- `scraper_pages_scraped_total` - Total pages processed
- `scraper_cache_hit_rate` - Cache effectiveness
- `scraper_request_duration_seconds` - API response times
- `scraper_worker_queue_depth` - Pending jobs in queue

**Infrastructure Metrics**:
- CPU utilization (target: <70%)
- Memory utilization (target: <80%)
- Disk I/O (IOPS, throughput)
- Network throughput
- PostgreSQL connections
- Redis memory usage

### Alerting Rules

**alerts.yaml**:
```yaml
groups:
- name: scraper_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(scraper_jobs_total{status="failed"}[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High job failure rate"

  - alert: WorkerQueueBacklog
    expr: scraper_worker_queue_depth > 100
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Worker queue backlog growing"

  - alert: APIHighLatency
    expr: histogram_quantile(0.95, scraper_request_duration_seconds) > 5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "API p95 latency > 5s"

  - alert: DatabaseConnectionExhausted
    expr: pg_stat_database_numbackends / pg_settings_max_connections > 0.9
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "PostgreSQL connection pool near limit"
```

### Logging (Structured Logs)

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "scrape_started",
    job_id="job_123",
    url="https://docs.example.com",
    options={"max_depth": 10}
)

# Output (JSON):
{
  "event": "scrape_started",
  "job_id": "job_123",
  "url": "https://docs.example.com",
  "options": {"max_depth": 10},
  "timestamp": "2025-10-26T19:00:00Z",
  "level": "info"
}
```

**Log Aggregation**:
- **ELK Stack**: Elasticsearch, Logstash, Kibana
- **Loki**: Grafana Loki for log aggregation
- **Cloud Services**: CloudWatch, Stackdriver, Azure Monitor

---

## Security

### Network Security

**API Security**:
```yaml
# Security headers in Nginx
add_header X-Frame-Options "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
```

**TLS Configuration**:
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;
ssl_prefer_server_ciphers on;
```

### Authentication & Authorization

**API Key Management**:
```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not is_valid_api_key(api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
```

**Role-Based Access Control**:
```python
class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"

@app.post("/api/v1/scrape")
async def create_scrape_job(
    request: ScrapeRequest,
    user: User = Depends(get_current_user)
):
    if user.role == UserRole.READONLY:
        raise HTTPException(403, "Insufficient permissions")
    ...
```

### Secrets Management

**Kubernetes Secrets**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: scraper-secrets
type: Opaque
stringData:
  database-url: "postgresql://user:pass@db:5432/scraper"
  redis-password: "secret"
  s3-access-key: "AKIAIOSFODNN7EXAMPLE"
  s3-secret-key: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

**External Secrets (Vault)**:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: scraper-secrets
spec:
  secretStoreRef:
    name: vault-backend
  target:
    name: scraper-secrets
  data:
  - secretKey: database-url
    remoteRef:
      key: scraper/database
      property: url
```

---

## Disaster Recovery & Backup

### Database Backups

**Automated Backups (RDS)**:
```hcl
resource "aws_db_instance" "scraper_db" {
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"
  skip_final_snapshot    = false
  final_snapshot_identifier = "scraper-db-final-snapshot"
}
```

**Backup Verification**:
```bash
#!/bin/bash
# Daily backup verification
pg_dump -h $DB_HOST -U $DB_USER -d scraper | \
  psql -h $BACKUP_DB_HOST -U $DB_USER -d scraper_backup

# Test restore
psql -h $TEST_DB_HOST -U $DB_USER -d test_restore < backup.sql
```

### Export Artifact Backup

**S3 Cross-Region Replication**:
```hcl
resource "aws_s3_bucket_replication_configuration" "replication" {
  bucket = aws_s3_bucket.scraper_exports.id

  rule {
    id     = "replicate-all"
    status = "Enabled"

    destination {
      bucket        = aws_s3_bucket.scraper_exports_backup.arn
      storage_class = "GLACIER"
    }
  }
}
```

### Recovery Procedures

**RPO/RTO Targets**:
- **RPO (Recovery Point Objective)**: 1 hour (max data loss)
- **RTO (Recovery Time Objective)**: 2 hours (max downtime)

**Recovery Steps**:
1. Restore database from latest backup
2. Restore Redis from snapshot (if available)
3. Redeploy application from container registry
4. Verify health checks pass
5. Restore load balancer traffic

---

## Cost Optimization

### Auto-Scaling Configuration

**Horizontal Pod Autoscaler**:
```yaml
# Scale based on queue depth
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: worker-queue-based-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: scraper-worker
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: External
    external:
      metric:
        name: redis_queue_depth
      target:
        type: AverageValue
        averageValue: "10"  # 10 jobs per worker
```

**Vertical Pod Autoscaler**:
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: scraper-api-vpa
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: scraper-api
  updatePolicy:
    updateMode: "Auto"
```

### Resource Optimization

**Spot Instances for Workers**:
```yaml
# Node affinity for spot instances
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: node-type
          operator: In
          values:
          - spot
```

**S3 Lifecycle Policies**:
```json
{
  "Rules": [
    {
      "Id": "archive-old-exports",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

---

## CI/CD Pipeline

### GitLab CI/CD

**.gitlab-ci.yml**:
```yaml
stages:
  - test
  - build
  - deploy

variables:
  DOCKER_REGISTRY: registry.example.com
  IMAGE_NAME: scraper-api

test:
  stage: test
  image: python:3.11
  script:
    - pip install poetry
    - poetry install
    - poetry run pytest --cov
    - poetry run mypy src/
    - poetry run black --check src/

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t $IMAGE_NAME:$CI_COMMIT_SHA .
    - docker tag $IMAGE_NAME:$CI_COMMIT_SHA $IMAGE_NAME:latest
    - docker push $IMAGE_NAME:$CI_COMMIT_SHA
    - docker push $IMAGE_NAME:latest
  only:
    - main

deploy_staging:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - kubectl set image deployment/scraper-api api=$IMAGE_NAME:$CI_COMMIT_SHA -n staging
    - kubectl rollout status deployment/scraper-api -n staging
  environment:
    name: staging
  only:
    - main

deploy_production:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - kubectl set image deployment/scraper-api api=$IMAGE_NAME:$CI_COMMIT_SHA -n production
    - kubectl rollout status deployment/scraper-api -n production
  environment:
    name: production
  when: manual
  only:
    - main
```

---

## Performance Tuning

### Database Optimization

**Connection Pooling**:
```python
# SQLAlchemy connection pool
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,        # Base pool size
    max_overflow=10,     # Additional connections
    pool_timeout=30,     # Wait timeout
    pool_recycle=3600,   # Recycle connections hourly
    pool_pre_ping=True   # Verify connection before use
)
```

**Query Optimization**:
```sql
-- Index for job status queries
CREATE INDEX idx_jobs_status_created ON jobs(status, created_at);

-- Index for user lookups
CREATE INDEX idx_jobs_user_id ON jobs(user_id) WHERE deleted_at IS NULL;

-- Partial index for active jobs
CREATE INDEX idx_active_jobs ON jobs(status) WHERE status IN ('queued', 'running');
```

### Caching Strategy

**Multi-Layer Caching**:
```
Request → Application Cache (LRU) → Redis → Database
            ↓ (miss)                  ↓ (miss)    ↓
          Redis ← ─ ─ ─ ─ ─ ─ ─ ─ Database
```

**Cache Configuration**:
```python
# Redis configuration
REDIS_CONFIG = {
    'max_connections': 100,
    'socket_keepalive': True,
    'socket_timeout': 5,
    'retry_on_timeout': True,
    'decode_responses': True
}

# Cache TTLs
CACHE_TTLS = {
    'page_content': 3600,      # 1 hour
    'job_metadata': 300,       # 5 minutes
    'user_data': 600,          # 10 minutes
    'api_response': 60         # 1 minute
}
```

---

## Next Steps

1. Set up Docker containerization
2. Create Kubernetes manifests
3. Configure CI/CD pipeline
4. Implement monitoring and alerting
5. Set up backup and disaster recovery
6. Configure auto-scaling policies
7. Perform load testing and optimization
8. Document deployment procedures
9. Create runbooks for common operations
10. Plan and execute production rollout
