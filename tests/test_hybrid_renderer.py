"""
Tests for hybrid renderer (static + JavaScript).
"""

import pytest

try:
    from scrape_api_docs.hybrid_renderer import HybridRenderer
    from scrape_api_docs.async_http import AsyncHTTPClient
    from scrape_api_docs.playwright_pool import PlaywrightBrowserPool, PLAYWRIGHT_AVAILABLE
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_hybrid_renderer_initialization():
    """Test hybrid renderer initialization."""
    async with HybridRenderer() as renderer:
        assert renderer is not None
        assert renderer.browser_pool is not None
        assert renderer.http_client is not None
        assert renderer.spa_detector is not None


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_static_rendering():
    """Test static rendering path."""
    # Note: Would need mock HTTP server for real test
    # For now, test that renderer is callable
    async with HybridRenderer(auto_detect=False) as renderer:
        assert callable(renderer.render)


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_force_javascript_mode():
    """Test forcing JavaScript rendering."""
    async with HybridRenderer(force_javascript=True) as renderer:
        assert renderer.force_javascript is True


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_stats_tracking():
    """Test that stats are tracked correctly."""
    async with HybridRenderer() as renderer:
        initial_stats = renderer.get_stats()
        assert initial_stats['total_renders'] == 0
        assert initial_stats['static_renders'] == 0
        assert initial_stats['js_renders'] == 0


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_auto_detection_enabled():
    """Test that auto-detection is enabled by default."""
    async with HybridRenderer() as renderer:
        assert renderer.auto_detect is True


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.asyncio
async def test_custom_components():
    """Test using custom browser pool and HTTP client."""
    async with PlaywrightBrowserPool(max_browsers=2) as pool:
        async with AsyncHTTPClient() as client:
            async with HybridRenderer(
                browser_pool=pool,
                http_client=client,
            ) as renderer:
                # Renderer should use provided components
                assert renderer.browser_pool is pool
                assert renderer.http_client is client
