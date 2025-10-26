# JavaScript Rendering Architecture
## Playwright Integration for SPA and Dynamic Content

**Version:** 2.0.0
**Date:** 2025-10-26
**Status:** Design Phase

---

## Overview

Many modern documentation sites use JavaScript frameworks (React, Vue, Angular) and require browser rendering to access content. This document outlines the architecture for integrating Playwright to handle JavaScript-rendered pages.

---

## Problem Statement

### Current Limitations
- Static HTML scraper cannot access JavaScript-rendered content
- Single-page applications (SPAs) show empty or minimal HTML
- Dynamic content loaded via AJAX/fetch not captured
- Modern doc frameworks (Docusaurus, VuePress, Gatsby) unsupported

### Examples of JS-Heavy Doc Sites
- React documentation (create-react-app)
- Vue.js documentation
- Svelte documentation
- Docusaurus-based sites
- GitBook sites with dynamic loading

---

## Architecture Design

### Dual-Mode Rendering Strategy

```
Request → Detect Content Type → Choose Renderer
                │
                ├─ Static HTML → requests/aiohttp (fast)
                │
                └─ JavaScript → Playwright (slower, complete)
```

### Renderer Selection Logic
1. **Manual specification**: User explicitly sets `render_javascript: true`
2. **Auto-detection**: Analyze page HTML for SPA indicators
3. **Fallback**: Try static first, use Playwright if content insufficient

---

## Playwright Integration Architecture

### Component Structure

```
┌─────────────────────────────────────────────┐
│         Renderer Factory                    │
│  - Static Renderer (aiohttp)                │
│  - JavaScript Renderer (Playwright)         │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
   ┌────▼──────┐      ┌──────▼────────┐
   │  Static   │      │  Playwright   │
   │  Renderer │      │   Renderer    │
   └───────────┘      └───────┬───────┘
                              │
                    ┌─────────▼─────────┐
                    │  Browser Pool     │
                    │  - Context Mgmt   │
                    │  - Page Lifecycle │
                    │  - Resource Mgmt  │
                    └───────────────────┘
```

### Browser Pool Management

```python
class PlaywrightBrowserPool:
    """
    Manages Playwright browser instances and contexts.

    Features:
    - Browser instance pooling
    - Context reuse for performance
    - Resource cleanup
    - Concurrent page handling
    """

    def __init__(
        self,
        max_browsers: int = 3,
        max_contexts_per_browser: int = 5,
        headless: bool = True,
        browser_type: str = 'chromium'
    ):
        self.max_browsers = max_browsers
        self.max_contexts_per_browser = max_contexts_per_browser
        self.headless = headless
        self.browser_type = browser_type

        self.playwright: Optional[Playwright] = None
        self.browsers: List[Browser] = []
        self.contexts: Dict[Browser, List[BrowserContext]] = {}

        self.semaphore = asyncio.Semaphore(
            max_browsers * max_contexts_per_browser
        )

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup all contexts and browsers
        for browser, contexts in self.contexts.items():
            for context in contexts:
                await context.close()
        for browser in self.browsers:
            await browser.close()
        await self.playwright.stop()

    async def get_browser(self) -> Browser:
        """Get or create browser instance."""
        if len(self.browsers) < self.max_browsers:
            browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-gpu',
                ]
            )
            self.browsers.append(browser)
            self.contexts[browser] = []
            return browser

        # Return least-used browser
        return min(
            self.browsers,
            key=lambda b: len(self.contexts[b])
        )

    async def get_context(self) -> BrowserContext:
        """Get or create browser context."""
        browser = await self.get_browser()

        if len(self.contexts[browser]) < self.max_contexts_per_browser:
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (compatible; DocScraper/2.0)',
                ignore_https_errors=True,
                java_script_enabled=True
            )
            self.contexts[browser].append(context)
            return context

        # Reuse existing context (least recently used)
        return self.contexts[browser][0]

    @asynccontextmanager
    async def acquire_page(self) -> Page:
        """Context manager for acquiring a page."""
        async with self.semaphore:
            context = await self.get_context()
            page = await context.new_page()

            try:
                yield page
            finally:
                await page.close()
```

---

## JavaScript Renderer Implementation

### Core Renderer Class

