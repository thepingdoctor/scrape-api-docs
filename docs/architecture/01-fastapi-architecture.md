# FastAPI REST API Architecture
## Documentation Scraper API Design

**Version:** 2.0.0
**Date:** 2025-10-26
**Status:** Design Phase

---

## Overview

The FastAPI-based REST API provides programmatic access to the documentation scraper with full async support, job management, and real-time progress tracking.

---

## API Architecture

### Design Principles
1. **RESTful design** with resource-oriented endpoints
2. **Async-first** using FastAPI's native async support
3. **Type-safe** with Pydantic models for validation
4. **Versioned API** for backward compatibility
5. **Observable** with built-in metrics and health checks

### API Structure
```
api/
├── v1/
│   ├── scrape/          # Scraping operations
│   ├── jobs/            # Job management
│   ├── auth/            # Authentication
│   ├── exports/         # Export operations
│   └── system/          # Health, metrics, status
└── v2/                  # Future version
```

---

## Endpoint Specifications

### 1. Scraping Operations

#### POST /api/v1/scrape
Create a new scraping job

**Request Body:**
```json
{
  "url": "https://docs.example.com",
  "options": {
    "render_javascript": false,
    "max_depth": 10,
    "include_patterns": ["*/docs/*"],
    "exclude_patterns": ["*/blog/*"],
    "rate_limit": 2.0,
    "timeout": 30,
    "cache_enabled": true,
    "cache_ttl": 3600
  },
  "export_formats": ["markdown", "pdf", "json"],
  "authentication": {
    "type": "bearer",
    "token": "secret-token"
  },
  "webhook_url": "https://callback.example.com/webhook",
  "priority": "normal"
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "job_abc123xyz",
  "status": "queued",
  "created_at": "2025-10-26T19:00:00Z",
  "estimated_duration": 300,
  "status_url": "/api/v1/jobs/job_abc123xyz",
  "websocket_url": "ws://api.example.com/api/v1/jobs/job_abc123xyz/stream"
}
```

#### POST /api/v1/scrape/sync
Synchronous scraping for small sites (blocks until complete)

**Request Body:** Same as async endpoint

**Response (200 OK):**
```json
{
  "job_id": "job_abc123xyz",
  "status": "completed",
  "duration": 45.2,
  "pages_scraped": 23,
  "exports": [
    {
      "format": "markdown",
      "url": "/api/v1/exports/job_abc123xyz/output.md",
      "size_bytes": 524288
    }
  ],
  "statistics": {
    "total_pages": 23,
    "cache_hits": 15,
    "cache_misses": 8,
    "errors": 0,
    "avg_page_time": 1.96
  }
}
```

#### POST /api/v1/scrape/validate
Validate URL and scraping options without executing

**Request Body:**
```json
{
  "url": "https://docs.example.com",
  "options": { ... }
}
```

**Response (200 OK):**
```json
{
  "valid": true,
  "estimated_pages": 50,
  "estimated_duration": 600,
  "warnings": [
    "Site uses JavaScript rendering - enable render_javascript option"
  ],
  "recommendations": {
    "render_javascript": true,
    "rate_limit": 1.5
  }
}
```

---

### 2. Job Management

#### GET /api/v1/jobs
List all jobs with filtering and pagination

**Query Parameters:**
- `status`: Filter by status (queued, running, completed, failed)
- `limit`: Results per page (default: 20, max: 100)
- `offset`: Pagination offset
- `sort`: Sort field (created_at, updated_at, duration)
- `order`: Sort order (asc, desc)

