# Poetry Packaging Guide - scrape-api-docs v0.2.0

## Package Information

**Name**: `scrape-api-docs`
**Version**: `0.2.0` (updated from 0.1.0)
**Description**: A Python tool to scrape documentation from websites and GitHub repositories
**License**: MIT
**Python**: >=3.9,<3.9.7 || >3.9.7,<4.0

## What's New in v0.2.0

### GitHub Repository Scraping
- Added `src/scrape_api_docs/github_scraper.py` module
- Scrape documentation directly from GitHub repositories
- Support for multiple GitHub URL formats
- Rate limiting with optional authentication
- Auto-detection in Streamlit UI

## Installation

### From PyPI (when published)
```bash
pip install scrape-api-docs
```

### From Source (Development)
```bash
# Clone the repository
git clone https://github.com/thepingdoctor/scrape-api-docs.git
cd scrape-api-docs

# Install with Poetry
poetry install

# Or install with pip
pip install -e .
```

### With Optional Dependencies

#### PDF Export Support
```bash
poetry install -E pdf
# or
pip install scrape-api-docs[pdf]
```

#### EPUB Export Support
```bash
poetry install -E epub
# or
pip install scrape-api-docs[epub]
```

#### All Export Formats
```bash
poetry install -E all-formats
# or
pip install scrape-api-docs[all-formats]
```

## Package Structure

```
scrape-api-docs/
├── src/
│   └── scrape_api_docs/
│       ├── __init__.py              # Package exports
│       ├── __main__.py              # CLI entry point
│       ├── scraper.py               # Web scraper
│       ├── github_scraper.py        # GitHub scraper (NEW)
│       ├── streamlit_app.py         # Streamlit UI
│       ├── config.py                # Configuration
│       ├── logging_config.py        # Logging setup
│       ├── security.py              # Security validation
│       ├── robots.py                # robots.txt handling
│       ├── rate_limiter.py          # Rate limiting
│       ├── user_agents.py           # User agent management
│       ├── async_scraper.py         # Async scraping
│       ├── js_renderer.py           # JavaScript rendering
│       ├── hybrid_renderer.py       # Hybrid rendering
│       ├── spa_detector.py          # SPA detection
│       ├── playwright_pool.py       # Browser pool
│       ├── exceptions.py            # Custom exceptions
│       ├── api/                     # FastAPI endpoints
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── routers/
│       │   ├── services/
│       │   └── models/
│       └── exporters/               # Export formats
│           ├── __init__.py
│           ├── base.py
│           ├── orchestrator.py
│           ├── json_exporter.py
│           ├── html_exporter.py
│           ├── pdf_exporter.py
│           └── epub_exporter.py
├── tests/                           # Test suite
│   ├── unit/
│   │   ├── test_scraper.py
│   │   ├── test_github_scraper.py   # NEW
│   │   └── ...
│   ├── integration/
│   └── e2e/
├── docs/                            # Documentation
│   ├── github-api-research.md       # NEW
│   ├── github-integration-plan.md   # NEW
│   ├── github-scraper-implementation.md  # NEW
│   ├── github-scraping-guide.md     # NEW
│   ├── IMPLEMENTATION_SUMMARY.md    # NEW
│   └── PACKAGING.md                 # NEW (this file)
├── examples/                        # Usage examples
│   └── github_scraper_example.py    # NEW
├── pyproject.toml                   # Poetry configuration
├── poetry.lock                      # Dependency lock file
├── README.md                        # Project README
├── CHANGELOG.md                     # Version history (NEW)
└── LICENSE                          # MIT License
```

## Dependencies

### Core Dependencies (Required)
- `requests ^2.31.0` - HTTP library for web and API requests
- `beautifulsoup4 ^4.12.0` - HTML parsing
- `markdownify ^0.11.0` - HTML to Markdown conversion
- `pyyaml ^6.0.1` - Configuration file parsing
- `streamlit ^1.28.0` - Web UI framework
- `pandas ^2.0.0` - Data manipulation for UI
- `jinja2 ^3.1.0` - Template engine for exports
- `markdown ^3.5.0` - Markdown processing
- `aiohttp ^3.9.0` - Async HTTP client
- `playwright ^1.40.0` - JavaScript rendering

### Optional Dependencies
- `weasyprint ^60.0` - PDF generation (extra: pdf)
- `ebooklib ^0.18` - EPUB generation (extra: epub)

