# Quick Start Guide - DevOps Setup

## 5-Minute Docker Deployment

### Option 1: Docker CLI Only

```bash
# Build image
docker build -t scraper-api:latest .

# Run web UI
docker run -d -p 8501:8501 -v $(pwd)/output:/data scraper-api:latest \
  streamlit run /app/src/scrape_api_docs/streamlit_app.py

# Access at http://localhost:8501
```

### Option 2: Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# Services available:
# - Web UI: http://localhost:8501
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000
# - Redis: localhost:6379
# - PostgreSQL: localhost:5432

# View logs
docker-compose logs -f scraper-ui

# Stop services
docker-compose down
```

## 15-Minute Kubernetes Deployment

### Prerequisites
```bash
# Verify cluster access
kubectl cluster-info

# Install cert-manager (for TLS)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

### Deploy Application

```bash
# 1. Create namespace
kubectl apply -f k8s/namespace.yml

# 2. Setup secrets (EDIT VALUES FIRST!)
vim k8s/secrets.yml  # Update passwords and keys
kubectl apply -f k8s/secrets.yml

# 3. Deploy Redis
kubectl apply -f k8s/redis-statefulset.yml

# 4. Deploy application
kubectl apply -f k8s/deployment.yml
kubectl apply -f k8s/worker-deployment.yml

# 5. Setup ingress (UPDATE DOMAIN FIRST!)
vim k8s/ingress.yml  # Update scraper.example.com to your domain
kubectl apply -f k8s/ingress.yml

# 6. Verify deployment
kubectl get all -n scraper
kubectl logs -l app=scraper-api -n scraper --tail=50
```

## Using Makefile (Easiest)

```bash
# Local development
make install-dev
make test
make format

# Docker operations
make docker-build
make docker-compose-up
make docker-compose-logs

# Kubernetes operations
make k8s-deploy-all          # Deploy everything
make k8s-status              # Check status
make k8s-logs-api            # View API logs
make k8s-scale-worker REPLICAS=10  # Scale workers

# CI/CD simulation
make ci-local                # Run all CI checks locally

# See all commands
make help
```

## CI/CD Setup (GitHub Actions)

### Required Repository Secrets

1. Go to GitHub repository → Settings → Secrets and Variables → Actions
2. Add the following secrets:

```
KUBE_CONFIG_STAGING
  - Base64-encoded kubeconfig for staging cluster
  - Generate: cat ~/.kube/config | base64 -w 0

KUBE_CONFIG_PRODUCTION
  - Base64-encoded kubeconfig for production cluster
  - Generate: cat ~/.kube/config | base64 -w 0

CODECOV_TOKEN (optional)
  - Get from https://codecov.io
```

### Workflow Triggers

```bash
# Staging deployment (automatic)
git push origin develop

# Production deployment (manual approval)
git tag v1.0.0
git push origin v1.0.0
# Then create GitHub Release

# Security scans (daily + on PR)
# Runs automatically
```

## Monitoring Setup

### Prometheus + Grafana (Docker Compose)

```bash
# Already included in docker-compose.yml
docker-compose up -d prometheus grafana

# Access Grafana
open http://localhost:3000
# Login: admin / admin (change on first login)

# Import dashboards from config/grafana/dashboards/
```

### Prometheus (Kubernetes)

```bash
# Using Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace

# Port forward to access
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
```

## Troubleshooting

### Docker Issues

```bash
# View container logs
docker logs <container-id> --tail=100 -f

# Exec into container
docker exec -it <container-id> /bin/sh

# Rebuild without cache
docker build --no-cache -t scraper-api:latest .
```

### Kubernetes Issues

```bash
# Check pod status
kubectl describe pod <pod-name> -n scraper

# View events
kubectl get events -n scraper --sort-by='.lastTimestamp'

# Restart deployment
kubectl rollout restart deployment/scraper-api -n scraper

# Delete and redeploy
kubectl delete deployment scraper-api -n scraper
kubectl apply -f k8s/deployment.yml
```

### Common Errors

**Port already in use:**
```bash
# Find and kill process using port 8501
lsof -ti:8501 | xargs kill -9

# Or use different port
docker run -p 8502:8501 scraper-api:latest
```

**Permission denied (Docker):**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

**ImagePullBackOff (Kubernetes):**
```bash
# Login to container registry
docker login ghcr.io -u USERNAME

# Create image pull secret
kubectl create secret docker-registry regcred \
  --docker-server=ghcr.io \
  --docker-username=USERNAME \
  --docker-password=TOKEN \
  -n scraper
```

## Health Checks

```bash
# Docker
curl http://localhost:8501/_stcore/health

# Kubernetes
kubectl get pods -n scraper
kubectl exec -it <pod-name> -n scraper -- curl localhost:8000/api/v1/system/health
```

## Next Steps

1. Review [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for detailed instructions
2. Configure monitoring in [config/prometheus.yml](../../config/prometheus.yml)
3. Setup alerts in [config/alerts.yml](../../config/alerts.yml)
4. Customize Kubernetes resources in [k8s/](../../k8s/)
5. Enable GitHub Actions workflows

## Getting Help

- **Documentation:** https://github.com/thepingdoctor/scrape-api-docs
- **Issues:** https://github.com/thepingdoctor/scrape-api-docs/issues
- **CI/CD Pipeline:** `.github/workflows/ci-cd.yml`
- **Kubernetes Docs:** https://kubernetes.io/docs/
