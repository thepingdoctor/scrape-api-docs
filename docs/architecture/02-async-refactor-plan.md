# Async/Concurrent Processing Refactor Plan
## Migration from Synchronous to Asynchronous Architecture

**Version:** 2.0.0
**Date:** 2025-10-26
**Status:** Design Phase

---

## Executive Summary

This document outlines the strategy for refactoring the Documentation Scraper from synchronous to asynchronous architecture, enabling concurrent processing, improved performance, and better resource utilization.

### Performance Goals
- **3-5x throughput improvement** through concurrent page processing
- **50-70% reduction in total scraping time** for large documentation sites
- **Better resource utilization** with non-blocking I/O
- **Scalable architecture** supporting distributed workers

---

## Current State Analysis

### Existing Synchronous Architecture

**Current Flow:**
```python
def scrape_site(base_url):
    all_pages = get_all_site_links(base_url)  # Sequential crawling
    for url in all_pages:                      # Sequential processing
        html = fetch_url(url)                  # Blocking I/O
        content = extract_content(html)        # CPU-bound
        markdown = convert_to_markdown(content) # CPU-bound
        save_to_file(markdown)                 # Blocking I/O
```

**Bottlenecks:**
1. **Sequential page discovery**: Pages discovered one at a time
2. **Blocking network I/O**: Each HTTP request waits for response
3. **No parallelization**: Single-threaded execution
4. **Resource underutilization**: CPU idle during network waits
5. **Poor scalability**: Linear time complexity O(n) with page count

### Performance Baseline (100-page site)
- **Total time**: ~200 seconds
- **Network I/O time**: ~150 seconds (75%)
- **Processing time**: ~50 seconds (25%)
- **Effective throughput**: 0.5 pages/second
- **CPU utilization**: 15-20%
- **Memory usage**: 50-100 MB

---

## Target Asynchronous Architecture

### Async Design Principles

1. **Non-blocking I/O**: Use `async/await` for all network operations
2. **Concurrent execution**: Process multiple pages simultaneously
3. **Worker pools**: Configurable concurrency limits
4. **Resource management**: Connection pooling and rate limiting
5. **Graceful degradation**: Handle failures without blocking pipeline

### New Async Flow
```python
async def scrape_site_async(base_url):
    # Concurrent page discovery
    all_pages = await discover_pages_concurrent(base_url)

    # Process pages in batches with worker pool
    async with WorkerPool(max_workers=10) as pool:
        tasks = [
            pool.submit(process_page_async, url)
            for url in all_pages
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Aggregate results
    return combine_results(results)
```

**Expected Performance (100-page site):**
- **Total time**: ~40 seconds (5x faster)
- **Network I/O time**: ~30 seconds (overlapped)
- **Processing time**: ~10 seconds (parallelized)
- **Effective throughput**: 2.5 pages/second
- **CPU utilization**: 60-80%
- **Memory usage**: 150-250 MB

---

## Migration Strategy

### Phase 1: Core Async Infrastructure (Week 1)

#### 1.1 Add Async HTTP Client
Replace `requests` with `aiohttp`:

```python
# Before (synchronous)
import requests

def fetch_url(url: str) -> str:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text

# After (asynchronous)
import aiohttp

async def fetch_url_async(
    url: str,
    session: aiohttp.ClientSession
) -> str:
    async with session.get(url, timeout=10) as response:
        response.raise_for_status()
        return await response.text()
```

#### 1.2 Async Session Management
Implement connection pooling:

```python
class AsyncHTTPClient:
    def __init__(
        self,
        max_connections: int = 100,
        timeout: int = 30
    ):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=10,
            ttl_dns_cache=300
        )
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get(self, url: str, **kwargs) -> str:
        async with self.session.get(url, **kwargs) as response:
            return await response.text()
```

#### 1.3 Async Rate Limiting Integration
Adapt existing rate limiter for async:

```python
class AsyncRateLimiter:
    def __init__(self, rate_limiter: RateLimiter):
        self._rate_limiter = rate_limiter
        self._lock = asyncio.Lock()

    async def acquire(self, url: str, timeout: float = 60.0):
        """Async context manager for rate limiting."""
        domain = self._extract_domain(url)
        bucket = self._rate_limiter._get_bucket(domain)

        start_time = asyncio.get_event_loop().time()

        # Wait for token
        while not bucket.consume():
            wait_time = bucket.wait_time()

            if asyncio.get_event_loop().time() - start_time + wait_time > timeout:
                raise TimeoutError("Rate limit timeout")

            await asyncio.sleep(wait_time)

        return AsyncRateLimitContext(self._rate_limiter, url)
```

