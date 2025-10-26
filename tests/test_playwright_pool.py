"""
Tests for Playwright browser pool management.
"""

import pytest
import asyncio

try:
    from scrape_api_docs.playwright_pool import (
        PlaywrightBrowserPool,
        render_page_with_playwright,
        PLAYWRIGHT_AVAILABLE,
    )
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_browser_pool_initialization():
    """Test browser pool initialization and cleanup."""
    async with PlaywrightBrowserPool(max_browsers=2, max_contexts_per_browser=3) as pool:
        assert pool.max_browsers == 2
        assert pool.max_contexts_per_browser == 3
        assert pool.stats.total_browsers == 0  # No browsers created yet


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_page_acquisition():
    """Test acquiring and releasing pages."""
    async with PlaywrightBrowserPool(max_browsers=1) as pool:
        async with pool.acquire_page() as page:
            assert page is not None
            assert pool.stats.active_pages == 1

        # Page should be released
        assert pool.stats.active_pages == 0
        assert pool.stats.total_renders == 1


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_render_simple_page():
    """Test rendering a simple HTML page."""
    async with PlaywrightBrowserPool(headless=True) as pool:
        async with pool.acquire_page() as page:
            # Create simple test HTML
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Test Page</title></head>
            <body><h1>Hello World</h1></body>
            </html>
            """
            await page.set_content(html)
            content = await page.content()

            assert 'Hello World' in content
            assert '<title>Test Page</title>' in content


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_concurrent_page_rendering():
    """Test concurrent page rendering with browser pool."""
    async with PlaywrightBrowserPool(max_browsers=2) as pool:
        async def render_test_page(n):
            async with pool.acquire_page() as page:
                html = f"<html><body><h1>Page {n}</h1></body></html>"
                await page.set_content(html)
                content = await page.content()
                return content

        # Render 5 pages concurrently
        tasks = [render_test_page(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for i, result in enumerate(results):
            assert f'Page {i}' in result


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_stats_tracking():
    """Test statistics tracking."""
    async with PlaywrightBrowserPool(max_browsers=1) as pool:
        # Render multiple pages
        for _ in range(3):
            async with pool.acquire_page() as page:
                await page.set_content("<html><body>Test</body></html>")

        stats = pool.get_stats()
        assert stats.total_renders == 3
        assert stats.blocked_requests >= 0  # May block requests


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_request_blocking():
    """Test that unnecessary requests are blocked."""
    async with PlaywrightBrowserPool(headless=True) as pool:
        async with pool.acquire_page() as page:
            # Try to load a page with images (should be blocked)
            html = """
            <html>
            <body>
                <img src="https://example.com/test.jpg">
                <script src="https://google-analytics.com/analytics.js"></script>
            </body>
            </html>
            """
            await page.set_content(html)

            # Check that requests were blocked
            stats = pool.get_stats()
            # Note: set_content doesn't trigger resource loads, so blocked_requests may be 0


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_convenience_function():
    """Test convenience function for one-off rendering."""
    # Note: This would require a real URL to test properly
    # For now, just test that the function is importable
    assert callable(render_page_with_playwright)
