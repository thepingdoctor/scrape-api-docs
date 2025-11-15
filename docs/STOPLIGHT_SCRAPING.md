# Stoplight.io Documentation Scraping

## Overview

The scrape-api-docs package now supports scraping documentation from Stoplight.io hosted sites. Stoplight is a popular platform for API documentation that uses client-side rendering (React), making it challenging for traditional scrapers to access content.

## Features

✨ **Key Capabilities:**

- 🔍 **Automatic Detection**: Auto-detects Stoplight URLs and uses the appropriate scraper
- 🎭 **JavaScript Rendering**: Full Playwright integration for dynamic content
- 🔦 **Smart Page Discovery**: Intelligent navigation tree parsing to find all pages
- 📊 **API Extraction**: Automatically extracts endpoints, models, and schemas
- 📝 **Multiple Formats**: Output as Markdown or structured JSON
- ⚡ **Rate Limiting**: Built-in politeness and error recovery
- 📈 **Progress Feedback**: Real-time progress tracking during scraping

## Quick Start

### Basic Usage

```python
import asyncio
from scrape_api_docs import scrape_site_async

async def main():
    # Auto-detects Stoplight URL and scrapes
    result = await scrape_site_async(
        'https://example.stoplight.io/docs/api',
        max_pages=100,
        output_dir='./docs'
    )

    print(f"Scraped {result.pages_successful} pages")

asyncio.run(main())
```

### Stoplight-Specific Scraper

```python
import asyncio
from scrape_api_docs.stoplight_scraper import scrape_stoplight_site

async def main():
    output_path = await scrape_stoplight_site(
        url='https://example.stoplight.io/docs/api',
        output_dir='./docs',
        max_pages=100,
        output_format='markdown'  # or 'json'
    )

    print(f"Documentation saved to: {output_path}")

asyncio.run(main())
```

### Command Line

```bash
# Auto-detection (if Stoplight URL)
scrape-docs https://example.stoplight.io/docs/api

# Python API
python -m scrape_api_docs.stoplight_scraper https://example.stoplight.io/docs/api
```

## Installation Requirements

Stoplight scraping requires Playwright for JavaScript rendering:

```bash
# Install package
pip install scrape-api-docs

# Install Playwright
pip install playwright

# Install browser engines
playwright install chromium
```

## Output Formats

### Markdown Output

Generates a single consolidated Markdown file with:
- Table of contents
- API endpoints section
- Full page content
- Preserved code examples

**Example:**
```markdown
# Documentation for workspace/project

**Scraped:** 2025-11-15 19:00:00 UTC
**Total Pages:** 45

---

## Getting Started

**URL:** https://example.stoplight.io/docs/api/getting-started

### API Endpoints
- **GET** `/api/users`: Get all users
- **POST** `/api/users`: Create a new user

[... page content ...]

---
```

### JSON Output

Structured JSON optimized for LLM consumption:

```json
{
  "metadata": {
    "workspace": "example",
    "project": "api",
    "scraped_at": "2025-11-15 19:00:00 UTC",
    "total_pages": 45,
    "source": "Stoplight.io"
  },
  "pages": [
    {
      "url": "https://example.stoplight.io/docs/api/getting-started",
      "title": "Getting Started",
      "markdown": "...",
      "api_endpoints": [
        {
          "method": "GET",
          "path": "/api/users",
          "description": "Get all users"
        }
      ],
      "api_models": [
        {
          "name": "User",
          "schema": "{...}"
        }
      ],
      "code_examples": [
        {
          "language": "javascript",
          "code": "fetch('/api/users')..."
        }
      ],
      "metadata": {
        "render_time": 2.3,
        "rendered_with_js": true,
        "scraped_at": "2025-11-15 19:00:00 UTC"
      }
    }
  ]
}
```

## Architecture

### How It Works

1. **URL Detection**: Checks if URL is a Stoplight site (*.stoplight.io domain)
2. **Page Discovery**:
   - Loads base page with JavaScript rendering
   - Parses navigation sidebar/menu for links
   - Uses BFS to discover all documentation pages