---

### Phase 2: Async Page Discovery (Week 1-2)

#### 2.1 Concurrent Page Crawling
Implement breadth-first concurrent crawling:

```python
async def discover_pages_concurrent(
    base_url: str,
    max_depth: int = 10,
    max_workers: int = 10,
    rate_limiter: Optional[AsyncRateLimiter] = None
) -> Set[str]:
    """
    Discover all pages concurrently using BFS.

    Args:
        base_url: Starting URL
        max_depth: Maximum crawl depth
        max_workers: Concurrent worker limit
        rate_limiter: Optional rate limiter

    Returns:
        Set of discovered URLs
    """
    to_visit = asyncio.Queue()
    await to_visit.put((base_url, 0))  # (url, depth)

    visited = set()
    all_pages = set()

    base_netloc = urlparse(base_url).netloc
    base_path = urlparse(base_url).path

    async with AsyncHTTPClient() as client:
        async with AsyncWorkerPool(max_workers=max_workers) as pool:
            while not to_visit.empty() or pool.active_tasks > 0:
                try:
                    url, depth = await asyncio.wait_for(
                        to_visit.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                if url in visited or depth > max_depth:
                    continue

                visited.add(url)
                all_pages.add(url)

                # Submit crawl task
                task = pool.submit(
                    crawl_page_for_links,
                    url,
                    client,
                    rate_limiter,
                    base_netloc,
                    base_path,
                    depth,
                    to_visit
                )

    return all_pages


async def crawl_page_for_links(
    url: str,
    client: AsyncHTTPClient,
    rate_limiter: Optional[AsyncRateLimiter],
    base_netloc: str,
    base_path: str,
    depth: int,
    queue: asyncio.Queue
):
    """Crawl single page and extract links."""
    try:
        # Rate limit if configured
        if rate_limiter:
            await rate_limiter.acquire(url)

        # Fetch page
        html = await client.get(url)

        # Extract links
        soup = BeautifulSoup(html, 'html.parser')

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            absolute_link = urljoin(url, href)
            parsed = urlparse(absolute_link)
            clean_link = parsed._replace(query="", fragment="").geturl()

            # Same domain check
            if (parsed.netloc == base_netloc and
                parsed.path.startswith(base_path)):
                await queue.put((clean_link, depth + 1))

    except Exception as e:
        logger.error(f"Failed to crawl {url}: {e}")
```

#### 2.2 Async Worker Pool
Implement configurable worker pool:

```python
class AsyncWorkerPool:
    """Async worker pool with concurrency limit."""

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.tasks: Set[asyncio.Task] = set()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Wait for all tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

    async def submit(self, coro_func, *args, **kwargs):
        """Submit coroutine for execution."""
        async def _wrapped():
            async with self.semaphore:
                return await coro_func(*args, **kwargs)

        task = asyncio.create_task(_wrapped())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    @property
    def active_tasks(self) -> int:
        return len(self.tasks)
```

---

### Phase 3: Async Content Processing (Week 2)

#### 3.1 Async Page Processing Pipeline
Process pages concurrently:

```python
async def process_page_async(
    url: str,
    client: AsyncHTTPClient,
    rate_limiter: AsyncRateLimiter,
    cache_manager: CacheManager
) -> PageResult:
    """
    Process single page asynchronously.

    Returns:
        PageResult with extracted content
    """
    try:
        # Check cache
        cached = cache_manager.get(url)
        if cached:
            return PageResult.from_cache(cached)

        # Rate limit
        await rate_limiter.acquire(url)

        # Fetch page
        html = await client.get(url)

        # Extract content (CPU-bound, run in executor)
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            None,
            extract_main_content,
            html
        )

        # Convert to markdown (CPU-bound)
        markdown = await loop.run_in_executor(
            None,
            convert_html_to_markdown,
            content
        )

        # Cache result
        cache_manager.set(url, markdown)

        return PageResult(
            url=url,
            content=markdown,
            success=True
        )

    except Exception as e:
        logger.error(f"Failed to process {url}: {e}")
        return PageResult(
            url=url,
            content=None,
            success=False,
            error=str(e)
        )
```

#### 3.2 Batch Processing with Progress Tracking
Process pages in batches with progress updates:

```python
async def process_pages_in_batches(
    urls: List[str],
    batch_size: int = 20,
    max_workers: int = 10,
    progress_callback: Optional[Callable] = None
) -> List[PageResult]:
    """
    Process pages in batches with progress tracking.

    Args:
        urls: List of URLs to process
        batch_size: Pages per batch
        max_workers: Concurrent workers
        progress_callback: Optional progress callback

    Returns:
        List of page results
    """
    all_results = []
    total_pages = len(urls)

    async with AsyncHTTPClient() as client:
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]

            # Process batch concurrently
            tasks = [
                process_page_async(url, client, rate_limiter, cache)
                for url in batch
            ]

            batch_results = await asyncio.gather(
                *tasks,
                return_exceptions=True
            )

            all_results.extend(batch_results)

            # Progress callback
            if progress_callback:
                progress = {
                    'completed': len(all_results),
                    'total': total_pages,
                    'percent': (len(all_results) / total_pages) * 100
                }
                await progress_callback(progress)

    return all_results
```

---

### Phase 4: Async Integration Layer (Week 3)

#### 4.1 Unified Async Scraper Interface
Main async scraper class:

```python
class AsyncDocumentationScraper:
    """
    Async documentation scraper with concurrent processing.
    """

    def __init__(
        self,
        max_workers: int = 10,
        batch_size: int = 20,
        rate_limit: float = 2.0,
        cache_dir: str = '.cache',
        timeout: int = 30
    ):
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.rate_limiter = AsyncRateLimiter(
            RateLimiter(requests_per_second=rate_limit)
        )
        self.cache_manager = CacheManager(
            disk_cache_dir=cache_dir
        )
        self.timeout = timeout

        self.statistics = ScraperStatistics()

    async def scrape_site(
        self,
        base_url: str,
        progress_callback: Optional[Callable] = None,
        export_formats: List[str] = ['markdown']
    ) -> ScrapeResult:
        """
        Scrape entire documentation site asynchronously.

        Args:
            base_url: Starting URL
            progress_callback: Optional progress callback
            export_formats: List of export formats

        Returns:
            ScrapeResult with all outputs
        """
        start_time = time.time()

        # Phase 1: Discover pages concurrently
        logger.info(f"Discovering pages from {base_url}")
        all_pages = await discover_pages_concurrent(
            base_url,
            max_workers=self.max_workers,
            rate_limiter=self.rate_limiter
        )

        logger.info(f"Discovered {len(all_pages)} pages")
        self.statistics.pages_discovered = len(all_pages)

        # Phase 2: Process pages in batches
        logger.info("Processing pages concurrently")
        results = await process_pages_in_batches(
            list(all_pages),
            batch_size=self.batch_size,
            max_workers=self.max_workers,
            progress_callback=progress_callback
        )

        self.statistics.pages_processed = len([
            r for r in results if r.success
        ])
        self.statistics.errors = len([
            r for r in results if not r.success
        ])

        # Phase 3: Generate exports concurrently
        logger.info("Generating exports")
        exports = await self._generate_exports_async(
            results,
            base_url,
            export_formats
        )

        duration = time.time() - start_time

        return ScrapeResult(
            url=base_url,
            pages_processed=self.statistics.pages_processed,
            pages_discovered=self.statistics.pages_discovered,
            errors=self.statistics.errors,
            duration=duration,
            exports=exports,
            statistics=self.statistics.to_dict()
        )

    async def _generate_exports_async(
        self,
        results: List[PageResult],
        base_url: str,
        formats: List[str]
    ) -> Dict[str, str]:
        """Generate exports in parallel."""
        tasks = []

        for format_type in formats:
            task = asyncio.create_task(
                self._export_format_async(results, base_url, format_type)
            )
            tasks.append((format_type, task))

        exports = {}
        for format_type, task in tasks:
            try:
                exports[format_type] = await task
            except Exception as e:
                logger.error(f"Export failed for {format_type}: {e}")

        return exports
```

#### 4.2 Backward Compatibility Layer
Provide sync wrapper for backward compatibility:

```python
class DocumentationScraper:
    """Synchronous wrapper for async scraper (backward compatible)."""

    def __init__(self, **kwargs):
        self.async_scraper = AsyncDocumentationScraper(**kwargs)

    def scrape_site(
        self,
        base_url: str,
        **kwargs
    ) -> ScrapeResult:
        """Synchronous scrape method."""
        return asyncio.run(
            self.async_scraper.scrape_site(base_url, **kwargs)
        )
```

---

### Phase 5: Performance Optimization (Week 3-4)

#### 5.1 Connection Pooling Optimization
```python
# Optimize connection limits based on domain
connector = aiohttp.TCPConnector(
    limit=100,              # Total connections
    limit_per_host=10,      # Per-domain limit
    ttl_dns_cache=300,      # DNS cache TTL
    enable_cleanup_closed=True,
    force_close=False       # Reuse connections
)
```

