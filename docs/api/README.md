# Documentation Scraper REST API

## Overview

Production-ready FastAPI REST API for scraping and exporting documentation websites.

## Features

- **Async Operations**: Non-blocking job execution with background processing
- **Job Management**: Create, monitor, cancel, and retry scraping jobs
- **Real-time Updates**: WebSocket support for live progress tracking
- **Multiple Export Formats**: Markdown, PDF, JSON, EPUB, HTML
- **Authentication**: API key and Bearer token support
- **Rate Limiting**: Per-IP and per-user rate limiting
- **Caching**: Multi-tier caching for improved performance
- **Monitoring**: Prometheus metrics and health checks
- **Docker Support**: Production-ready containerization

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Build and start the API
docker-compose up -d

# Check logs
docker-compose logs -f api

# Stop the API
docker-compose down
```

The API will be available at `http://localhost:8000`.

### Using Python Directly

```bash
# Install dependencies
pip install -r requirements-api.txt

# Run the API
uvicorn src.scrape_api_docs.api.main:app --reload --port 8000
```

## API Documentation

### Interactive Docs

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI Schema**: http://localhost:8000/api/openapi.json

### Core Endpoints

#### Create Scraping Job (Async)

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://docs.example.com",
    "options": {
      "max_depth": 10,
      "rate_limit": 2.0,
      "cache_enabled": true
    },
    "export_formats": ["markdown", "pdf"]
  }'
```

Response:
```json
{
  "job_id": "job_abc123xyz",
  "status": "queued",
  "created_at": "2025-10-26T19:00:00Z",
  "status_url": "/api/v1/jobs/job_abc123xyz",
  "websocket_url": "ws://localhost:8000/api/v1/jobs/job_abc123xyz/stream"
}
```

#### Get Job Status

```bash
curl "http://localhost:8000/api/v1/jobs/job_abc123xyz"
```

#### Download Export

```bash
curl -O "http://localhost:8000/api/v1/exports/job_abc123xyz/output.md"
```

#### WebSocket Progress Tracking

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/jobs/job_abc123xyz/stream');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log(update.type, update.data);
};
```

### Authentication

#### API Key (Header)

```bash
curl -H "X-API-Key: your_api_key_here" \
  "http://localhost:8000/api/v1/jobs"
```

#### Bearer Token

```bash
curl -H "Authorization: Bearer your_token_here" \
  "http://localhost:8000/api/v1/jobs"
```

## Configuration

### Environment Variables

```bash
# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
LOG_LEVEL=info

# Database
DATABASE_PATH=.scraper_jobs.db

# Storage
STORAGE_DIR=.scraper_storage

# Security
SECRET_KEY=your-secret-key
API_KEY_SALT=your-api-key-salt

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=120

# Scraping Defaults
DEFAULT_RATE_LIMIT=2.0
DEFAULT_TIMEOUT=30
DEFAULT_CACHE_TTL=3600
```

## Production Deployment

### Docker

```bash
# Build image
docker build -t scrape-api-docs:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/exports:/app/exports \
  -e SECRET_KEY=production-secret-key \
  scrape-api-docs:latest
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scraper-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: scrape-api-docs:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: scraper-secrets
              key: database-url
```

## Monitoring

### Health Check

```bash
curl http://localhost:8000/api/v1/system/health
```

### Metrics (Prometheus)

```bash
curl http://localhost:8000/api/v1/system/metrics
```

### System Stats

```bash
curl http://localhost:8000/api/v1/system/stats
```

## Performance

- **Async Processing**: Non-blocking I/O for high concurrency
- **Background Jobs**: Long-running scrapes don't block API responses
- **Connection Pooling**: Efficient HTTP connection reuse
- **Caching**: Multi-tier caching reduces redundant requests
- **Rate Limiting**: Prevents server overload

## Security

- **Input Validation**: Pydantic models validate all inputs
- **Authentication**: API key and Bearer token support
- **Rate Limiting**: Prevents abuse and DoS attacks
- **CORS**: Configurable cross-origin policies
- **HTTPS**: TLS/SSL support via reverse proxy

## Error Handling

All errors return consistent JSON format:

```json
{
  "error": {
    "code": "INVALID_URL",
    "message": "The provided URL is not accessible",
    "details": {...},
    "timestamp": "2025-10-26T19:00:00Z"
  }
}
```

## Rate Limits

Default limits:
- 60 requests per minute per IP
- Burst of 120 requests

Rate limit headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1698345600
```

## Support

- **Documentation**: `/api/docs`
- **Health Check**: `/api/v1/system/health`
- **GitHub**: https://github.com/thepingdoctor/scrape-api-docs

## License

MIT License - See LICENSE file for details
