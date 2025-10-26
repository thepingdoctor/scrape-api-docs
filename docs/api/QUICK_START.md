# FastAPI Quick Start Guide

## Installation & Setup

### Method 1: Docker (Recommended)

```bash
# Build and start the API
docker-compose -f docker-compose.api.yml up -d

# View logs
docker-compose -f docker-compose.api.yml logs -f api

# Stop the API
docker-compose -f docker-compose.api.yml down
```

### Method 2: Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-api.txt

# Run the API
uvicorn src.scrape_api_docs.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/api/docs
```

## Basic Usage Examples

### 1. Create a Scraping Job

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://docs.python.org/3/",
    "options": {
      "max_depth": 5,
      "rate_limit": 2.0,
      "cache_enabled": true
    },
    "export_formats": ["markdown", "json"]
  }'
```

Response:
```json
{
  "job_id": "job_abc123xyz",
  "status": "queued",
  "created_at": "2025-10-26T19:00:00Z",
  "estimated_duration": 10,
  "status_url": "/api/v1/jobs/job_abc123xyz",
  "websocket_url": "ws://localhost:8000/api/v1/jobs/job_abc123xyz/stream"
}
```

### 2. Check Job Status

```bash
curl http://localhost:8000/api/v1/jobs/job_abc123xyz
```

### 3. List All Jobs

```bash
curl "http://localhost:8000/api/v1/jobs?limit=10&status=completed"
```

### 4. Download Export

```bash
# Get export metadata
curl http://localhost:8000/api/v1/exports/job_abc123xyz/metadata

# Download file
curl -O http://localhost:8000/api/v1/exports/job_abc123xyz/output.md
```

### 5. WebSocket Progress Tracking (Python)

```python
import asyncio
import websockets
import json

async def watch_job(job_id):
    uri = f"ws://localhost:8000/api/v1/jobs/{job_id}/stream"

    async with websockets.connect(uri) as websocket:
        async for message in websocket:
            update = json.loads(message)
            print(f"{update['type']}: {update['data']}")

            if update['type'] in ['complete', 'error']:
                break

asyncio.run(watch_job("job_abc123xyz"))
```

### 6. WebSocket Progress Tracking (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/jobs/job_abc123xyz/stream');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log(`${update.type}:`, update.data);

  if (['complete', 'error', 'cancelled'].includes(update.type)) {
    ws.close();
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

## Advanced Features

### Validate URL Before Scraping

```bash
curl -X POST "http://localhost:8000/api/v1/scrape/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://docs.example.com",
    "options": {
      "max_depth": 10
    }
  }'
```

### Synchronous Scraping (Small Sites Only)

```bash
curl -X POST "http://localhost:8000/api/v1/scrape/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://small-docs.example.com",
    "options": {
      "max_depth": 3
    }
  }'
```

### Cancel Running Job

```bash
curl -X DELETE http://localhost:8000/api/v1/jobs/job_abc123xyz
```

### Retry Failed Job

```bash
curl -X POST http://localhost:8000/api/v1/jobs/job_abc123xyz/retry
```

## Configuration Options

### Scraping Options

```json
{
  "render_javascript": false,      // Enable Playwright for JS sites
  "max_depth": 10,                 // Maximum crawl depth
  "include_patterns": ["*/docs/*"], // URL patterns to include
  "exclude_patterns": ["*/blog/*"], // URL patterns to exclude
  "rate_limit": 2.0,               // Requests per second
  "timeout": 30,                   // Request timeout (seconds)
  "cache_enabled": true,           // Enable caching
  "cache_ttl": 3600,              // Cache TTL (seconds)
  "user_agent": "Custom UA",      // Custom User-Agent
  "follow_redirects": true,       // Follow HTTP redirects
  "verify_ssl": true              // Verify SSL certificates
}
```

### Export Formats

- `markdown` - Markdown format (.md)
- `pdf` - PDF document (.pdf)
- `json` - Structured JSON (.json)
- `epub` - EPUB ebook (.epub)
- `html` - Single-page HTML (.html)

### Job Priorities

- `low` - Background processing
- `normal` - Standard priority (default)
- `high` - Expedited processing
- `urgent` - Highest priority

## Monitoring & Debugging

### System Health

```bash
curl http://localhost:8000/api/v1/system/health
```

### System Statistics

```bash
curl http://localhost:8000/api/v1/system/stats
```

### Prometheus Metrics

```bash
curl http://localhost:8000/api/v1/system/metrics
```

### Job Logs

```bash
curl "http://localhost:8000/api/v1/jobs/job_abc123xyz/logs?limit=50"
```

## Troubleshooting

### API Not Starting

```bash
# Check logs
docker-compose -f docker-compose.api.yml logs api

# Check port availability
netstat -an | grep 8000
```

### Job Stuck in "queued" Status

- Check background worker status
- Review job logs
- Check system resources

### WebSocket Connection Issues

- Ensure WebSocket support in proxy/load balancer
- Check firewall rules
- Verify CORS configuration

### Rate Limit Errors

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Maximum 60 requests per minute allowed.",
    "retry_after": 60
  }
}
```

Wait for `retry_after` seconds before retrying.

## Next Steps

- Review full [API Documentation](./README.md)
- Explore [Interactive API Docs](http://localhost:8000/api/docs)
- Check [Architecture Documentation](../architecture/01-fastapi-architecture.md)
- Review [Examples](../../examples/)

## Support

- API Docs: http://localhost:8000/api/docs
- GitHub: https://github.com/thepingdoctor/scrape-api-docs
- Issues: https://github.com/thepingdoctor/scrape-api-docs/issues