3. **Content Extraction**:
   - Renders each page with Playwright
   - Extracts main content using Stoplight-specific selectors
   - Parses API endpoints, models, and code examples
4. **Output Generation**:
   - Combines pages into single document
   - Converts HTML to Markdown
   - Structures data for JSON output

### Integration with Existing Architecture

The Stoplight scraper follows the same design patterns as the GitHub scraper:

```
scrape_api_docs/
├── stoplight_scraper.py      # Main Stoplight scraper
├── github_scraper.py          # GitHub scraper (similar pattern)
├── async_scraper_wrapper.py   # Auto-detection and routing
├── hybrid_renderer.py         # JavaScript rendering
├── config.py                  # Configuration management
├── logging_config.py          # Structured logging
└── security.py                # Security validation
```

**Key Components:**

- `is_stoplight_url()`: URL detection
- `parse_stoplight_url()`: URL parsing and validation
- `discover_stoplight_pages()`: Page discovery with BFS
- `scrape_stoplight_page()`: Single page scraping
- `extract_api_elements()`: API-specific content extraction
- `scrape_stoplight_site()`: Main orchestration function

## Configuration

### Default Settings

```yaml
scraper:
  timeout: 30
  politeness_delay: 1.0
  max_pages: 100

javascript:
  enabled: true  # Required for Stoplight
  timeout: 30000  # 30 seconds
  pool_size: 3

rate_limiting:
  enabled: true
  requests_per_second: 2.0

security:
  validate_urls: true
  sanitize_filenames: true
```

### Custom Configuration

```python
from scrape_api_docs.config import Config

config = Config.load()

# Adjust for faster scraping
config.set('scraper.politeness_delay', 0.5)
config.set('rate_limiting.requests_per_second', 5.0)

# Longer timeout for slow pages
config.set('javascript.timeout', 60000)  # 60 seconds

# Use in scraping
await scrape_stoplight_site(url, config=config)
```

## Advanced Usage

### Batch Scraping

```python
async def scrape_multiple_sites():
    sites = [
        'https://api1.stoplight.io/docs/api',
        'https://api2.stoplight.io/docs/api',
        'https://api3.stoplight.io/docs/api',
    ]

    for url in sites:
        try:
            output = await scrape_stoplight_site(
                url=url,
                output_dir='./docs',
                max_pages=50
            )
            print(f"✅ {url} → {output}")
        except Exception as e:
            print(f"❌ {url} failed: {e}")
```

### Progress Tracking

```python
# Progress tracking is built-in with logging
import logging

# Enable INFO level to see progress
logging.basicConfig(level=logging.INFO)

# Scraping will show progress automatically
await scrape_stoplight_site(url)
# Output:
# INFO: Discovering pages from: https://...
# INFO: Found 45 pages to scrape
# INFO: Progress: 10/45 pages scraped
# INFO: Progress: 20/45 pages scraped
# ...
```

### Error Handling

```python
from scrape_api_docs.exceptions import (
    NetworkException,
    ValidationException,
    ScraperException
)

try:
    output = await scrape_stoplight_site(url)
except ValidationException as e:
    print(f"Invalid URL: {e}")
except NetworkException as e:
    print(f"Network error: {e}")
except ScraperException as e:
    print(f"Scraping failed: {e}")
```

## API Reference

### `scrape_stoplight_site()`

Main function to scrape a Stoplight documentation site.

**Signature:**
```python
async def scrape_stoplight_site(
    url: str,
    output_dir: str = '.',
    max_pages: int = 100,
    output_format: str = 'markdown',
    config: Optional[Config] = None
) -> str
```

**Parameters:**
- `url` (str): Stoplight documentation URL
- `output_dir` (str): Output directory for documentation file
- `max_pages` (int): Maximum number of pages to scrape
- `output_format` (str): Output format ('markdown' or 'json')
- `config` (Optional[Config]): Configuration instance

**Returns:**
- `str`: Path to the output file

**Raises:**
- `ValidationException`: If URL is invalid
- `NetworkException`: If scraping fails

### `is_stoplight_url()`

Check if a URL is a Stoplight.io documentation site.

**Signature:**
```python
def is_stoplight_url(url: str) -> bool
```