**Response (200 OK):**
```json
{
  "jobs": [
    {
      "job_id": "job_abc123xyz",
      "url": "https://docs.example.com",
      "status": "completed",
      "created_at": "2025-10-26T19:00:00Z",
      "completed_at": "2025-10-26T19:05:30Z",
      "duration": 330.5,
      "pages_scraped": 45,
      "exports_available": ["markdown", "pdf"]
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

#### GET /api/v1/jobs/{job_id}
Get detailed job status and results

**Response (200 OK):**
```json
{
  "job_id": "job_abc123xyz",
  "url": "https://docs.example.com",
  "status": "running",
  "progress": {
    "current_page": 23,
    "total_pages": 45,
    "percent_complete": 51,
    "current_operation": "Rendering JavaScript page"
  },
  "created_at": "2025-10-26T19:00:00Z",
  "started_at": "2025-10-26T19:00:05Z",
  "estimated_completion": "2025-10-26T19:10:00Z",
  "statistics": {
    "pages_discovered": 45,
    "pages_processed": 23,
    "cache_hits": 15,
    "cache_misses": 8,
    "errors": 0
  },
  "exports": [],
  "logs": [
    {
      "timestamp": "2025-10-26T19:00:05Z",
      "level": "info",
      "message": "Started crawling https://docs.example.com"
    }
  ]
}
```

#### DELETE /api/v1/jobs/{job_id}
Cancel a running job or delete completed job data

**Response (200 OK):**
```json
{
  "job_id": "job_abc123xyz",
  "status": "cancelled",
  "message": "Job cancelled successfully"
}
```

#### GET /api/v1/jobs/{job_id}/stream (WebSocket)
Real-time progress updates via WebSocket

**WebSocket Messages:**
```json
{
  "type": "progress",
  "data": {
    "job_id": "job_abc123xyz",
    "status": "running",
    "current_page": 23,
    "total_pages": 45,
    "percent_complete": 51
  }
}
```

```json
{
  "type": "log",
  "data": {
    "timestamp": "2025-10-26T19:00:05Z",
    "level": "info",
    "message": "Processing page: /docs/getting-started"
  }
}
```

```json
{
  "type": "complete",
  "data": {
    "job_id": "job_abc123xyz",
    "status": "completed",
    "exports": [...]
  }
}
```

---

### 3. Export Operations

#### GET /api/v1/exports/{job_id}/{filename}
Download exported documentation

**Response (200 OK):**
- Content-Type: `application/pdf`, `application/epub+zip`, `text/markdown`, `application/json`
- Content-Disposition: `attachment; filename="output.pdf"`
- Body: File content

#### POST /api/v1/exports/{job_id}/convert
Convert existing export to different format

**Request Body:**
```json
{
  "target_format": "epub",
  "options": {
    "include_toc": true,
    "metadata": {
      "title": "API Documentation",
      "author": "Example Corp"
    }
  }
}
```

**Response (202 Accepted):**
```json
{
  "conversion_id": "conv_xyz789",
  "status": "processing",
  "status_url": "/api/v1/exports/conversions/conv_xyz789"
}
```

#### GET /api/v1/exports/{job_id}/metadata
Get export metadata and available formats

**Response (200 OK):**
```json
{
  "job_id": "job_abc123xyz",
  "formats": {
    "markdown": {
      "available": true,
      "url": "/api/v1/exports/job_abc123xyz/output.md",
      "size_bytes": 524288,
      "created_at": "2025-10-26T19:05:30Z"
    },
    "pdf": {
      "available": true,
      "url": "/api/v1/exports/job_abc123xyz/output.pdf",
      "size_bytes": 1048576,
      "created_at": "2025-10-26T19:06:00Z"
    },
    "epub": {
      "available": false,
      "message": "Not requested in original job"
    }
  }
}
```

---

### 4. Authentication Management

#### POST /api/v1/auth/credentials
Store authentication credentials for a domain

**Request Body:**
```json
{
  "domain": "api.example.com",
  "auth_type": "bearer",
  "credentials": {
    "token": "secret-token"
  },
  "expires_at": "2025-12-31T23:59:59Z"
}
```

**Response (201 Created):**
```json
{
  "credential_id": "cred_abc123",
  "domain": "api.example.com",
  "auth_type": "bearer",
  "created_at": "2025-10-26T19:00:00Z"
}
```

#### GET /api/v1/auth/credentials
List stored credentials

**Response (200 OK):**
```json
{
  "credentials": [
    {
      "credential_id": "cred_abc123",
      "domain": "api.example.com",
      "auth_type": "bearer",
      "created_at": "2025-10-26T19:00:00Z",
      "expires_at": "2025-12-31T23:59:59Z"
    }
  ]
}
```

#### DELETE /api/v1/auth/credentials/{credential_id}
Delete stored credential

---

### 5. System Operations

#### GET /api/v1/system/health
Health check endpoint

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "uptime": 86400,
  "dependencies": {
    "cache": "healthy",
    "storage": "healthy",
    "database": "healthy",
    "playwright": "healthy"
  }
}
```

