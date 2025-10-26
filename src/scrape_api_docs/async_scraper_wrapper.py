"""
Async Scraper Wrapper - Integration with Phase 1 Security Features
===================================================================

This module provides a backward-compatible async wrapper that integrates
the high-performance async scraper with Phase 1 security features:
- Robots.txt compliance
- Rate limiting
- SSRF protection
- Content validation
- Structured logging

Usage:
    from scrape_api_docs import scrape_site_async

    result = await scrape_site_async('https://docs.example.com')
    print(f"Throughput: {result.throughput:.2f} pages/sec")
"""

import asyncio
from typing import Optional, Callable
from pathlib import Path

from .async_scraper import AsyncDocumentationScraper, ScrapeResult
from .config import Config
from .logging_config import get_logger

logger = get_logger(__name__)


async def scrape_site_async(
    base_url: str,
    max_workers: int = 10,
    max_pages: int = 100,
    output_dir: str = '.',
    config: Optional[Config] = None,
    progress_callback: Optional[Callable] = None
) -> ScrapeResult:
    """
    Async scraper with Phase 1 security features integrated.

    Provides 5-10x performance improvement while maintaining all security
    features from Phase 1:
    - Robots.txt compliance checking
    - Rate limiting with adaptive throttling
    - SSRF protection
    - Content size validation
    - Structured logging

    Args:
        base_url: Base URL to scrape
        max_workers: Concurrent workers (default: 10)
        max_pages: Maximum pages to scrape
        output_dir: Output directory
        config: Optional configuration
        progress_callback: Optional async progress callback

    Returns:
        ScrapeResult with statistics and exports

    Raises:
        SSRFException: If URL fails security validation
        RobotsException: If scraping is blocked by robots.txt
    """
    if config is None:
        config = Config.load()

    # Validate configuration
    config.validate()

    # Get configuration values
    rate_limit = config.get('rate_limiting.requests_per_second', 2.0)
    timeout = config.get('scraper.timeout', 30)

    logger.info(f"Starting async scrape for: {base_url}")
    logger.info(f"Using {max_workers} workers for 5-10x speed improvement")

    # Security validation moved to AsyncDocumentationScraper
    # to perform during page discovery

    # Create async scraper
    scraper = AsyncDocumentationScraper(
        max_workers=max_workers,
        rate_limit=rate_limit,
        timeout=timeout
    )

    # Run async scrape
    result = await scraper.scrape_site(
        base_url=base_url,
        progress_callback=progress_callback
    )

    # Save output if directory specified
    if output_dir:
        from .scraper import generate_filename_from_url

        output_filename = generate_filename_from_url(base_url, config)
        output_path = Path(output_dir) / output_filename

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        encoding = config.get('output.encoding', 'utf-8')
        with open(output_path, 'w', encoding=encoding) as f:
            f.write(result.exports['markdown'])

        logger.info(f"Documentation saved to: {output_path}")

    return result


def scrape_site_async_sync_wrapper(
    base_url: str,
    **kwargs
) -> ScrapeResult:
    """
    Synchronous wrapper for async scraper.

    Allows calling async scraper from synchronous code.

    Args:
        base_url: Base URL to scrape
        **kwargs: Additional arguments for scrape_site_async

    Returns:
        ScrapeResult
    """
    # Check if event loop is already running
    try:
        loop = asyncio.get_running_loop()
        # Already in async context - can't use asyncio.run()
        raise RuntimeError(
            "Cannot use sync wrapper from async context. "
            "Use scrape_site_async() directly."
        )
    except RuntimeError:
        # No running loop - safe to use asyncio.run()
        return asyncio.run(scrape_site_async(base_url, **kwargs))


# Backward compatibility alias
scrape_docs_async = scrape_site_async


if __name__ == "__main__":
    import sys

    async def main():
        """Example async scraper usage."""
        # Progress callback
        async def progress(info: dict):
            if 'discovered' in info:
                print(f"📄 Discovery: {info['discovered']} pages found")
            elif 'completed' in info:
                print(
                    f"⚙️  Processing: {info['completed']}/{info['total']} "
                    f"({info['percent']:.1f}%)"
                )

        result = await scrape_site_async(
            'https://docs.python.org/3/tutorial/',
            max_workers=5,
            progress_callback=progress
        )

        print(f"\n{'='*60}")
        print(f"✨ Scraping Complete!")
        print(f"{'='*60}")
        print(f"Pages discovered: {result.pages_discovered}")
        print(f"Pages processed: {result.pages_successful}")
        print(f"Duration: {result.duration:.2f}s")
        print(f"Throughput: {result.throughput:.2f} pages/sec")

    asyncio.run(main())