**Parameters:**
- `url` (str): URL to check

**Returns:**
- `bool`: True if URL is a Stoplight site

### `parse_stoplight_url()`

Parse Stoplight URL into components.

**Signature:**
```python
def parse_stoplight_url(url: str) -> Dict[str, str]
```

**Parameters:**
- `url` (str): Stoplight URL to parse

**Returns:**
- `Dict[str, str]`: Dictionary with keys: base_url, workspace, project, path

**Raises:**
- `ValidationException`: If URL is not a valid Stoplight URL

## Troubleshooting

### Common Issues

**1. Playwright Not Installed**
```
Error: Playwright is not installed
```
**Solution:**
```bash
pip install playwright
playwright install chromium
```

**2. Browser Installation Failed**
```
Error: Browser executable not found
```
**Solution:**
```bash
# Install specific browser
playwright install chromium

# Or install all browsers
playwright install
```

**3. JavaScript Rendering Timeout**
```
Error: Page load timeout
```
**Solution:**
```python
config = Config.load()
config.set('javascript.timeout', 60000)  # Increase to 60s
```

**4. Rate Limiting**
```
Warning: Too many requests
```
**Solution:**
```python
config = Config.load()
config.set('scraper.politeness_delay', 2.0)  # Slower scraping
config.set('rate_limiting.requests_per_second', 1.0)
```

## Performance Considerations

### Speed

- **Page Discovery**: ~2-5 seconds per page (with JS rendering)
- **Content Extraction**: ~1-3 seconds per page
- **Total Time**: ~3-8 seconds per page on average

### Optimization Tips

1. **Reduce Politeness Delay**: For faster scraping (be respectful)
   ```python
   config.set('scraper.politeness_delay', 0.5)
   ```

2. **Increase Rate Limit**: If the site allows
   ```python
   config.set('rate_limiting.requests_per_second', 5.0)
   ```

3. **Limit Max Pages**: Only scrape what you need
   ```python
   await scrape_stoplight_site(url, max_pages=20)
   ```

### Memory Usage

- **Playwright**: ~100-200 MB per browser instance
- **Content Storage**: ~10-50 MB for typical documentation
- **Peak Usage**: ~250-300 MB during scraping

## Comparison with Other Scrapers

| Feature | Generic Scraper | GitHub Scraper | **Stoplight Scraper** |
|---------|----------------|----------------|----------------------|
| JavaScript Rendering | Optional | Not needed | **Required** |
| API Extraction | No | No | **Yes** |
| Page Discovery | Link crawling | API-based | **Navigation parsing** |
| Speed | Fast | Very fast | Moderate (JS rendering) |
| Output Formats | Markdown | Markdown | **Markdown + JSON** |

## Examples

See `examples/stoplight_example.py` for comprehensive examples including:

1. Basic scraping with auto-detection
2. Progress tracking
3. Markdown output
4. Error handling
5. Batch scraping multiple sites
6. Custom configuration

## Support

For issues or questions:

- **GitHub Issues**: https://github.com/thepingdoctor/scrape-api-docs/issues
- **Documentation**: https://github.com/thepingdoctor/scrape-api-docs/tree/main/docs
- **Examples**: See `examples/stoplight_example.py`

## Limitations

1. **Requires JavaScript**: Cannot work without Playwright
2. **Slower than Static**: ~3-8 seconds per page vs ~1-2 seconds
3. **Domain Detection**: Only auto-detects *.stoplight.io domains
4. **Custom Domains**: May need manual flag for custom Stoplight domains

## Future Enhancements

Planned features:

- [ ] Custom domain detection via content analysis
- [ ] Improved API schema extraction (OpenAPI/Swagger)
- [ ] Parallel page scraping with multiple browsers
- [ ] Export to additional formats (PDF, EPUB)
- [ ] Smart caching to avoid re-scraping unchanged pages
- [ ] Integration with Stoplight API (if available)

## Contributing

Contributions are welcome! Areas for improvement:

- Better API endpoint detection
- Support for custom Stoplight domains
- Performance optimizations
- Additional output formats
- Test coverage

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.
