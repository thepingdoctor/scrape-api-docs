"""
Tests for Async Scraper Components
===================================

Comprehensive test suite for async scraper with pytest-asyncio.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from scrape_api_docs.async_client import AsyncHTTPClient
from scrape_api_docs.async_queue import AsyncWorkerPool, AsyncPriorityQueue, Priority
from scrape_api_docs.async_rate_limiter import AsyncRateLimiter
from scrape_api_docs.async_scraper import (
    AsyncDocumentationScraper,
    AsyncPageDiscovery,
    AsyncContentProcessor,
    PageResult
)


# AsyncHTTPClient Tests
@pytest.mark.asyncio
async def test_async_http_client_basic():
    """Test basic HTTP client functionality."""
    async with AsyncHTTPClient(max_connections=10) as client:
        # Mock response
        html = await client.get('https://httpbin.org/html')
        assert html is not None
        assert len(html) > 0


@pytest.mark.asyncio
async def test_async_http_client_connection_pooling():
    """Test connection pooling works correctly."""
    async with AsyncHTTPClient(max_connections=5, max_per_host=2) as client:
        # Make multiple concurrent requests
        urls = [
            'https://httpbin.org/delay/1',
            'https://httpbin.org/delay/1',
            'https://httpbin.org/delay/1',
        ]

        tasks = [client.get(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        assert all(not isinstance(r, Exception) for r in results)

        # Check statistics
        stats = client.get_stats()
        assert stats['requests'] >= len(urls)


@pytest.mark.asyncio
async def test_async_http_client_retry_logic():
    """Test retry logic with exponential backoff."""
    async with AsyncHTTPClient(max_retries=3, backoff_factor=0.1) as client:
        # This should trigger retries (non-existent page)
        with pytest.raises(Exception):
            await client.get('https://httpbin.org/status/500')

        # Check retries were attempted
        stats = client.get_stats()
        assert stats['retries'] > 0


# AsyncWorkerPool Tests
@pytest.mark.asyncio
async def test_worker_pool_basic():
    """Test worker pool basic functionality."""
    async def test_task(n: int) -> int:
        await asyncio.sleep(0.1)
        return n * 2

    async with AsyncWorkerPool(max_workers=3) as pool:
        tasks = [pool.submit(test_task, i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert results == [i * 2 for i in range(10)]


@pytest.mark.asyncio
async def test_worker_pool_concurrency_limit():
    """Test that worker pool respects concurrency limits."""
    max_workers = 3
    active_count = 0
    max_observed = 0

    async def test_task():
        nonlocal active_count, max_observed
        active_count += 1
        max_observed = max(max_observed, active_count)
        await asyncio.sleep(0.1)
        active_count -= 1

    async with AsyncWorkerPool(max_workers=max_workers) as pool:
        tasks = [pool.submit(test_task) for _ in range(10)]
        await asyncio.gather(*tasks)

    # Should not exceed max_workers
    assert max_observed <= max_workers


@pytest.mark.asyncio
async def test_worker_pool_error_handling():
    """Test worker pool handles errors gracefully."""
    async def failing_task():
        raise ValueError("Test error")

    async with AsyncWorkerPool(max_workers=2) as pool:
        task = await pool.submit(failing_task)

        with pytest.raises(ValueError):
            await task


@pytest.mark.asyncio
async def test_worker_pool_map():
    """Test worker pool map function."""
    async def square(n: int) -> int:
        await asyncio.sleep(0.01)
        return n * n

    async with AsyncWorkerPool(max_workers=5) as pool:
        results = await pool.map(square, range(10))

        assert results == [i * i for i in range(10)]


# AsyncPriorityQueue Tests
@pytest.mark.asyncio
async def test_priority_queue_ordering():
    """Test priority queue orders items correctly."""
    queue = AsyncPriorityQueue()

    # Add items with different priorities
    await queue.put("low", Priority.LOW)
    await queue.put("high", Priority.HIGH)
    await queue.put("normal", Priority.NORMAL)
    await queue.put("critical", Priority.CRITICAL)

    # Should come out in priority order
    assert await queue.get() == "critical"
    assert await queue.get() == "high"
    assert await queue.get() == "normal"
    assert await queue.get() == "low"


# AsyncRateLimiter Tests
@pytest.mark.asyncio
async def test_async_rate_limiter():
    """Test async rate limiter throttles correctly."""
    from examples.rate_limiting.rate_limiter import RateLimiter

    rate_limiter = RateLimiter(requests_per_second=5.0)
    async_limiter = AsyncRateLimiter(rate_limiter)

    url = 'https://example.com/test'

    # Should allow first request immediately
    async with async_limiter.acquire(url) as waited:
        assert waited == 0.0


# AsyncPageDiscovery Tests
@pytest.mark.asyncio
async def test_page_discovery_basic():
    """Test basic page discovery."""
    async with AsyncHTTPClient() as client:
        discoverer = AsyncPageDiscovery(
            client=client,
            max_workers=2,
            max_depth=1
        )

        # Discover pages (use small test site)
        pages = await discoverer.discover_pages('https://httpbin.org')

        assert len(pages) > 0
        assert all(isinstance(p, str) for p in pages)


# AsyncContentProcessor Tests
@pytest.mark.asyncio
async def test_content_processor_basic():
    """Test basic content processing."""
    async with AsyncHTTPClient() as client:
        processor = AsyncContentProcessor(
            client=client,
            rate_limiter=None,
            cache_manager=None
        )

        # Process a page
        result = await processor.process_page('https://httpbin.org/html')

        assert isinstance(result, PageResult)
        assert result.success
        assert result.content is not None
        assert len(result.content) > 0


@pytest.mark.asyncio
async def test_content_processor_error_handling():
    """Test content processor handles errors."""
    async with AsyncHTTPClient() as client:
        processor = AsyncContentProcessor(client=client)

        # Process non-existent page
        result = await processor.process_page('https://httpbin.org/status/404')

        assert isinstance(result, PageResult)
        assert not result.success
        assert result.error is not None


# AsyncDocumentationScraper Tests
@pytest.mark.asyncio
async def test_async_scraper_basic():
    """Test basic async scraper functionality."""
    scraper = AsyncDocumentationScraper(
        max_workers=2,
        rate_limit=5.0
    )

    # Scrape small site
    result = await scraper.scrape_site('https://httpbin.org/html')

    assert result.pages_discovered > 0
    assert result.duration > 0
    assert result.throughput > 0
    assert 'markdown' in result.exports


@pytest.mark.asyncio
async def test_async_scraper_progress_callback():
    """Test progress callback is called."""
    progress_calls = []

    async def progress(info: dict):
        progress_calls.append(info)

    scraper = AsyncDocumentationScraper(max_workers=2)

    await scraper.scrape_site(
        'https://httpbin.org/html',
        progress_callback=progress
    )

    # Progress should have been called
    assert len(progress_calls) > 0


@pytest.mark.asyncio
async def test_async_scraper_performance():
    """Test async scraper performance improvement."""
    import time

    scraper = AsyncDocumentationScraper(max_workers=10)

    start = time.time()
    result = await scraper.scrape_site('https://httpbin.org')
    duration = time.time() - start

    # Should complete reasonably quickly
    assert duration < 60  # 1 minute max for test site

    # Throughput should be reasonable
    if result.pages_successful > 0:
        assert result.throughput > 0.1  # At least 0.1 pages/sec


# Performance Comparison Test
@pytest.mark.asyncio
async def test_async_vs_sync_performance():
    """Compare async vs sync performance (if both available)."""
    # This test would compare both implementations
    # For now, just verify async works
    scraper = AsyncDocumentationScraper(max_workers=5)
    result = await scraper.scrape_site('https://httpbin.org/html')

    assert result.throughput > 0
    assert result.pages_successful > 0


# Edge Cases
@pytest.mark.asyncio
async def test_async_scraper_empty_site():
    """Test handling of site with no content."""
    scraper = AsyncDocumentationScraper(max_workers=2)

    result = await scraper.scrape_site('https://httpbin.org/status/404')

    # Should handle gracefully
    assert result.errors > 0 or result.pages_successful == 0


@pytest.mark.asyncio
async def test_async_scraper_large_concurrency():
    """Test scraper with large concurrency."""
    scraper = AsyncDocumentationScraper(max_workers=50)

    result = await scraper.scrape_site('https://httpbin.org')

    # Should not crash
    assert result is not None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, '-v'])
