# Documentation Scraper

A high-performance, production-ready Python documentation scraper with async architecture, FastAPI REST API, JavaScript rendering, and comprehensive export formats. Built for enterprise-scale documentation archival and processing.

## 🚀 Key Features

### 🐙 GitHub Repository Scraping (NEW in v0.2.0)
- **Direct repo scraping**: Scrape documentation from GitHub without cloning
- **Folder-specific**: Target specific directories (e.g., `/docs`, `/wiki`)
- **Auto-detection**: Automatically detects GitHub URLs in UI
- **Rate limiting**: Handles GitHub API limits (60/hr unauth, 5,000/hr with token)
- **Link conversion**: Converts relative links to absolute GitHub URLs
- **Multiple formats**: HTTPS, SSH, tree, blob URL support

### ⚡ High-Performance Async Architecture (5-10x Faster)
- **Async scraping**: 2.5 pages/sec (vs 0.5 sync)
- **Connection pooling**: Reusable HTTP connections with DNS caching
- **Priority queue**: Intelligent task scheduling and resource management
- **Rate limiting**: Non-blocking token bucket algorithm with backoff
- **Worker pool**: Concurrent processing with semaphore-based control

### 🔌 FastAPI REST API (23+ Endpoints)
- **Async job management**: Create, monitor, and cancel scraping jobs
- **Real-time progress**: WebSocket streaming for live updates
- **Multiple export formats**: PDF, EPUB, HTML, JSON
- **Authentication**: Token-based API security
- **System monitoring**: Health checks, metrics, and diagnostics

### 🎨 JavaScript Rendering & SPA Support
- **Hybrid rendering**: Automatic detection of static vs dynamic content
- **Playwright integration**: Full JavaScript execution with browser pool
- **SPA detection**: React, Vue, Angular, Ember framework support
- **Resource optimization**: Intelligent browser lifecycle management

### 📦 Export Formats
- **Markdown**: Clean, consolidated documentation
- **PDF**: Professional documents via WeasyPrint
- **EPUB**: E-book format for offline reading
- **HTML**: Standalone HTML with embedded styles
- **JSON**: Structured data for programmatic access

### 🔒 Security & Compliance
- **SSRF prevention**: URL validation and private IP blocking
- **robots.txt compliance**: Automatic crawl delay and permission checks
- **Content sanitization**: XSS protection and safe HTML handling
- **Rate limiting**: Configurable request throttling per domain

