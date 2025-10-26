"""
Playwright browser pool management for concurrent JavaScript rendering.

This module provides efficient browser instance pooling and context management
for scraping JavaScript-heavy documentation sites.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from dataclasses import dataclass

try:
    from playwright.async_api import (
        async_playwright,
        Browser,
        BrowserContext,
        Page,
        Playwright,
        Route,
    )
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    # Provide stub types for graceful degradation
    Browser = None
    BrowserContext = None
    Page = None
    Playwright = None
    Route = None


logger = logging.getLogger(__name__)


# Domains to block for performance optimization
BLOCKED_DOMAINS = [
    'google-analytics.com',
    'googletagmanager.com',
    'facebook.com',
    'doubleclick.net',
    'googlesyndication.com',
    'analytics',
    'tracking',
    'advertisement',
    'adserver',
    'ads.',
]

# Resource types to always block
BLOCKED_RESOURCE_TYPES = [
    'image',
    'font',
    'media',
    'stylesheet',  # Block CSS for faster loading (we only need content)
]


@dataclass
class BrowserPoolStats:
    """Statistics for browser pool monitoring."""
    total_browsers: int = 0
    total_contexts: int = 0
    active_pages: int = 0
    total_renders: int = 0
    blocked_requests: int = 0


class PlaywrightBrowserPool:
    """
    Manages Playwright browser instances and contexts for concurrent rendering.

    Features:
    - Browser instance pooling (max configurable browsers)
    - Context reuse for performance
    - Resource cleanup and lifecycle management
    - Concurrent page handling with semaphore
    - Request interception for performance optimization

    Example:
        async with PlaywrightBrowserPool(max_browsers=3) as pool:
            async with pool.acquire_page() as page:
                await page.goto('https://example.com')
                html = await page.content()
    """

    def __init__(
        self,
        max_browsers: int = 3,
        max_contexts_per_browser: int = 5,
        headless: bool = True,
        browser_type: str = 'chromium',
        timeout: int = 30000,
    ):
        """
        Initialize browser pool.

        Args:
            max_browsers: Maximum number of browser instances
            max_contexts_per_browser: Maximum contexts per browser
            headless: Run browsers in headless mode
            browser_type: Browser type ('chromium', 'firefox', 'webkit')
            timeout: Default timeout for operations (milliseconds)
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright is not installed. Install with: "
                "pip install playwright && playwright install chromium"
            )

        self.max_browsers = max_browsers
        self.max_contexts_per_browser = max_contexts_per_browser
        self.headless = headless
        self.browser_type = browser_type
        self.timeout = timeout

        self.playwright: Optional[Playwright] = None
        self.browsers: List[Browser] = []
        self.contexts: Dict[Browser, List[BrowserContext]] = {}
        self.stats = BrowserPoolStats()

        # Semaphore to limit concurrent pages
        max_concurrent_pages = max_browsers * max_contexts_per_browser
        self.semaphore = asyncio.Semaphore(max_concurrent_pages)

        # Lock for thread-safe browser/context creation
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        """Start Playwright on pool entry."""
        self.playwright = await async_playwright().start()
        logger.info(
            f"Playwright browser pool initialized: "
            f"{self.max_browsers} browsers, {self.max_contexts_per_browser} contexts each"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup all resources on pool exit."""
        await self.cleanup()

    async def cleanup(self):
        """Cleanup all browsers and contexts."""
        logger.info("Cleaning up browser pool...")

        # Close all contexts
        for browser, contexts in self.contexts.items():
            for context in contexts:
                try:
                    await context.close()
                except Exception as e:
                    logger.warning(f"Error closing context: {e}")

        # Close all browsers
        for browser in self.browsers:
            try:
                await browser.close()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")

        # Stop Playwright
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                logger.warning(f"Error stopping Playwright: {e}")

        logger.info(
            f"Browser pool cleaned up. "
            f"Total renders: {self.stats.total_renders}, "
            f"Blocked requests: {self.stats.blocked_requests}"
        )

    async def get_browser(self) -> Browser:
        """
        Get or create a browser instance.

        Returns:
            Browser instance (creates new if under limit, else returns least-used)
        """
        async with self._lock:
            # Create new browser if under limit
            if len(self.browsers) < self.max_browsers:
                browser = await self._create_browser()
                self.browsers.append(browser)
                self.contexts[browser] = []
                self.stats.total_browsers += 1
                return browser

            # Return least-used browser (by context count)
            return min(
                self.browsers,
                key=lambda b: len(self.contexts.get(b, []))
            )

    async def _create_browser(self) -> Browser:
        """Create a new browser instance with optimized settings."""
        # Browser launch arguments for headless scraping
        browser_args = [
            '--disable-dev-shm-usage',  # Prevent shared memory issues
            '--no-sandbox',  # Required for Docker
            '--disable-setuid-sandbox',
            '--disable-gpu',
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

        # Select browser type
        if self.browser_type == 'chromium':
            browser_launcher = self.playwright.chromium
        elif self.browser_type == 'firefox':
            browser_launcher = self.playwright.firefox
        elif self.browser_type == 'webkit':
            browser_launcher = self.playwright.webkit
        else:
            raise ValueError(f"Unknown browser type: {self.browser_type}")

        browser = await browser_launcher.launch(
            headless=self.headless,
            args=browser_args,
        )

        logger.debug(f"Created new {self.browser_type} browser instance")
        return browser

    async def get_context(self) -> BrowserContext:
        """
        Get or create a browser context.

        Returns:
            BrowserContext instance
        """
        async with self._lock:
            browser = await self.get_browser()

            # Create new context if under limit
            if len(self.contexts[browser]) < self.max_contexts_per_browser:
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (compatible; DocScraper/2.0; +https://github.com/thepingdoctor/scrape-api-docs)',
                    ignore_https_errors=True,
                    java_script_enabled=True,
                    accept_downloads=False,
                )
                self.contexts[browser].append(context)
                self.stats.total_contexts += 1
                logger.debug(f"Created new browser context (total: {self.stats.total_contexts})")
                return context

            # Reuse existing context (round-robin)
            return self.contexts[browser][0]

    @asynccontextmanager
    async def acquire_page(self, enable_request_blocking: bool = True):
        """
        Context manager for acquiring a page with automatic cleanup.

        Args:
            enable_request_blocking: Enable request interception for performance

        Yields:
            Page instance

        Example:
            async with pool.acquire_page() as page:
                await page.goto('https://example.com')
                html = await page.content()
        """
        async with self.semaphore:
            context = await self.get_context()
            page = await context.new_page()

            # Set default timeout
            page.set_default_timeout(self.timeout)

            # Enable request interception for performance
            if enable_request_blocking:
                await page.route('**/*', self._route_handler)

            self.stats.active_pages += 1

            try:
                yield page
            finally:
                try:
                    await page.close()
                except Exception as e:
                    logger.warning(f"Error closing page: {e}")
                finally:
                    self.stats.active_pages -= 1
                    self.stats.total_renders += 1

    async def _route_handler(self, route: Route):
        """
        Intercept and block unnecessary requests for performance.

        Blocks:
        - Images, fonts, media, stylesheets
        - Analytics and tracking scripts
        - Advertisements
        """
        request = route.request

        # Block resource types
        if request.resource_type in BLOCKED_RESOURCE_TYPES:
            await route.abort()
            self.stats.blocked_requests += 1
            return

        # Block analytics and ads
        if any(domain in request.url for domain in BLOCKED_DOMAINS):
            await route.abort()
            self.stats.blocked_requests += 1
            return

        # Continue with essential requests
        await route.continue_()

    def get_stats(self) -> BrowserPoolStats:
        """Get current pool statistics."""
        return self.stats


# Convenience function for one-off rendering
async def render_page_with_playwright(
    url: str,
    wait_until: str = 'networkidle',
    timeout: int = 30000,
    headless: bool = True,
) -> str:
    """
    Render a single page with Playwright (convenience function).

    Args:
        url: URL to render
        wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')
        timeout: Timeout in milliseconds
        headless: Run in headless mode

    Returns:
        Rendered HTML content

    Example:
        html = await render_page_with_playwright('https://example.com')
    """
    async with PlaywrightBrowserPool(headless=headless) as pool:
        async with pool.acquire_page() as page:
            await page.goto(url, wait_until=wait_until, timeout=timeout)
            # Small additional wait for any remaining JS
            await page.wait_for_timeout(1000)
            return await page.content()
