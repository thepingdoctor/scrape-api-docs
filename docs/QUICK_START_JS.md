# Quick Start: JavaScript Rendering

Get started with Phase 3 JavaScript rendering in 5 minutes.

## Installation

### 1. Install Dependencies

```bash
# Install Python dependencies
poetry install

# Or with pip
pip install -e .
```

### 2. Install Playwright Browsers

```bash
# Install Chromium (recommended)
poetry run playwright install chromium

# Or install all browsers
poetry run playwright install
```

### 3. Verify Installation

```python
# test_install.py
import asyncio
from scrape_api_docs.hybrid_renderer import render_page

async def test():
    try:
        html = await render_page('https://example.com', auto_detect=False)
        print(f"✅ Success! Fetched {len(html)} bytes")
    except Exception as e:
        print(f"❌ Error: {e}")

asyncio.run(test())
```

## Quick Examples

### Example 1: Scrape React Documentation

```python
import asyncio
from scrape_api_docs.async_scraper import scrape_documentation

async def main():
    output = await scrape_documentation(
        'https://react.dev/learn',
        auto_detect=True  # Auto-detects React SPA
    )
    print(f"Saved to: {output}")

asyncio.run(main())
```

### Example 2: Scrape Vue Documentation

```python
async def scrape_vue():
    output = await scrape_documentation(
        'https://vuejs.org/guide/',
        force_javascript=True  # Force JS rendering
    )
    print(f"Saved to: {output}")

asyncio.run(scrape_vue())
```

### Example 3: Check If Site Is SPA

```python
from scrape_api_docs.spa_detector import SPADetector
from scrape_api_docs.async_http import fetch_url
import asyncio

async def check_spa(url):
    # Fetch static HTML
    html = await fetch_url(url)
    
    # Analyze
    detector = SPADetector()
    analysis = detector.analyze_page_structure(html)
    
    print(f"URL: {url}")
    print(f"SPA Confidence: {analysis['confidence_score']:.2f}")
    print(f"Indicators: {analysis['spa_indicators']}")
    print(f"Needs JS: {analysis['confidence_score'] > 0.5}")

asyncio.run(check_spa('https://react.dev'))
```

### Example 4: Custom Rendering Configuration

```python
from scrape_api_docs.playwright_pool import PlaywrightBrowserPool
from scrape_api_docs.hybrid_renderer import HybridRenderer
import asyncio

async def custom_scrape():
    # Create custom browser pool
    async with PlaywrightBrowserPool(
        max_browsers=5,
        max_contexts_per_browser=10,
        headless=True,
        browser_type='chromium'
    ) as pool:
        # Create hybrid renderer
        async with HybridRenderer(
            browser_pool=pool,
            auto_detect=True,
            spa_confidence_threshold=0.7  # More conservative
        ) as renderer:
            # Render pages
            urls = [
                'https://react.dev/learn',
                'https://vuejs.org/guide/',
                'https://angular.io/docs'
            ]
            
            results = await renderer.render_many(urls, max_concurrent=3)
            
            for result in results:
                print(f"{result.url}: JS={result.rendered_with_javascript}, "
                      f"Time={result.render_time:.2f}s")
            
            # Get stats
            stats = renderer.get_stats()
            print(f"\nStats: {stats}")

asyncio.run(custom_scrape())
```

### Example 5: Benchmark Rendering Modes

```python
import asyncio
import time
from scrape_api_docs.hybrid_renderer import HybridRenderer

async def benchmark(url):
    # Test static rendering
    async with HybridRenderer(force_javascript=False) as renderer:
        start = time.time()
        result = await renderer.render(url, force_mode='static')
        static_time = time.time() - start
        static_size = len(result.html)
    
    # Test JavaScript rendering
    async with HybridRenderer(force_javascript=True) as renderer:
        start = time.time()
        result = await renderer.render(url)
        js_time = time.time() - start
        js_size = len(result.html)
    
    print(f"URL: {url}")
    print(f"Static: {static_time:.2f}s, {static_size:,} bytes")
    print(f"JavaScript: {js_time:.2f}s, {js_size:,} bytes")
    print(f"Speedup: {js_time/static_time:.1f}x slower")
    print(f"Content gain: {js_size/static_size:.1f}x more content")

asyncio.run(benchmark('https://react.dev/learn'))
```

## Common Use Cases

### 1. Scrape Known SPA Site

```python
# Force JavaScript for known SPA
await scrape_documentation(
    'https://nextjs.org/docs',
    force_javascript=True,
    auto_detect=False
)
```

### 2. Scrape Unknown Site (Auto-Detect)

```python
# Let hybrid renderer decide
await scrape_documentation(
    'https://unknown-docs.com',
    auto_detect=True,
    force_javascript=False
)
```

### 3. Scrape Multiple Sites Concurrently

```python
from scrape_api_docs.async_scraper import AsyncDocScraper
import asyncio

async def scrape_multiple():
    urls = [
        'https://react.dev/learn',
        'https://vuejs.org/guide/',
        'https://svelte.dev/docs'
    ]
    
    async with AsyncDocScraper(auto_detect=True, max_concurrent=3) as scraper:
        for url in urls:
            output = await scraper.scrape_site(url)
            print(f"Saved: {output}")

asyncio.run(scrape_multiple())
```

## Troubleshooting

### Error: "Playwright browsers not installed"

```bash
Solution:
poetry run playwright install chromium
```

### Error: "Timeout waiting for page"

```python
# Increase timeout
from scrape_api_docs.js_renderer import JavaScriptRenderer

renderer = JavaScriptRenderer(
    browser_pool=pool,
    timeout=60000,  # 60 seconds
    wait_until='load'  # Less strict
)
```

### Error: "Memory issues"

```python
# Reduce concurrent browsers
async with PlaywrightBrowserPool(
    max_browsers=1,
    max_contexts_per_browser=2
) as pool:
    # ...
```

## Command-Line Usage

### Using the async scraper wrapper (if available)

```bash
# Scrape with auto-detection
python -m scrape_api_docs.async_scraper_wrapper https://react.dev/learn

# Force JavaScript
python -m scrape_api_docs.async_scraper_wrapper https://react.dev/learn --force-js

# Custom output
python -m scrape_api_docs.async_scraper_wrapper https://react.dev/learn -o react_docs.md
```

## Docker Usage

### Build Image

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

WORKDIR /app
COPY . .
RUN pip install poetry && poetry install --no-dev

CMD ["python", "-m", "scrape_api_docs"]
```

### Run Container

```bash
docker build -t doc-scraper .

docker run -v $(pwd)/output:/app/output doc-scraper \
    python -c "
import asyncio
from scrape_api_docs.async_scraper import scrape_documentation
asyncio.run(scrape_documentation('https://react.dev/learn', output_file='/app/output/docs.md'))
"
```

## Performance Tips

1. **Use auto-detection** for unknown sites (saves time on static sites)
2. **Increase browser pool** for large scrapes (5 browsers, 10 contexts)
3. **Reduce timeout** for faster failures (15s instead of 30s)
4. **Disable cache** for one-time scrapes
5. **Use concurrent rendering** (5-10 pages at once)

## Next Steps

- Read full documentation: `docs/JAVASCRIPT_RENDERING.md`
- Check architecture: `docs/architecture/03-javascript-rendering.md`
- Run tests: `poetry run pytest tests/test_hybrid_renderer.py -v`
- Try example scripts in `examples/` directory

## Support

Issues: https://github.com/thepingdoctor/scrape-api-docs/issues

---

**Phase 3 Complete** - JavaScript rendering ready! 🚀