### 🐳 Production Deployment
- **Docker**: Multi-stage builds for optimized images
- **Kubernetes**: Complete deployment manifests with autoscaling
- **CI/CD**: GitHub Actions with automated testing and security scans
- **Monitoring**: Prometheus metrics and alerting rules

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
  - [Web Interface (Streamlit)](#web-interface-streamlit-ui)
  - [REST API](#rest-api)
  - [Command Line](#command-line-interface)
  - [Python API](#python-api)
- [Features](#features-in-depth)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Development](#development)
- [Documentation](#documentation)
- [Architecture](#architecture)

## 🎯 Quick Start

### Basic Scraping
```bash
# Install
pip install git+https://github.com/thepingdoctor/scrape-api-docs.git

# Scrape with async (5-10x faster)
scrape-docs https://docs.example.com

# Launch web UI
scrape-docs-ui
```

### REST API
```bash
# Using Docker
docker-compose up -d

# API available at http://localhost:8000
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://docs.example.com", "output_format": "pdf"}'
```

### Python API
```python
import asyncio
from scrape_api_docs import AsyncDocumentationScraper

async def main():
    scraper = AsyncDocumentationScraper(max_workers=10)
    result = await scraper.scrape_site('https://docs.example.com')
    print(f"Scraped {result.total_pages} pages at {result.throughput:.2f} pages/sec")

asyncio.run(main())
```

## 📦 Installation

### Requirements
- Python 3.11 or higher
- Poetry (recommended) or pip

### Using Poetry (Recommended)
```bash
git clone https://github.com/thepingdoctor/scrape-api-docs
cd scrape-api-docs
poetry install

# For all export formats (PDF, EPUB)
poetry install --extras all-formats

# Activate virtual environment
poetry shell
```

### Using pip
```bash
pip install git+https://github.com/thepingdoctor/scrape-api-docs.git

# With all export formats
pip install "git+https://github.com/thepingdoctor/scrape-api-docs.git#egg=scrape-api-docs[all-formats]"
```

### Using Docker
```bash
# Basic scraper
docker pull ghcr.io/thepingdoctor/scrape-api-docs:latest

# API server
docker-compose -f docker-compose.api.yml up -d
```

## 🎮 Usage

### Web Interface (Streamlit UI)

Launch the interactive web interface:

```bash
scrape-docs-ui
```

Features:
- 📝 URL input with real-time validation
- ⚙️ Advanced configuration (timeout, max pages, custom filename)
- 📦 **Multiple export formats**: Markdown, PDF, EPUB, HTML, JSON
- 📊 Real-time progress tracking with visual feedback
- 📄 Results preview and downloadable output
- 💾 Direct file download from browser (files saved to `tmp/` directory)
- 🎨 Modern, user-friendly interface

**Export Formats:**
- **Markdown** (default) - Clean, consolidated documentation
- **PDF** - Professional documents via WeasyPrint
- **EPUB** - E-book format for offline reading
- **HTML** - Standalone HTML with embedded styles
- **JSON** - Structured data for programmatic access

**Note:** Scraped files are temporarily stored in the `tmp/` directory (git-ignored) and can be downloaded directly from the browser interface. PDF and EPUB formats require additional dependencies: `pip install scrape-api-docs[all-formats]`

**For detailed UI guide, see [STREAMLIT_UI_GUIDE.md](STREAMLIT_UI_GUIDE.md)**

### REST API

Start the API server:

```bash
# Development
uvicorn scrape_api_docs.api.main:app --reload

# Production with Docker
docker-compose -f docker-compose.api.yml up -d

# Using make
make docker-api
```

#### API Endpoints (23+ total)

**Scraping Operations:**
```bash
# Create async scraping job
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://docs.example.com",
    "output_format": "markdown",
    "max_pages": 100
  }'

# Get job status
curl "http://localhost:8000/api/v1/jobs/{job_id}"

# WebSocket progress streaming
wscat -c "ws://localhost:8000/api/v1/jobs/{job_id}/stream"
```

**Export Formats:**
```bash
# Export to PDF
curl -X POST "http://localhost:8000/api/v1/exports/pdf" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "abc123"}'

# Export to EPUB
curl -X POST "http://localhost:8000/api/v1/exports/epub" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "abc123", "title": "API Documentation"}'
```

**System Endpoints:**
```bash
# Health check
curl "http://localhost:8000/api/v1/system/health"

# Metrics
curl "http://localhost:8000/api/v1/system/metrics"
```

**Full API documentation:** http://localhost:8000/docs

### Command-Line Interface

```bash
# Basic usage
scrape-docs https://docs.example.com

# With options
scrape-docs https://docs.example.com \
  --output my-docs.md \
  --max-pages 50 \
  --timeout 30

# Enable JavaScript rendering
scrape-docs https://spa-app.example.com \
  --enable-js \
  --browser-pool-size 3

# Export to PDF
scrape-docs https://docs.example.com \
  --format pdf \
  --output docs.pdf
```

### Python API

#### Async Scraper (Recommended - 5-10x Faster)

```python
import asyncio
from scrape_api_docs import AsyncDocumentationScraper

async def main():
    # Initialize with custom settings
    scraper = AsyncDocumentationScraper(
        max_workers=10,
        rate_limit=10.0,  # requests per second
        timeout=30,
        enable_js=True
    )

    # Scrape site
    result = await scraper.scrape_site(
        'https://docs.example.com',
        output_file='output.md',
        max_pages=100
    )

    # Results
    print(f"Pages scraped: {result.total_pages}")
    print(f"Throughput: {result.throughput:.2f} pages/sec")
    print(f"Errors: {len(result.errors)}")
    print(f"Duration: {result.duration:.2f}s")

asyncio.run(main())
```

#### Synchronous Scraper (Legacy)

```python
from scrape_api_docs import scrape_site

# Simple usage
scrape_site('https://docs.example.com')

# With options
scrape_site(
    'https://docs.example.com',
    output_file='custom-output.md',
    max_pages=50,
    timeout=30
)
```

#### JavaScript Rendering

```python
import asyncio
from scrape_api_docs import AsyncDocumentationScraper

async def scrape_spa():
    scraper = AsyncDocumentationScraper(
        enable_js=True,
        browser_pool_size=3,
        browser_timeout=30000
    )

    result = await scraper.scrape_site('https://react-docs.example.com')
    print(f"Scraped SPA: {result.total_pages} pages")

asyncio.run(scrape_spa())
```

#### Export Formats

```python
from scrape_api_docs.exporters import (
    PDFExporter,
    EPUBExporter,
    HTMLExporter,
    ExportOrchestrator
)

# Export to PDF
pdf_exporter = PDFExporter()
pdf_exporter.export('output.md', 'output.pdf', metadata={
    'title': 'API Documentation',
    'author': 'Your Name'
})

# Export to EPUB
epub_exporter = EPUBExporter()
epub_exporter.export('output.md', 'output.epub', metadata={
    'title': 'API Documentation',
    'language': 'en'
})

# Multi-format export
orchestrator = ExportOrchestrator()
orchestrator.export_multiple('output.md', ['pdf', 'epub', 'html'])
```

## 🔧 Configuration

### Environment Variables

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Scraper Settings
MAX_WORKERS=10
RATE_LIMIT=10.0
REQUEST_TIMEOUT=30
MAX_PAGES=1000

# JavaScript Rendering
ENABLE_JS=false
BROWSER_POOL_SIZE=3
BROWSER_TIMEOUT=30000

# Security
ENABLE_ROBOTS_TXT=true
BLOCK_PRIVATE_IPS=true
```

### Configuration File (YAML)

```yaml
# config/default.yaml
scraper:
  max_workers: 10
  rate_limit: 10.0
  timeout: 30
  user_agent: "DocumentationScraper/2.0"

javascript:
  enabled: false
  pool_size: 3
  timeout: 30000

security:
  robots_txt: true
  block_private_ips: true
  max_content_size: 10485760  # 10MB

export:
  default_format: markdown
  pdf_options:
    page_size: A4
    margin: 20mm
```

## 🐳 Deployment

### Docker

```bash
# Build image
docker build -t scrape-api-docs .

# Run scraper
docker run -v $(pwd)/output:/output scrape-api-docs \
  https://docs.example.com

# Run API server
docker-compose -f docker-compose.api.yml up -d
```

### Kubernetes

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/secrets.yml
kubectl apply -f k8s/deployment.yml
kubectl apply -f k8s/ingress.yml

# Scale workers
kubectl scale deployment scraper-worker --replicas=5 -n scraper

# Using make
make k8s-deploy
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    image: scrape-api-docs:latest
    ports:
      - "8000:8000"
    environment:
      - MAX_WORKERS=10
      - ENABLE_JS=true
    volumes:
      - ./output:/output
```

## 🛠️ Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/thepingdoctor/scrape-api-docs
cd scrape-api-docs

# Install dependencies
poetry install --with dev

# Activate virtual environment
poetry shell
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test suite
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage
make test-coverage
```

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Type checking
make typecheck

# Security scan
make security-scan
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## 📚 Documentation

### Comprehensive Guides
- [API Implementation Summary](docs/api/README.md)
- [Async Quick Start](docs/ASYNC_QUICK_START.md)
- [JavaScript Rendering Guide](docs/JAVASCRIPT_RENDERING.md)
- [Export Formats Usage](docs/EXPORT_USAGE.md)
- [Deployment Guide](docs/deployment/DEPLOYMENT_GUIDE.md)

### Architecture Documentation
- [System Overview](docs/architecture/00-system-overview.md)
- [FastAPI Architecture](docs/architecture/01-fastapi-architecture.md)
- [Async Refactor Plan](docs/architecture/02-async-refactor-plan.md)
- [JavaScript Rendering](docs/architecture/03-javascript-rendering.md)
- [Export Formats](docs/architecture/04-export-formats.md)
- [Deployment Architecture](docs/architecture/05-deployment-architecture.md)

### Phase Summaries
- [Phase 1: Security & Compliance](docs/PHASE1_IMPLEMENTATION.md)
- [Phase 2: Async Architecture](docs/PHASE2_ASYNC_SUMMARY.md)
- [Phase 3: FastAPI REST API](docs/PHASE3_SUMMARY.md)

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                   Client Layer                          │
│  (CLI, Web UI, REST API, Python SDK)                   │
└─────────────────────────────────────────────────────────┘
                         │
┌─────────────────────────────────────────────────────────┐
│              Scraping Engine (Async)                    │
│  • AsyncHTTPClient (Connection Pooling)                 │
│  • AsyncWorkerPool (Concurrency Control)                │
│  • AsyncRateLimiter (Token Bucket)                      │
│  • Priority Queue (BFS Scheduling)                      │
└─────────────────────────────────────────────────────────┘
                         │
┌─────────────────────────────────────────────────────────┐
│           Rendering Layer (Hybrid)                      │
│  • Static HTML Parser (BeautifulSoup)                   │
│  • JavaScript Renderer (Playwright)                     │
│  • SPA Detector (Framework Detection)                   │
└─────────────────────────────────────────────────────────┘
                         │
┌─────────────────────────────────────────────────────────┐
│           Export Layer (Multi-format)                   │
│  • Markdown, PDF, EPUB, HTML, JSON                      │
│  • Template Engine (Jinja2)                             │
│  • Export Orchestrator                                  │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Core**: Python 3.11+, asyncio, aiohttp
- **API**: FastAPI, Pydantic, uvicorn
- **Rendering**: BeautifulSoup4, Playwright, markdownify
- **Export**: WeasyPrint (PDF), EbookLib (EPUB), Jinja2
- **Storage**: SQLite (jobs), filesystem (output)
- **Deployment**: Docker, Kubernetes, GitHub Actions
- **Monitoring**: Prometheus, structured logging

## 📊 Performance Benchmarks

| Metric | Sync Scraper | Async Scraper | Improvement |
|--------|--------------|---------------|-------------|
| Throughput | 0.5 pages/sec | 2.5 pages/sec | **5x** |
| 100-page site | 200 seconds | 40 seconds | **5x faster** |
| Memory usage | ~100 MB | ~150 MB | Acceptable |
| CPU usage | 15% | 45% | Efficient |

## 🔐 Security Features

- **SSRF Prevention**: Private IP blocking, URL validation
- **robots.txt Compliance**: Automatic crawl delay and permission checks
- **Rate Limiting**: Token bucket algorithm with per-domain limits
- **Content Sanitization**: XSS protection, safe HTML handling
- **Input Validation**: Pydantic models, URL whitelisting
- **Authentication**: Token-based API security (JWT)

## 📝 Examples

See the [examples/](examples/) directory for:
- Integration examples
- Authentication managers
- Caching strategies
- Rate limiting configurations
- Custom export pipelines

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is designed for legitimate purposes such as documentation archival for personal or internal team use. Users are responsible for:
- Ensuring they have the right to scrape any website
- Complying with the website's terms of service and robots.txt
- Respecting rate limits and server resources

The author is not responsible for any misuse of this tool. This software is provided "as is" without warranty of any kind.

## 🙏 Acknowledgments

- Built with FastAPI, Playwright, and BeautifulSoup
- Inspired by documentation tools like Docusaurus and MkDocs
- Performance optimizations based on async best practices

## 📞 Support

- **Issues**: https://github.com/thepingdoctor/scrape-api-docs/issues
- **Documentation**: https://github.com/thepingdoctor/scrape-api-docs/tree/main/docs
- **Discussions**: https://github.com/thepingdoctor/scrape-api-docs/discussions

---

**Made with ❤️ for the developer community**