#### 5.2 Memory Management
```python
# Process results in streaming fashion to limit memory
async def process_pages_streaming(urls: List[str]):
    async for result in stream_page_results(urls):
        await save_result_async(result)
        # Result can be garbage collected
```

#### 5.3 CPU-Bound Task Optimization
```python
# Use ProcessPoolExecutor for CPU-intensive work
from concurrent.futures import ProcessPoolExecutor

executor = ProcessPoolExecutor(max_workers=4)

async def process_cpu_intensive(data):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        heavy_processing_function,
        data
    )
```

---

## Testing Strategy

### Unit Tests for Async Components
```python
import pytest

@pytest.mark.asyncio
async def test_async_page_discovery():
    scraper = AsyncDocumentationScraper()
    pages = await scraper.discover_pages_concurrent(
        "https://example.com/docs"
    )
    assert len(pages) > 0
    assert all(isinstance(p, str) for p in pages)

@pytest.mark.asyncio
async def test_concurrent_processing():
    urls = ["https://example.com/page1", "https://example.com/page2"]
    results = await process_pages_in_batches(urls)
    assert len(results) == len(urls)
```

### Performance Benchmarks
```python
import pytest_benchmark

def test_sync_vs_async_performance(benchmark):
    """Compare sync and async performance."""

    # Sync version
    sync_time = benchmark(sync_scraper.scrape_site, test_url)

    # Async version
    async_time = benchmark(asyncio.run, async_scraper.scrape_site, test_url)

    # Assert async is faster
    assert async_time < sync_time * 0.5  # At least 2x faster
```

---

## Migration Checklist

### Week 1: Foundation
- [ ] Install async dependencies (aiohttp, asyncpg)
- [ ] Create AsyncHTTPClient with connection pooling
- [ ] Implement AsyncRateLimiter wrapper
- [ ] Create AsyncWorkerPool for concurrency control
- [ ] Write unit tests for async components

### Week 2: Core Functionality
- [ ] Implement async page discovery
- [ ] Create async content processing pipeline
- [ ] Add batch processing with progress tracking
- [ ] Integrate with existing cache manager
- [ ] Test concurrent processing performance

### Week 3: Integration
- [ ] Build unified AsyncDocumentationScraper class
- [ ] Create backward-compatible sync wrapper
- [ ] Implement async export generation
- [ ] Add comprehensive error handling
- [ ] Write integration tests

### Week 4: Optimization & Testing
- [ ] Optimize connection pooling parameters
- [ ] Add memory management for large sites
- [ ] Implement streaming results processing
- [ ] Run performance benchmarks
- [ ] Load testing with 1000+ page sites

### Week 5: Documentation & Deployment
- [ ] Update API documentation
- [ ] Create migration guide
- [ ] Update CLI to use async version
- [ ] Deploy to staging environment
- [ ] Monitor performance metrics

---

## Risk Mitigation

### Technical Risks
1. **Complexity**: Async code harder to debug
   - *Mitigation*: Comprehensive logging, structured error handling

2. **Resource exhaustion**: Too many concurrent connections
   - *Mitigation*: Configurable limits, backpressure mechanisms

3. **Event loop blocking**: CPU-bound tasks blocking async
   - *Mitigation*: Use executors for CPU-intensive work

4. **Memory usage**: Higher memory with concurrent processing
   - *Mitigation*: Streaming processing, batch size limits

### Operational Risks
1. **Backward compatibility**: Breaking existing integrations
   - *Mitigation*: Maintain sync wrapper, versioned API

2. **Deployment complexity**: More moving parts
   - *Mitigation*: Containerization, comprehensive monitoring

---

## Success Metrics

### Performance
- ✅ 3-5x throughput improvement (pages/second)
- ✅ 50-70% reduction in total scraping time
- ✅ 60-80% CPU utilization (vs 15-20% sync)
- ✅ <500ms p99 latency for page processing

### Quality
- ✅ Zero regressions in output quality
- ✅ 100% backward compatibility for sync API
- ✅ 95%+ test coverage for async components
- ✅ No memory leaks under sustained load

### Operational
- ✅ Successful deployment to production
- ✅ <1% error rate under normal load
- ✅ Graceful degradation under high load
- ✅ Clear monitoring and debugging capabilities

---

## Next Steps

1. Set up async development environment
2. Implement AsyncHTTPClient and connection pooling
3. Create async page discovery with worker pool
4. Build concurrent processing pipeline
5. Integrate with FastAPI for async API endpoints
6. Run performance benchmarks and optimize
7. Deploy to staging for validation
8. Create migration documentation
9. Release to production with monitoring