```python
class JavaScriptRenderer:
    """
    Renders JavaScript-heavy pages using Playwright.

    Features:
    - Wait for network idle
    - Wait for specific selectors
    - Handle dynamic loading
    - Extract fully-rendered HTML
    """

    def __init__(
        self,
        browser_pool: PlaywrightBrowserPool,
        wait_until: str = 'networkidle',
        timeout: int = 30000,
        wait_for_selector: Optional[str] = None
    ):
        self.browser_pool = browser_pool
        self.wait_until = wait_until  # 'load', 'domcontentloaded', 'networkidle'
        self.timeout = timeout
        self.wait_for_selector = wait_for_selector

    async def render(self, url: str) -> str:
        """
        Render JavaScript page and return HTML.

        Args:
            url: URL to render

        Returns:
            Fully-rendered HTML content
        """
        async with self.browser_pool.acquire_page() as page:
            # Set up request interception for performance
            await page.route('**/*', self._route_handler)

            # Navigate to page
            await page.goto(
                url,
                wait_until=self.wait_until,
                timeout=self.timeout
            )

            # Wait for specific selector if configured
            if self.wait_for_selector:
                await page.wait_for_selector(
                    self.wait_for_selector,
                    timeout=self.timeout
                )

            # Additional wait for any remaining JS
            await page.wait_for_timeout(1000)

            # Extract rendered HTML
            html = await page.content()

            return html

    async def _route_handler(self, route: Route):
        """
        Intercept and block unnecessary resources.

        Improves performance by blocking:
        - Images (unless needed for content)
        - Fonts
        - Analytics scripts
        - Ads
        """
        request = route.request

        # Block resource types
        if request.resource_type in ['image', 'font', 'media']:
            await route.abort()
            return

        # Block analytics and ads
        blocked_domains = [
            'google-analytics.com',
            'googletagmanager.com',
            'facebook.com',
            'doubleclick.net',
            'analytics',
            'tracking'
        ]

        if any(domain in request.url for domain in blocked_domains):
            await route.abort()
            return

        # Continue with request
        await route.continue_()

    async def extract_main_content(
        self,
        url: str,
        selector: str = 'main, article, .content'
    ) -> str:
        """
        Render page and extract main content.

        Args:
            url: URL to render
            selector: CSS selector for main content

        Returns:
            Main content HTML
        """
        async with self.browser_pool.acquire_page() as page:
            await page.goto(url, wait_until=self.wait_until)

            # Try to find main content
            element = await page.query_selector(selector)

            if element:
                return await element.inner_html()

            # Fallback to full content
            return await page.content()
```

---

## Auto-Detection of JavaScript Rendering

### Detection Heuristics

```python
class RenderDetector:
    """
    Detects if page requires JavaScript rendering.

    Uses multiple heuristics to determine rendering strategy.
    """

    @staticmethod
    def needs_javascript_rendering(
        url: str,
        html: str,
        content_threshold: int = 500
    ) -> bool:
        """
        Determine if JavaScript rendering is needed.

        Checks:
        1. Known SPA frameworks in HTML
        2. Root div patterns (React, Vue)
        3. Low content-to-script ratio
        4. Meta tags indicating SPA
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Check for SPA framework indicators
        spa_indicators = [
            'data-react-root',
            'data-reactroot',
            'ng-app',
            'ng-version',
            'v-app',
            '__NUXT__',
            '__NEXT_DATA__',
            'data-gatsby',
        ]

        for indicator in spa_indicators:
            if soup.find(attrs={indicator: True}) or indicator in html:
                logger.info(f"Detected SPA indicator: {indicator}")
                return True

        # Check for minimal content with root div
        root_patterns = [
            ('div', {'id': 'root'}),
            ('div', {'id': 'app'}),
            ('div', {'id': '__next'}),
        ]

        for tag, attrs in root_patterns:
            root = soup.find(tag, attrs)
            if root:
                content = root.get_text(strip=True)
                if len(content) < content_threshold:
                    logger.info(f"Detected minimal content in root div")
                    return True

        # Check content-to-script ratio
        text_content = soup.get_text(strip=True)
        scripts = soup.find_all('script')

        if len(scripts) > 5 and len(text_content) < content_threshold:
            logger.info(f"High script-to-content ratio")
            return True

        # Check for meta tags
        meta_spa = soup.find('meta', attrs={'name': 'generator'})
        if meta_spa and meta_spa.get('content', '').lower() in [
            'docusaurus', 'vuepress', 'gatsby', 'hugo'
        ]:
            logger.info(f"Detected SPA framework in meta tag")
            return True

        return False

    @staticmethod
    async def test_rendering_requirement(
        url: str,
        static_html: str,
        playwright_pool: PlaywrightBrowserPool
    ) -> bool:
        """
        Compare static vs rendered content to determine if JS needed.

        Args:
            url: URL to test
            static_html: HTML from static fetch
            playwright_pool: Browser pool for testing

        Returns:
            True if JavaScript rendering produces significantly more content
        """
        static_text = BeautifulSoup(static_html, 'html.parser').get_text(strip=True)

        # Render with JavaScript
        renderer = JavaScriptRenderer(playwright_pool)
        js_html = await renderer.render(url)
        js_text = BeautifulSoup(js_html, 'html.parser').get_text(strip=True)

        # If JS version has >50% more content, use JavaScript rendering
        improvement = len(js_text) / len(static_text) if len(static_text) > 0 else float('inf')

        logger.info(
            f"Content improvement with JS rendering: {improvement:.2f}x"
        )

        return improvement > 1.5
```