#### GET /api/v1/system/metrics
System metrics (Prometheus format)

**Response (200 OK):**
```
# HELP scraper_jobs_total Total number of scraping jobs
# TYPE scraper_jobs_total counter
scraper_jobs_total{status="completed"} 150
scraper_jobs_total{status="failed"} 5

# HELP scraper_pages_scraped_total Total pages scraped
# TYPE scraper_pages_scraped_total counter
scraper_pages_scraped_total 6750

# HELP scraper_cache_hit_rate Cache hit rate
# TYPE scraper_cache_hit_rate gauge
scraper_cache_hit_rate 0.82
```

#### GET /api/v1/system/stats
System statistics

**Response (200 OK):**
```json
{
  "jobs": {
    "total": 155,
    "completed": 150,
    "failed": 5,
    "running": 3,
    "queued": 2
  },
  "performance": {
    "avg_job_duration": 285.5,
    "avg_pages_per_job": 45,
    "avg_page_processing_time": 2.3,
    "cache_hit_rate": 0.82
  },
  "resources": {
    "cache_size_mb": 512,
    "storage_used_gb": 15.5,
    "active_workers": 5
  }
}
```

---

## Data Models (Pydantic)

### ScrapeRequest
```python
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict
from enum import Enum

class AuthType(str, Enum):
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"
    COOKIE = "cookie"

class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class ScrapeOptions(BaseModel):
    render_javascript: bool = False
    max_depth: int = Field(default=10, ge=1, le=100)
    include_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    rate_limit: float = Field(default=2.0, ge=0.1, le=10.0)
    timeout: int = Field(default=30, ge=5, le=300)
    cache_enabled: bool = True
    cache_ttl: int = Field(default=3600, ge=0)
    user_agent: Optional[str] = None

class AuthCredentials(BaseModel):
    type: AuthType
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    api_key: Optional[str] = None
    cookies: Optional[Dict[str, str]] = None

class ScrapeRequest(BaseModel):
    url: HttpUrl
    options: ScrapeOptions = ScrapeOptions()
    export_formats: List[str] = ["markdown"]
    authentication: Optional[AuthCredentials] = None
    webhook_url: Optional[HttpUrl] = None
    priority: Priority = Priority.NORMAL
    metadata: Optional[Dict[str, str]] = None
```

### JobStatus
```python
from enum import Enum
from datetime import datetime

class JobStatusEnum(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobProgress(BaseModel):
    current_page: int
    total_pages: int
    percent_complete: float
    current_operation: str

class JobStatistics(BaseModel):
    pages_discovered: int = 0
    pages_processed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    avg_page_time: float = 0.0

class JobStatus(BaseModel):
    job_id: str
    url: str
    status: JobStatusEnum
    progress: Optional[JobProgress] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    duration: Optional[float] = None
    statistics: JobStatistics = JobStatistics()
    exports: List[Dict] = []
    error_message: Optional[str] = None
```

---

## API Implementation Structure

### Directory Layout
```
src/scrape_api_docs/api/
├── __init__.py
├── main.py                 # FastAPI app initialization
├── dependencies.py         # Dependency injection
├── middleware.py           # Custom middleware
├── routers/
│   ├── __init__.py
│   ├── scrape.py          # Scraping endpoints
│   ├── jobs.py            # Job management
│   ├── exports.py         # Export endpoints
│   ├── auth.py            # Authentication
│   └── system.py          # System endpoints
├── models/
│   ├── __init__.py
│   ├── requests.py        # Request models
│   ├── responses.py       # Response models
│   └── schemas.py         # Database schemas
├── services/
│   ├── __init__.py
│   ├── scraper_service.py # Core scraping logic
│   ├── job_service.py     # Job management
│   ├── export_service.py  # Export handling
│   └── auth_service.py    # Authentication
└── background/
    ├── __init__.py
    ├── tasks.py           # Background task definitions
    └── worker.py          # Worker process
```