### Development Dependencies
- `pytest ^7.4.0` - Testing framework
- `pytest-asyncio ^0.21.0` - Async testing support
- `black ^23.7.0` - Code formatting
- `flake8 ^6.1.0` - Code linting
- `mypy ^1.5.0` - Type checking

## CLI Commands

Poetry automatically creates these commands:

### Scrape Documentation (CLI)
```bash
poetry run scrape-docs <url>
# or
scrape-docs <url>  # if installed globally
```

### Launch Streamlit UI
```bash
poetry run scrape-docs-ui
# or
streamlit run src/scrape_api_docs/streamlit_app.py
```

## Building the Package

### Build Distribution
```bash
poetry build
```

This creates:
- `dist/scrape-api-docs-0.2.0.tar.gz` - Source distribution
- `dist/scrape-api-docs-0.2.0-py3-none-any.whl` - Wheel distribution

### Publish to PyPI (Maintainers Only)
```bash
# Test PyPI
poetry publish --build -r testpypi

# Production PyPI
poetry publish --build
```

## Development Workflow

### Install for Development
```bash
poetry install
```

### Run Tests
```bash
poetry run pytest
poetry run pytest tests/unit/test_github_scraper.py -v
```

### Format Code
```bash
poetry run black src/ tests/
```

### Lint Code
```bash
poetry run flake8 src/ tests/
```

### Type Check
```bash
poetry run mypy src/
```

### Update Dependencies
```bash
poetry update
```

### Add New Dependency
```bash
poetry add <package-name>

# Add as development dependency
poetry add --group dev <package-name>

# Add as optional dependency
poetry add --optional <package-name>
```

## Python API Usage

### Web Scraping
```python
from scrape_api_docs import scrape_site

output_path = scrape_site(
    base_url='https://example.com/docs/',
    max_pages=100,
    output_dir='output'
)
```

### GitHub Scraping (NEW)
```python
from scrape_api_docs import scrape_github_repo

output_path = scrape_github_repo(
    url='https://github.com/owner/repo/tree/main/docs',
    output_dir='output',
    max_files=100
)
```

### URL Detection (NEW)
```python
from scrape_api_docs import is_github_url, parse_github_url

# Check if URL is a GitHub repository
if is_github_url(url):
    info = parse_github_url(url)
    print(f"Owner: {info['owner']}")
    print(f"Repo: {info['repo']}")
    print(f"Branch: {info['branch']}")
    print(f"Path: {info['path']}")
```

### Export to Multiple Formats
```python
from scrape_api_docs.exporters import ExportOrchestrator
from scrape_api_docs.exporters.base import ExportOptions
from pathlib import Path

orchestrator = ExportOrchestrator()

options = ExportOptions(
    title="My Documentation",
    source_url="https://example.com",
    include_metadata=True,
    include_toc=True
)

results = await orchestrator.generate_exports(
    pages=page_results,
    base_url=base_url,
    formats=['pdf', 'epub', 'html', 'json'],
    output_dir=Path('output'),
    options={'pdf': options, 'epub': options}
)
```

## Package Metadata

### PyPI Classifiers
```python
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Documentation",
    "Topic :: Internet :: WWW/HTTP",
    "Topic :: Software Development :: Documentation",
]
```

### Keywords
```
documentation, scraper, markdown, crawler, web-scraping,
github, github-scraper, api-docs, repository-docs
```

## Version History

### v0.2.0 (2025-01-14)
- Added GitHub repository scraping
- Auto-detection of GitHub URLs in UI
- Support for folder-specific scraping
- Rate limiting with optional authentication
- Comprehensive documentation and tests

### v0.1.0
- Initial release
- Web scraping with async architecture
- FastAPI REST API
- JavaScript rendering
- Multiple export formats
- Streamlit UI

## Troubleshooting

### Poetry Not Found
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -
```

### Lock File Out of Sync
```bash
poetry lock --no-update
```

### Dependency Conflicts
```bash
poetry update
```

### Clean Install
```bash
poetry env remove python
poetry install
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Install development dependencies: `poetry install`
4. Make changes and add tests
5. Run tests: `poetry run pytest`
6. Format code: `poetry run black src/ tests/`
7. Lint code: `poetry run flake8 src/ tests/`
8. Submit pull request

## License

MIT License - see LICENSE file for details

---

**Package Maintained With**: Poetry 1.x
**Python Compatibility**: 3.9, 3.10, 3.11, 3.12
**Current Version**: 0.2.0
**Status**: Production Ready