---

## Hybrid Rendering Strategy

### Unified Renderer Interface

```python
class HybridRenderer:
    """
    Unified renderer that chooses strategy automatically.

    Supports:
    - Static HTML rendering (fast)
    - JavaScript rendering (complete)
    - Automatic detection
    - Fallback mechanisms
    """

    def __init__(
        self,
        browser_pool: PlaywrightBrowserPool,
        http_client: AsyncHTTPClient,
        force_javascript: bool = False,
        auto_detect: bool = True
    ):
        self.browser_pool = browser_pool
        self.http_client = http_client
        self.force_javascript = force_javascript
        self.auto_detect = auto_detect

        self.static_renderer = StaticRenderer(http_client)
        self.js_renderer = JavaScriptRenderer(browser_pool)
        self.detector = RenderDetector()

    async def render(self, url: str) -> RenderedPage:
        """
        Render page using optimal strategy.

        Args:
            url: URL to render

        Returns:
            RenderedPage with content and metadata
        """
        # Force JavaScript rendering if specified
        if self.force_javascript:
            return await self._render_with_javascript(url)

        # Try static first
        static_html = await self.static_renderer.render(url)

        # Auto-detect if needed
        if self.auto_detect:
            needs_js = self.detector.needs_javascript_rendering(
                url,
                static_html
            )

            if needs_js:
                logger.info(f"Auto-switching to JavaScript rendering for {url}")
                return await self._render_with_javascript(url)

        # Use static rendering
        return RenderedPage(
            url=url,
            html=static_html,
            rendered_with_javascript=False,
            render_time=0.0
        )

    async def _render_with_javascript(self, url: str) -> RenderedPage:
        """Render using Playwright."""
        start_time = time.time()

        html = await self.js_renderer.render(url)

        render_time = time.time() - start_time

        return RenderedPage(
            url=url,
            html=html,
            rendered_with_javascript=True,
            render_time=render_time
        )
```

---

## Performance Optimization

### Resource Blocking
Block unnecessary resources to improve performance:

```python
async def optimized_route_handler(route: Route):
    """Optimized request handler for documentation scraping."""
    request = route.request

    # Always block
    always_block = ['image', 'font', 'media', 'stylesheet']
    if request.resource_type in always_block:
        await route.abort()
        return

    # Block tracking
    if any(domain in request.url for domain in BLOCKED_DOMAINS):
        await route.abort()
        return

    # Continue with essential requests
    await route.continue_()

# Expected performance improvement: 50-70% faster page loads
```

### Concurrent Browser Contexts
Use multiple browser contexts for parallelism:

```python
async def render_multiple_pages(
    urls: List[str],
    browser_pool: PlaywrightBrowserPool
) -> List[str]:
    """Render multiple pages concurrently."""
    tasks = [
        render_page_async(url, browser_pool)
        for url in urls
    ]

    return await asyncio.gather(*tasks)
```

### Browser Configuration
Optimize browser settings for headless scraping:

```python
browser_args = [
    '--disable-dev-shm-usage',      # Prevent shared memory issues
    '--no-sandbox',                  # Required for Docker
    '--disable-setuid-sandbox',
    '--disable-gpu',                 # No GPU in headless
    '--disable-software-rasterizer',
    '--disable-extensions',
    '--disable-sync',
    '--disable-translate',
    '--disable-background-networking',
    '--disable-background-timer-throttling',
    '--disable-backgrounding-occluded-windows',
    '--disable-breakpad',
    '--disable-client-side-phishing-detection',
    '--disable-component-extensions-with-background-pages',
    '--disable-default-apps',
    '--disable-hang-monitor',
    '--disable-ipc-flooding-protection',
    '--disable-popup-blocking',
    '--disable-prompt-on-repost',
    '--metrics-recording-only',
    '--no-first-run',
    '--no-default-browser-check',
    '--password-store=basic',
    '--use-mock-keychain',
]
```

---

## Integration with Existing Components

### Rate Limiting Integration
```python
async def render_with_rate_limiting(
    url: str,
    renderer: HybridRenderer,
    rate_limiter: AsyncRateLimiter
):
    """Render page with rate limiting."""
    await rate_limiter.acquire(url)
    return await renderer.render(url)
```

### Cache Integration
```python
async def render_with_caching(
    url: str,
    renderer: HybridRenderer,
    cache_manager: CacheManager
):
    """Render page with caching."""
    cached = cache_manager.get(url)
    if cached:
        return cached

    result = await renderer.render(url)
    cache_manager.set(url, result.html)
    return result
```

---

## Error Handling & Resilience

### Retry Logic
```python
async def render_with_retry(
    url: str,
    renderer: JavaScriptRenderer,
    max_retries: int = 3
) -> str:
    """Render with retry on failure."""
    for attempt in range(max_retries):
        try:
            return await renderer.render(url)
        except PlaywrightTimeoutError:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Retry {attempt + 1}/{max_retries} for {url}")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Fallback to Static
```python
async def render_with_fallback(
    url: str,
    hybrid_renderer: HybridRenderer
):
    """Render with fallback to static if JS fails."""
    try:
        return await hybrid_renderer.render(url)
    except Exception as e:
        logger.error(f"JavaScript rendering failed: {e}")
        logger.info("Falling back to static rendering")
        return await hybrid_renderer.static_renderer.render(url)
```

---

## Deployment Considerations

### Docker Configuration
```dockerfile
# Install Playwright browsers in Docker
FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browsers already installed in base image
# Or install specific browser:
# RUN playwright install chromium

COPY . .

CMD ["python", "-m", "uvicorn", "app.main:app"]
```

### Resource Limits
```yaml
# Kubernetes resource limits for browser pods
resources:
  limits:
    memory: "2Gi"    # Browsers are memory-intensive
    cpu: "1000m"
  requests:
    memory: "1Gi"
    cpu: "500m"
```

---

## Performance Benchmarks

### Expected Performance
| Metric | Static Rendering | JS Rendering | Ratio |
|--------|------------------|--------------|-------|
| Time per page | 1-2s | 3-8s | 3-4x slower |
| Memory usage | 50MB | 200-300MB | 4-6x more |
| CPU usage | 5-10% | 30-50% | 5x more |
| Throughput | 30-60 pages/min | 10-20 pages/min | 3x slower |

### Optimization Targets
- Reduce JS render time to <5s per page
- Reuse browser contexts for 80%+ of requests
- Block 60-70% of unnecessary requests
- Achieve 15-25 pages/min throughput for JS rendering

---

## Testing Strategy

### Unit Tests
```python
@pytest.mark.asyncio
async def test_javascript_rendering():
    async with PlaywrightBrowserPool() as pool:
        renderer = JavaScriptRenderer(pool)
        html = await renderer.render("https://react-app.example.com")
        assert len(html) > 1000
        assert "react" in html.lower()
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_hybrid_renderer_auto_detection():
    renderer = HybridRenderer(pool, client, auto_detect=True)

    # Static site
    result1 = await renderer.render("https://static.example.com")
    assert not result1.rendered_with_javascript

    # SPA site
    result2 = await renderer.render("https://spa.example.com")
    assert result2.rendered_with_javascript
```

---

## Next Steps

1. Install and configure Playwright
2. Implement PlaywrightBrowserPool
3. Create JavaScriptRenderer class
4. Build auto-detection logic
5. Integrate with HybridRenderer
6. Add comprehensive error handling
7. Optimize performance (resource blocking, context reuse)
8. Write tests for JS rendering
9. Benchmark performance vs static rendering
10. Document usage and configuration
