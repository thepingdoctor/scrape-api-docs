"""
Hybrid renderer that intelligently chooses between static and JavaScript rendering.

This module provides a unified interface that automatically selects the optimal
rendering strategy based on page characteristics.
"""

import logging
import time
from typing import Optional
from dataclasses import dataclass

from .async_http import AsyncHTTPClient, HTTPResponse
from .playwright_pool import PlaywrightBrowserPool
from .js_renderer import JavaScriptRenderer, RenderResult
from .spa_detector import SPADetector

logger = logging.getLogger(__name__)


@dataclass
class HybridRenderResult:
    """Result of hybrid rendering operation."""
    url: str
    html: str
    rendered_with_javascript: bool
    render_time: float
    from_cache: bool = False
    error: Optional[str] = None
    auto_detected: bool = False
    spa_confidence: float = 0.0


class HybridRenderer:
    """
    Unified renderer that chooses optimal strategy automatically.

    Rendering strategy decision flow:
    1. If force_javascript=True: Always use Playwright
    2. Otherwise: Try static fetch first
    3. If auto_detect=True: Analyze HTML for SPA indicators
    4. If SPA detected (confidence > threshold): Switch to JavaScript rendering
    5. Otherwise: Use static HTML

    This ensures fast rendering for static sites while supporting dynamic SPAs.

    Example:
        async with HybridRenderer() as renderer:
            result = await renderer.render('https://example.com')
            print(f"Used JS: {result.rendered_with_javascript}")
            print(f"Content: {result.html[:100]}")
    """

    def __init__(
        self,
        browser_pool: Optional[PlaywrightBrowserPool] = None,
        http_client: Optional[AsyncHTTPClient] = None,
        force_javascript: bool = False,
        auto_detect: bool = True,
        spa_confidence_threshold: float = 0.5,
        enable_cache: bool = True,
    ):
        """
        Initialize hybrid renderer.

        Args:
            browser_pool: Playwright browser pool (creates default if None)
            http_client: Async HTTP client (creates default if None)
            force_javascript: Always use JavaScript rendering
            auto_detect: Automatically detect if JavaScript rendering needed
            spa_confidence_threshold: Confidence threshold for SPA detection (0-1)
            enable_cache: Enable HTTP response caching
        """
        self.force_javascript = force_javascript
        self.auto_detect = auto_detect
        self.spa_confidence_threshold = spa_confidence_threshold
        self.enable_cache = enable_cache

        # Initialize components
        self.browser_pool = browser_pool
        self.http_client = http_client
        self.spa_detector = SPADetector()

        # Track if we own the components (for cleanup)
        self._owns_browser_pool = browser_pool is None
        self._owns_http_client = http_client is None

        # Statistics
        self.stats = {
            'total_renders': 0,
            'static_renders': 0,
            'js_renders': 0,
            'auto_switches': 0,
            'cache_hits': 0,
        }

    async def __aenter__(self):
        """Initialize components on context entry."""
        # Create browser pool if not provided
        if self._owns_browser_pool:
            self.browser_pool = PlaywrightBrowserPool()
            await self.browser_pool.__aenter__()

        # Create HTTP client if not provided
        if self._owns_http_client:
            self.http_client = AsyncHTTPClient()
            await self.http_client.__aenter__()

        # Create renderers
        self.js_renderer = JavaScriptRenderer(self.browser_pool)

        logger.info(
            f"Hybrid renderer initialized: "
            f"force_js={self.force_javascript}, "
            f"auto_detect={self.auto_detect}, "
            f"threshold={self.spa_confidence_threshold}"
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup components on context exit."""
        # Close components we own
        if self._owns_http_client and self.http_client:
            await self.http_client.__aexit__(exc_type, exc_val, exc_tb)

        if self._owns_browser_pool and self.browser_pool:
            await self.browser_pool.__aexit__(exc_type, exc_val, exc_tb)

        logger.info(
            f"Hybrid renderer stats: "
            f"total={self.stats['total_renders']}, "
            f"static={self.stats['static_renders']}, "
            f"js={self.stats['js_renders']}, "
            f"auto_switches={self.stats['auto_switches']}, "
            f"cache_hits={self.stats['cache_hits']}"
        )

    async def render(
        self,
        url: str,
        force_mode: Optional[str] = None,
    ) -> HybridRenderResult:
        """
        Render page using optimal strategy.

        Args:
            url: URL to render
            force_mode: Force rendering mode ('static' or 'javascript')

        Returns:
            HybridRenderResult with content and metadata
        """
        start_time = time.time()
        self.stats['total_renders'] += 1

        # Handle forced modes
        if force_mode == 'javascript' or self.force_javascript:
            return await self._render_with_javascript(url)
        elif force_mode == 'static':
            return await self._render_static_only(url)

        # Try static first
        static_response = await self.http_client.fetch(
            url,
            use_cache=self.enable_cache,
        )

        if static_response.from_cache:
            self.stats['cache_hits'] += 1

        # Check for HTTP errors
        if static_response.error or static_response.status_code != 200:
            # Try JavaScript rendering as fallback
            logger.warning(
                f"Static fetch failed for {url} ({static_response.error}), "
                f"trying JavaScript rendering"
            )
            return await self._render_with_javascript(url)

        # Auto-detect if JavaScript rendering needed
        if self.auto_detect:
            spa_confidence = self.spa_detector.calculate_spa_confidence(
                static_response.html
            )

            needs_js = spa_confidence >= self.spa_confidence_threshold

            if needs_js:
                logger.info(
                    f"Auto-switching to JavaScript rendering for {url} "
                    f"(confidence={spa_confidence:.2f})"
                )
                self.stats['auto_switches'] += 1
                return await self._render_with_javascript(url, spa_confidence)

        # Use static rendering
        self.stats['static_renders'] += 1
        render_time = time.time() - start_time

        return HybridRenderResult(
            url=url,
            html=static_response.html,
            rendered_with_javascript=False,
            render_time=render_time,
            from_cache=static_response.from_cache,
        )

    async def _render_with_javascript(
        self,
        url: str,
        spa_confidence: float = 0.0,
    ) -> HybridRenderResult:
        """
        Render using Playwright.

        Args:
            url: URL to render
            spa_confidence: SPA detection confidence (for logging)

        Returns:
            HybridRenderResult
        """
        self.stats['js_renders'] += 1

        result = await self.js_renderer.render(url)

        return HybridRenderResult(
            url=url,
            html=result.html,
            rendered_with_javascript=True,
            render_time=result.render_time,
            error=result.error,
            auto_detected=spa_confidence > 0,
            spa_confidence=spa_confidence,
        )

    async def _render_static_only(self, url: str) -> HybridRenderResult:
        """
        Render using static HTTP only (no auto-detection).

        Args:
            url: URL to render

        Returns:
            HybridRenderResult
        """
        start_time = time.time()
        self.stats['static_renders'] += 1

        response = await self.http_client.fetch(url, use_cache=self.enable_cache)
        render_time = time.time() - start_time

        return HybridRenderResult(
            url=url,
            html=response.html,
            rendered_with_javascript=False,
            render_time=render_time,
            from_cache=response.from_cache,
            error=response.error,
        )

    async def render_many(
        self,
        urls: list,
        max_concurrent: int = 5,
    ) -> list:
        """
        Render multiple URLs concurrently.

        Args:
            urls: List of URLs to render
            max_concurrent: Maximum concurrent renders

        Returns:
            List of HybridRenderResult objects
        """
        import asyncio

        semaphore = asyncio.Semaphore(max_concurrent)

        async def render_with_semaphore(url):
            async with semaphore:
                return await self.render(url)

        tasks = [render_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)

    def get_stats(self) -> dict:
        """Get rendering statistics."""
        return self.stats.copy()


# Convenience function
async def render_page(
    url: str,
    force_javascript: bool = False,
    auto_detect: bool = True,
) -> str:
    """
    Render a single page (convenience function).

    Args:
        url: URL to render
        force_javascript: Force JavaScript rendering
        auto_detect: Auto-detect if JavaScript needed

    Returns:
        Rendered HTML content
    """
    async with HybridRenderer(
        force_javascript=force_javascript,
        auto_detect=auto_detect,
    ) as renderer:
        result = await renderer.render(url)

        if result.error:
            raise Exception(f"Failed to render {url}: {result.error}")

        return result.html
