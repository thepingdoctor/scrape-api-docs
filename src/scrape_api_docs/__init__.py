"""Documentation scraper for converting docs websites to Markdown.

This package provides both synchronous and asynchronous scrapers:
- scrape_site(): Backward-compatible function (defaults to async for performance)
- AsyncDocumentationScraper: High-performance async scraper (5-10x faster)
- Synchronous functions: Legacy compatibility

Performance Improvement:
- Async scraper: 2.5 pages/sec (5-10x faster)
- Sync scraper: 0.5 pages/sec (legacy)

Example:
    # Simple usage (async by default)
    from scrape_api_docs import scrape_site
    scrape_site('https://docs.example.com')

    # Advanced async usage
    from scrape_api_docs import AsyncDocumentationScraper
    import asyncio

    async def main():
        scraper = AsyncDocumentationScraper(max_workers=10)
        result = await scraper.scrape_site('https://docs.example.com')
        print(f"Throughput: {result.throughput:.2f} pages/sec")

    asyncio.run(main())
"""

__version__ = "2.0.0"

from .scraper import (
    scrape_site,
    get_all_site_links,
    extract_main_content,
    convert_html_to_markdown,
    generate_filename_from_url
)

# Async components (import may fail if dependencies not installed)
try:
    from .async_scraper import AsyncDocumentationScraper, PageResult, ScrapeResult
    from .async_client import AsyncHTTPClient
    from .async_queue import AsyncWorkerPool, AsyncPriorityQueue
    from .async_rate_limiter import AsyncRateLimiter

    __all__ = [
        # Main API
        "scrape_site",
        # Async components
        "AsyncDocumentationScraper",
        "AsyncHTTPClient",
        "AsyncWorkerPool",
        "AsyncPriorityQueue",
        "AsyncRateLimiter",
        # Data classes
        "PageResult",
        "ScrapeResult",
        # Sync utilities
        "get_all_site_links",
        "extract_main_content",
        "convert_html_to_markdown",
        "generate_filename_from_url"
    ]

except ImportError as e:
    # Async dependencies not installed, provide sync-only API
    __all__ = [
        "scrape_site",
        "get_all_site_links",
        "extract_main_content",
        "convert_html_to_markdown",
        "generate_filename_from_url"
    ]