### Main Application (main.py)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .routers import scrape, jobs, exports, auth, system
from .middleware import LoggingMiddleware, RateLimitMiddleware

app = FastAPI(
    title="Documentation Scraper API",
    version="2.0.0",
    description="REST API for scraping and exporting documentation",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Routers
app.include_router(scrape.router, prefix="/api/v1/scrape", tags=["scrape"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(exports.router, prefix="/api/v1/exports", tags=["exports"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])

# Metrics
Instrumentator().instrument(app).expose(app)

@app.on_event("startup")
async def startup_event():
    # Initialize services
    pass

@app.on_event("shutdown")
async def shutdown_event():
    # Cleanup
    pass
```

---

## Authentication & Security

### API Key Authentication
```python
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key not in valid_api_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    return api_key
```

### Rate Limiting
```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host

        # Check rate limit
        if not await rate_limiter.check(client_ip):
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded"}
            )

        return await call_next(request)
```

---

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "INVALID_URL",
    "message": "The provided URL is not accessible",
    "details": {
      "url": "https://invalid.example.com",
      "reason": "Connection timeout"
    },
    "timestamp": "2025-10-26T19:00:00Z",
    "request_id": "req_abc123"
  }
}
```

### Error Codes
- `INVALID_URL`: URL validation failed
- `AUTHENTICATION_FAILED`: Authentication credentials invalid
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `JOB_NOT_FOUND`: Job ID does not exist
- `SCRAPING_FAILED`: Scraping operation failed
- `EXPORT_FAILED`: Export generation failed
- `INTERNAL_ERROR`: Unexpected server error

---

## Performance Considerations

### Async Request Handling
- All endpoints use `async def` for non-blocking I/O
- Database queries use async drivers (asyncpg, motor)
- HTTP requests use aiohttp

### Connection Pooling
- Reuse HTTP connections with aiohttp session
- Database connection pooling
- Redis connection pooling

### Caching Strategies
- Response caching for GET requests
- ETags for conditional requests
- Cache-Control headers

### Background Processing
- Long-running scrapes executed in background workers
- Job queue (Celery, ARQ, or RQ)
- Progress updates via WebSocket or polling

---

## Testing Strategy

### Unit Tests
```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_scrape_job():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/scrape",
            json={
                "url": "https://docs.example.com",
                "options": {"max_depth": 5}
            }
        )
        assert response.status_code == 202
        assert "job_id" in response.json()
```

### Integration Tests
- Test complete scraping workflows
- Test WebSocket connections
- Test export generation
- Test error scenarios

### Load Testing
- Use Locust or k6 for load testing
- Target: 100 concurrent requests
- Monitor response times and resource usage

---

## Deployment

### Docker Container
```dockerfile
FROM python:3.11-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates && \
    playwright install-deps

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

COPY . .

CMD ["uvicorn", "src.scrape_api_docs.api.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4"]
```

### Kubernetes Deployment
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
        image: scraper-api:2.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: scraper-secrets
              key: database-url
        resources:
          limits:
            memory: "1Gi"
            cpu: "500m"
```

---

## Monitoring & Observability

### Metrics (Prometheus)
- Request rate and latency
- Job success/failure rates
- Cache hit rates
- Worker queue depth

### Logging (Structured)
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "scrape_started",
    job_id="job_abc123",
    url="https://docs.example.com",
    options={"max_depth": 10}
)
```

### Tracing (OpenTelemetry)
- Distributed tracing for request flows
- Track scraping job execution across workers
- Database query performance

---

## API Versioning Strategy

### Version Support
- **v1**: Current stable version (2.0.0)
- **v2**: Future version with breaking changes
- Support n-1 versions (v1 supported when v2 released)

### Deprecation Policy
- 6-month notice for deprecation
- Clear migration guide provided
- Sunset headers in responses

---

## Next Steps

1. Implement core FastAPI application structure
2. Create Pydantic models for request/response validation
3. Implement async scraper service
4. Build job queue and background worker system
5. Add WebSocket support for progress tracking
6. Integrate existing rate limiting, caching, auth modules
7. Write comprehensive API tests
8. Create OpenAPI documentation
9. Set up monitoring and metrics
10. Deploy to staging environment for testing
