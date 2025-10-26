# Makefile for Documentation Scraper
# Provides convenient shortcuts for common development and deployment tasks

.PHONY: help install test lint format clean build docker k8s-deploy monitor

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
POETRY := poetry
DOCKER := docker
KUBECTL := kubectl
NAMESPACE := scraper

## help: Show this help message
help:
	@echo "Documentation Scraper - Available Commands:"
	@echo ""
	@sed -n 's/^##//p' ${MAKEFILE_LIST} | column -t -s ':' | sed -e 's/^/ /'

## install: Install project dependencies
install:
	$(POETRY) install --no-interaction

## install-dev: Install project with development dependencies
install-dev:
	$(POETRY) install --no-interaction --with dev

## test: Run test suite
test:
	$(POETRY) run pytest tests/ -v --cov=src/scrape_api_docs --cov-report=html

## test-watch: Run tests in watch mode
test-watch:
	$(POETRY) run pytest-watch tests/

## lint: Run linting checks
lint:
	$(POETRY) run black --check src/ tests/
	$(POETRY) run flake8 src/ tests/
	$(POETRY) run mypy src/

## format: Auto-format code
format:
	$(POETRY) run black src/ tests/
	$(POETRY) run isort src/ tests/

## security: Run security checks
security:
	$(POETRY) run bandit -r src/
	$(POETRY) run pip install safety
	$(POETRY) export -f requirements.txt --without-hashes | $(POETRY) run safety check --stdin

## clean: Clean build artifacts and cache
clean:
	rm -rf dist/ build/ *.egg-info
	rm -rf .pytest_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

## build: Build Python package
build: clean
	$(POETRY) build

## docker-build: Build Docker image
docker-build:
	$(DOCKER) build -t scraper-api:latest .

## docker-build-dev: Build development Docker image
docker-build-dev:
	$(DOCKER) build --target development -t scraper-api:dev .

## docker-run-cli: Run Docker container in CLI mode
docker-run-cli:
	$(DOCKER) run --rm -v $(PWD)/output:/data scraper-api:latest https://docs.example.com

## docker-run-ui: Run Docker container with web UI
docker-run-ui:
	$(DOCKER) run -d -p 8501:8501 -v $(PWD)/output:/data scraper-api:latest \
		streamlit run /app/src/scrape_api_docs/streamlit_app.py

## docker-compose-up: Start all services with docker-compose
docker-compose-up:
	docker-compose up -d

## docker-compose-down: Stop all services
docker-compose-down:
	docker-compose down -v

## docker-compose-logs: View docker-compose logs
docker-compose-logs:
	docker-compose logs -f

## k8s-create-namespace: Create Kubernetes namespace
k8s-create-namespace:
	$(KUBECTL) apply -f k8s/namespace.yml

## k8s-deploy-secrets: Deploy Kubernetes secrets (update values first!)
k8s-deploy-secrets:
	@echo "WARNING: Update secret values in k8s/secrets.yml before deploying!"
	$(KUBECTL) apply -f k8s/secrets.yml

## k8s-deploy-redis: Deploy Redis to Kubernetes
k8s-deploy-redis:
	$(KUBECTL) apply -f k8s/redis-statefulset.yml

## k8s-deploy-app: Deploy application to Kubernetes
k8s-deploy-app:
	$(KUBECTL) apply -f k8s/deployment.yml
	$(KUBECTL) apply -f k8s/worker-deployment.yml

## k8s-deploy-ingress: Deploy ingress controller
k8s-deploy-ingress:
	$(KUBECTL) apply -f k8s/ingress.yml

## k8s-deploy-all: Deploy everything to Kubernetes
k8s-deploy-all: k8s-create-namespace k8s-deploy-secrets k8s-deploy-redis k8s-deploy-app k8s-deploy-ingress
	@echo "Deployment complete! Check status with: make k8s-status"

## k8s-status: Check Kubernetes deployment status
k8s-status:
	$(KUBECTL) get all -n $(NAMESPACE)
	$(KUBECTL) get ingress -n $(NAMESPACE)
	$(KUBECTL) get pvc -n $(NAMESPACE)

## k8s-logs-api: View API pod logs
k8s-logs-api:
	$(KUBECTL) logs -l app=scraper-api -n $(NAMESPACE) --tail=100 -f

## k8s-logs-worker: View worker pod logs
k8s-logs-worker:
	$(KUBECTL) logs -l app=scraper-worker -n $(NAMESPACE) --tail=100 -f

## k8s-scale-api: Scale API deployment (usage: make k8s-scale-api REPLICAS=5)
k8s-scale-api:
	$(KUBECTL) scale deployment scraper-api --replicas=$(REPLICAS) -n $(NAMESPACE)

## k8s-scale-worker: Scale worker deployment (usage: make k8s-scale-worker REPLICAS=10)
k8s-scale-worker:
	$(KUBECTL) scale deployment scraper-worker --replicas=$(REPLICAS) -n $(NAMESPACE)

## k8s-delete: Delete all Kubernetes resources
k8s-delete:
	$(KUBECTL) delete namespace $(NAMESPACE)

## monitor-prometheus: Port forward to Prometheus
monitor-prometheus:
	$(KUBECTL) port-forward -n monitoring svc/prometheus 9090:9090

## monitor-grafana: Port forward to Grafana
monitor-grafana:
	$(KUBECTL) port-forward -n monitoring svc/grafana 3000:80

## ci-local: Run CI checks locally
ci-local:
	make lint
	make test
	make security
	make build

## release: Create a new release (usage: make release VERSION=1.0.0)
release:
	@echo "Creating release $(VERSION)..."
	git tag -a v$(VERSION) -m "Release v$(VERSION)"
	git push origin v$(VERSION)
	@echo "Release v$(VERSION) created! GitHub Actions will handle the deployment."

## dev-setup: Setup development environment
dev-setup: install-dev
	@echo "Installing pre-commit hooks..."
	$(POETRY) run pre-commit install
	@echo "Development environment ready!"

## benchmark: Run performance benchmarks
benchmark:
	$(POETRY) run pytest tests/benchmarks/ -v --benchmark-only
