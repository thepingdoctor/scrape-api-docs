"""
JavaScript renderer using Playwright for dynamic content.

This module provides JavaScript rendering capabilities for documentation sites
that require browser execution to display content.
"""

import asyncio
import logging
import time
from typing import Optional
from dataclasses import dataclass

from .playwright_pool import PlaywrightBrowserPool

try:
    from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = None
    PlaywrightTimeoutError = TimeoutError


logger = logging.getLogger(__name__)


@dataclass
class RenderResult:
    """Result of a JavaScript rendering operation."""
    url: str
    html: str
    rendered_with_javascript: bool
    render_time: float
    error: Optional[str] = None
    screenshot_path: Optional[str] = None


class JavaScriptRenderer:
    """
    Renders JavaScript-heavy pages using Playwright.

    Features:
    - Configurable wait strategies (networkidle, load, domcontentloaded)
    - Selector-based waiting for dynamic content
    - Request interception for performance
    - Screenshot capability for debugging
    - Retry logic with exponential backoff
    """

    def __init__(
        self,
        browser_pool: PlaywrightBrowserPool,
        wait_until: str = 'networkidle',
        timeout: int = 30000,
        wait_for_selector: Optional[str] = None,
        additional_wait: int = 1000,
    ):
        """
        Initialize JavaScript renderer.

        Args:
            browser_pool: Browser pool for page rendering
            wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')
            timeout: Timeout for operations (milliseconds)
            wait_for_selector: Optional CSS selector to wait for
            additional_wait: Additional wait after page load (milliseconds)
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright is not installed. Install with: "
                "pip install playwright && playwright install chromium"
            )

        self.browser_pool = browser_pool
        self.wait_until = wait_until
        self.timeout = timeout
        self.wait_for_selector = wait_for_selector
        self.additional_wait = additional_wait

    async def render(
        self,
        url: str,
        max_retries: int = 3,
        screenshot_on_error: bool = False,
    ) -> RenderResult:
        """
        Render JavaScript page and return HTML.

        Args:
            url: URL to render
            max_retries: Maximum retry attempts on failure
            screenshot_on_error: Take screenshot on error for debugging

        Returns:
            RenderResult with HTML content and metadata
        """
        start_time = time.time()
        last_error = None

        for attempt in range(max_retries):
            try:
                html = await self._render_page(url)
                render_time = time.time() - start_time

                return RenderResult(
                    url=url,
                    html=html,
                    rendered_with_javascript=True,
                    render_time=render_time,
                )

            except PlaywrightTimeoutError as e:
                last_error = f"Timeout: {str(e)}"
                logger.warning(
                    f"Timeout rendering {url} (attempt {attempt + 1}/{max_retries})"
                )

                if attempt < max_retries - 1:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to render {url} after {max_retries} attempts")

            except Exception as e:
                last_error = str(e)
                logger.error(f"Error rendering {url}: {e}")

                if screenshot_on_error and attempt == max_retries - 1:
                    try:
                        screenshot_path = await self._take_screenshot(url)
                        logger.info(f"Error screenshot saved to: {screenshot_path}")
                    except Exception as screenshot_error:
                        logger.warning(f"Failed to take screenshot: {screenshot_error}")

                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        # All retries failed
        render_time = time.time() - start_time
        return RenderResult(
            url=url,
            html='',
            rendered_with_javascript=True,
            render_time=render_time,
            error=last_error,
        )

    async def _render_page(self, url: str) -> str:
        """
        Render a single page with Playwright.

        Args:
            url: URL to render

        Returns:
            Rendered HTML content
        """
        async with self.browser_pool.acquire_page() as page:
            # Navigate to page
            logger.debug(f"Navigating to {url} (wait_until={self.wait_until})")
            await page.goto(
                url,
                wait_until=self.wait_until,
                timeout=self.timeout,
            )

            # Wait for specific selector if configured
            if self.wait_for_selector:
                logger.debug(f"Waiting for selector: {self.wait_for_selector}")
                await page.wait_for_selector(
                    self.wait_for_selector,
                    timeout=self.timeout,
                )

            # Additional wait for any remaining JavaScript execution
            if self.additional_wait > 0:
                await page.wait_for_timeout(self.additional_wait)

            # Extract rendered HTML
            html = await page.content()
            logger.debug(f"Successfully rendered {url} ({len(html)} bytes)")

            return html

    async def extract_main_content(
        self,
        url: str,
        selector: str = 'main, article, .content, .main-content, #content',
    ) -> str:
        """
        Render page and extract main content using CSS selector.

        Args:
            url: URL to render
            selector: CSS selector for main content

        Returns:
            Main content HTML
        """
        async with self.browser_pool.acquire_page() as page:
            await page.goto(url, wait_until=self.wait_until, timeout=self.timeout)

            # Try to find main content with multiple selectors
            for sel in selector.split(','):
                sel = sel.strip()
                element = await page.query_selector(sel)
                if element:
                    content = await element.inner_html()
                    logger.debug(f"Extracted main content from selector: {sel}")
                    return content

            # Fallback to full page content
            logger.debug("No main content selector matched, returning full page")
            return await page.content()

    async def _take_screenshot(
        self,
        url: str,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Take screenshot of page for debugging.

        Args:
            url: URL to screenshot
            output_path: Output path (auto-generated if None)

        Returns:
            Path to screenshot file
        """
        if output_path is None:
            # Generate filename from URL
            safe_url = url.replace('://', '_').replace('/', '_').replace('?', '_')[:100]
            output_path = f"debug_screenshot_{safe_url}.png"

        async with self.browser_pool.acquire_page(enable_request_blocking=False) as page:
            await page.goto(url, wait_until=self.wait_until, timeout=self.timeout)
            await page.screenshot(path=output_path, full_page=True)

        return output_path

    async def evaluate_javascript(
        self,
        url: str,
        script: str,
    ):
        """
        Render page and evaluate custom JavaScript.

        Args:
            url: URL to render
            script: JavaScript code to evaluate

        Returns:
            Result of JavaScript evaluation
        """
        async with self.browser_pool.acquire_page() as page:
            await page.goto(url, wait_until=self.wait_until, timeout=self.timeout)
            result = await page.evaluate(script)
            return result

    async def wait_for_network_idle(
        self,
        url: str,
        idle_time: int = 500,
        max_wait: int = 30000,
    ) -> str:
        """
        Render page and wait for network to be idle.

        Args:
            url: URL to render
            idle_time: Time (ms) of network inactivity to consider idle
            max_wait: Maximum time (ms) to wait

        Returns:
            Rendered HTML content
        """
        async with self.browser_pool.acquire_page() as page:
            # Navigate and wait for network idle
            await page.goto(url, wait_until='networkidle', timeout=max_wait)

            # Additional wait for specified idle time
            await page.wait_for_timeout(idle_time)

            return await page.content()


# Convenience function for one-off rendering
async def render_javascript_page(
    url: str,
    headless: bool = True,
    wait_until: str = 'networkidle',
    timeout: int = 30000,
) -> str:
    """
    Render a single JavaScript page (convenience function).

    Args:
        url: URL to render
        headless: Run browser in headless mode
        wait_until: Wait condition
        timeout: Timeout in milliseconds

    Returns:
        Rendered HTML content
    """
    async with PlaywrightBrowserPool(headless=headless) as pool:
        renderer = JavaScriptRenderer(
            browser_pool=pool,
            wait_until=wait_until,
            timeout=timeout,
        )
        result = await renderer.render(url)

        if result.error:
            raise Exception(f"Failed to render {url}: {result.error}")

        return result.html
