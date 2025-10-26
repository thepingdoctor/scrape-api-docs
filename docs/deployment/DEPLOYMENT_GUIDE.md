# Deployment Guide - Documentation Scraper

**Version:** 2.0.0
**Last Updated:** 2025-10-26

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Docker Deployment](#docker-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Monitoring Setup](#monitoring-setup)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Local Development with Docker Compose

```bash
# Clone repository
git clone https://github.com/thepingdoctor/scrape-api-docs.git
cd scrape-api-docs

# Start all services
docker-compose up -d

# Access Streamlit UI
open http://localhost:8501

# View logs
docker-compose logs -f scraper-ui
```

---

## Docker Deployment

### Building the Docker Image

```bash
# Build production image
docker build -t scraper-api:latest .

# Build development image
docker build --target development -t scraper-api:dev .

# Multi-platform build
docker buildx build --platform linux/amd64,linux/arm64 -t scraper-api:latest .
```

### Running the Container

**CLI Mode:**
```bash
docker run --rm \
  -v $(pwd)/output:/data \
  scraper-api:latest https://docs.example.com
```

**Web UI Mode:**
```bash
docker run -d \
  -p 8501:8501 \
  -v $(pwd)/output:/data \
  -e STREAMLIT_SERVER_PORT=8501 \
  scraper-api:latest \
  streamlit run /app/src/scrape_api_docs/streamlit_app.py
```

### Docker Compose Deployment

**Development Environment:**
```bash
# Start all services
docker-compose up -d

# Services available:
# - Streamlit UI: http://localhost:8501
# - Redis: localhost:6379
# - PostgreSQL: localhost:5432
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000
```

**Production Configuration:**
```bash
# Set environment variables
export POSTGRES_PASSWORD=your_secure_password
export GRAFANA_PASSWORD=your_grafana_password

# Start production stack
docker-compose -f docker-compose.yml up -d scraper-ui redis postgres nginx
```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured
- Helm 3.x (optional)
- cert-manager (for TLS)
- Metrics Server (for HPA)

### Quick Deploy

```bash
# Create namespace
kubectl apply -f k8s/namespace.yml

# Create secrets (UPDATE VALUES FIRST!)
kubectl apply -f k8s/secrets.yml

# Deploy Redis
kubectl apply -f k8s/redis-statefulset.yml

# Deploy API and Workers
kubectl apply -f k8s/deployment.yml
kubectl apply -f k8s/worker-deployment.yml

# Setup ingress
kubectl apply -f k8s/ingress.yml

# Verify deployment
kubectl get pods -n scraper
kubectl get svc -n scraper
```

### Step-by-Step Deployment

#### 1. Setup Namespace and RBAC

```bash
kubectl apply -f k8s/namespace.yml
```

Verify namespace:
```bash
kubectl get namespace scraper
kubectl describe namespace scraper
```

#### 2. Configure Secrets

**IMPORTANT:** Never commit real secrets to git!

```bash
# Option 1: Manual secret creation
kubectl create secret generic scraper-secrets \
  --from-literal=database-url='postgresql://user:pass@db:5432/scraper' \
  --from-literal=redis-password='your-redis-password' \
  --from-literal=aws-access-key-id='YOUR_KEY' \
  --from-literal=aws-secret-access-key='YOUR_SECRET' \
  -n scraper

# Option 2: Use sealed-secrets (recommended)
kubeseal --format=yaml < k8s/secrets.yml > k8s/sealed-secrets.yml
kubectl apply -f k8s/sealed-secrets.yml

# Option 3: Use external-secrets with Vault
kubectl apply -f k8s/secrets.yml  # Uses ExternalSecret resource
```

#### 3. Deploy Data Layer

```bash
# Deploy Redis cluster
kubectl apply -f k8s/redis-statefulset.yml

# Wait for Redis to be ready
kubectl wait --for=condition=ready pod -l app=redis -n scraper --timeout=300s

# Verify Redis
kubectl exec -it redis-0 -n scraper -- redis-cli ping
```

#### 4. Deploy Application

```bash
# Deploy API
kubectl apply -f k8s/deployment.yml

# Deploy Workers
kubectl apply -f k8s/worker-deployment.yml

# Monitor rollout
kubectl rollout status deployment/scraper-api -n scraper
kubectl rollout status deployment/scraper-worker -n scraper
```

#### 5. Setup Ingress and TLS

```bash
# Install cert-manager (if not already installed)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Deploy ingress
kubectl apply -f k8s/ingress.yml

# Get ingress IP
kubectl get ingress -n scraper
```

#### 6. Verify Deployment

```bash
# Check all resources
kubectl get all -n scraper

# Check pod status
kubectl get pods -n scraper -o wide

# Check logs
kubectl logs -l app=scraper-api -n scraper --tail=100
kubectl logs -l app=scraper-worker -n scraper --tail=100

# Test health endpoint
kubectl run curl-test --image=curlimages/curl --rm -it --restart=Never -- \
  curl -v http://scraper-api-service/api/v1/system/health
```

### Scaling

**Manual scaling:**
```bash
# Scale API
kubectl scale deployment scraper-api --replicas=5 -n scraper

# Scale workers
kubectl scale deployment scraper-worker --replicas=10 -n scraper
```

**Auto-scaling (HPA is already configured):**
```bash
# Check HPA status
kubectl get hpa -n scraper

# Describe HPA
kubectl describe hpa scraper-api-hpa -n scraper
kubectl describe hpa scraper-worker-hpa -n scraper
```

### Updates and Rollbacks

**Rolling update:**
```bash
# Update image
kubectl set image deployment/scraper-api \
  api=ghcr.io/thepingdoctor/scrape-api-docs:v2.1.0 \
  -n scraper

# Monitor rollout
kubectl rollout status deployment/scraper-api -n scraper

# Check rollout history
kubectl rollout history deployment/scraper-api -n scraper
```

**Rollback:**
```bash
# Rollback to previous version
kubectl rollout undo deployment/scraper-api -n scraper

# Rollback to specific revision
kubectl rollout undo deployment/scraper-api --to-revision=3 -n scraper
```

---

## CI/CD Pipeline

### GitHub Actions Setup

The CI/CD pipeline is configured in `.github/workflows/ci-cd.yml`.

#### Required Secrets

Configure these secrets in GitHub repository settings:

```
KUBE_CONFIG_STAGING       # Base64-encoded kubeconfig for staging
KUBE_CONFIG_PRODUCTION    # Base64-encoded kubeconfig for production
CODECOV_TOKEN             # Codecov upload token (optional)
```

**Generate kubeconfig secret:**
```bash
# Encode your kubeconfig
cat ~/.kube/config | base64 | pbcopy  # macOS
cat ~/.kube/config | base64 -w 0      # Linux

# Add to GitHub Secrets as KUBE_CONFIG_STAGING or KUBE_CONFIG_PRODUCTION
```

#### Pipeline Stages

1. **Lint & Security** - Code quality and vulnerability scanning
2. **Test** - Multi-platform testing with coverage
3. **Build** - Package building and validation
4. **Docker** - Container image building and scanning
5. **Deploy Staging** - Automatic deployment to staging
6. **Deploy Production** - Manual deployment to production

#### Manual Deployment Triggers

**Staging:**
```bash
# Push to develop branch
git push origin develop
```

**Production:**
```bash
# Create a release
git tag -a v2.0.0 -m "Release v2.0.0"
git push origin v2.0.0

# Or use GitHub UI to create a release
```

### Local CI Testing

```bash
# Install act (GitHub Actions local runner)
brew install act  # macOS
# OR
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run workflow locally
act -j test
act -j lint-and-security
act -j build
```

---

## Monitoring Setup

### Prometheus Configuration

1. **Deploy Prometheus:**
```bash
# Using Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --values config/prometheus-values.yml

# Or using Docker Compose
docker-compose up -d prometheus
```

2. **Configure scraping:**
```bash
# Apply Prometheus config
kubectl create configmap prometheus-config \
  --from-file=config/prometheus.yml \
  -n monitoring
```

3. **Deploy alert rules:**
```bash
kubectl create configmap prometheus-alerts \
  --from-file=config/alerts.yml \
  -n monitoring
```

### Grafana Dashboards

1. **Access Grafana:**
```bash
# Get Grafana password
kubectl get secret -n monitoring prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d

# Port forward to access
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
```

2. **Import dashboards:**
- Navigate to http://localhost:3000
- Import dashboard from `config/grafana/dashboards/scraper-dashboard.json`

### Key Metrics to Monitor

- **Application Metrics:**
  - `scraper_jobs_total{status="completed|failed"}` - Job counts
  - `scraper_pages_scraped_total` - Pages processed
  - `scraper_cache_hit_rate` - Cache effectiveness
  - `scraper_request_duration_seconds` - API latency

- **Infrastructure Metrics:**
  - CPU/Memory utilization
  - Pod restart counts
  - Network traffic
  - Disk I/O

### Alerting

Alerts are configured in `config/alerts.yml`:

- **Critical Alerts:** API down, database down, high error rate
- **Warning Alerts:** High latency, queue backlog, resource usage
- **Info Alerts:** Deployment events, scaling events

**Test alerting:**
```bash
# Trigger a test alert
kubectl exec -it prometheus-0 -n monitoring -- \
  wget --post-data='[{"labels":{"alertname":"TestAlert"}}]' \
  http://localhost:9093/api/v1/alerts
```

---

## Troubleshooting

### Common Issues

#### 1. Pods Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n scraper

# Check events
kubectl get events -n scraper --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n scraper --previous
```

**Common causes:**
- Image pull errors: Check image name and registry credentials
- Resource limits: Increase CPU/memory limits
- Configuration errors: Validate configmaps and secrets

#### 2. High Memory Usage

```bash
# Check memory usage
kubectl top pods -n scraper

# Increase memory limits
kubectl set resources deployment scraper-api \
  --limits=memory=8Gi \
  -n scraper
```

#### 3. Database Connection Errors

```bash
# Test database connectivity
kubectl run pg-test --image=postgres:15 --rm -it --restart=Never -- \
  psql postgresql://user:pass@postgres-service:5432/scraper

# Check database logs
kubectl logs -l app=postgres -n scraper
```

#### 4. Performance Issues

```bash
# Check HPA status
kubectl get hpa -n scraper

# Force scaling
kubectl scale deployment scraper-worker --replicas=10 -n scraper

# Check resource utilization
kubectl top nodes
kubectl top pods -n scraper
```

### Debug Mode

Enable debug logging:
```bash
kubectl set env deployment/scraper-api LOG_LEVEL=DEBUG -n scraper
kubectl rollout status deployment/scraper-api -n scraper
```

### Health Checks

```bash
# API health
curl -v https://api.scraper.example.com/api/v1/system/health

# Redis health
kubectl exec -it redis-0 -n scraper -- redis-cli ping

# Database health
kubectl exec -it postgres-0 -n scraper -- pg_isready
```

### Log Analysis

```bash
# Stream all logs
kubectl logs -f -l app=scraper-api -n scraper --all-containers=true

# Search for errors
kubectl logs -l app=scraper-api -n scraper | grep -i error

# Export logs
kubectl logs -l app=scraper-api -n scraper > api-logs.txt
```

---

## Best Practices

### Security

1. **Use secrets management**: Never hardcode credentials
2. **Enable RBAC**: Limit pod permissions
3. **Scan images**: Use Trivy or similar tools
4. **Update regularly**: Keep dependencies current
5. **Enable network policies**: Restrict pod-to-pod communication

### Performance

1. **Set resource limits**: Prevent resource exhaustion
2. **Use HPA**: Auto-scale based on metrics
3. **Enable caching**: Reduce database load
4. **Monitor metrics**: Identify bottlenecks early
5. **Use CDN**: Serve static content efficiently

### Reliability

1. **Use readiness probes**: Prevent traffic to unhealthy pods
2. **Set PodDisruptionBudgets**: Maintain availability during updates
3. **Implement circuit breakers**: Prevent cascade failures
4. **Use multi-AZ**: Distribute across availability zones
5. **Test disaster recovery**: Regular backup/restore drills

---

## Support

- **Documentation:** https://github.com/thepingdoctor/scrape-api-docs
- **Issues:** https://github.com/thepingdoctor/scrape-api-docs/issues
- **Kubernetes Docs:** https://kubernetes.io/docs/
- **Docker Docs:** https://docs.docker.com/
