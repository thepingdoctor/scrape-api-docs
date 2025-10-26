"""
Async HTTP client with rate limiting and caching for static content.

This module provides high-performance async HTTP fetching with built-in
rate limiting, caching, and retry logic.
"""

import asyncio
import logging
import time
from typing import Optional, Dict
from collections import defaultdict
from dataclasses import dataclass

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class HTTPResponse:
    """HTTP response with metadata."""
    url: str
    html: str
    status_code: int
    fetch_time: float
    from_cache: bool = False
    error: Optional[str] = None


class AsyncRateLimiter:
    """
    Token bucket rate limiter for async operations.

    Limits requests per domain to avoid overwhelming servers.
    """

    def __init__(
        self,
        requests_per_second: float = 5.0,
        burst_size: int = 10,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Average requests per second per domain
            burst_size: Maximum burst size
        """
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.tokens: Dict[str, float] = defaultdict(lambda: burst_size)
        self.last_update: Dict[str, float] = defaultdict(time.time)
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def acquire(self, domain: str):
        """
        Acquire token for domain.

        Args:
            domain: Domain to rate limit
        """
        async with self._locks[domain]:
            now = time.time()
            elapsed = now - self.last_update[domain]

            # Refill tokens based on elapsed time
            self.tokens[domain] = min(
                self.burst_size,
                self.tokens[domain] + elapsed * self.requests_per_second
            )
            self.last_update[domain] = now

            # Wait if no tokens available
            if self.tokens[domain] < 1.0:
                wait_time = (1.0 - self.tokens[domain]) / self.requests_per_second
                logger.debug(f"Rate limiting {domain}: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.tokens[domain] = 0.0
            else:
                self.tokens[domain] -= 1.0


class SimpleCache:
    """
    Simple in-memory cache with TTL support.

    Caches HTTP responses to reduce redundant requests.
    """

    def __init__(self, ttl: int = 3600):
        """
        Initialize cache.

        Args:
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        self.ttl = ttl
        self._cache: Dict[str, tuple] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[str]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/missing
        """
        async with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl:
                    logger.debug(f"Cache hit: {key}")
                    return value
                else:
                    # Expired
                    del self._cache[key]
                    logger.debug(f"Cache expired: {key}")
        return None

    async def set(self, key: str, value: str):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        async with self._lock:
            self._cache[key] = (value, time.time())
            logger.debug(f"Cache set: {key}")

    async def clear(self):
        """Clear entire cache."""
        async with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    def size(self) -> int:
        """Get number of cached items."""
        return len(self._cache)


class AsyncHTTPClient:
    """
    Async HTTP client with rate limiting, caching, and retry logic.

    Features:
    - Async HTTP requests with aiohttp
    - Per-domain rate limiting
    - Response caching with TTL
    - Automatic retries with exponential backoff
    - Custom headers and user agent
    """

    def __init__(
        self,
        rate_limiter: Optional[AsyncRateLimiter] = None,
        cache: Optional[SimpleCache] = None,
        timeout: int = 30,
        max_retries: int = 3,
        user_agent: str = 'Mozilla/5.0 (compatible; DocScraper/2.0)',
    ):
        """
        Initialize async HTTP client.

        Args:
            rate_limiter: Rate limiter instance (creates default if None)
            cache: Cache instance (creates default if None)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            user_agent: User agent string
        """
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp is not installed. Install with: pip install aiohttp")

        self.rate_limiter = rate_limiter or AsyncRateLimiter()
        self.cache = cache or SimpleCache()
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent

        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Create session on context entry."""
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': self.user_agent},
            timeout=aiohttp.ClientTimeout(total=self.timeout),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close session on context exit."""
        if self.session:
            await self.session.close()

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL for rate limiting."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc

    async def fetch(
        self,
        url: str,
        use_cache: bool = True,
        bypass_rate_limit: bool = False,
    ) -> HTTPResponse:
        """
        Fetch URL with rate limiting, caching, and retries.

        Args:
            url: URL to fetch
            use_cache: Use cached response if available
            bypass_rate_limit: Skip rate limiting (use carefully)

        Returns:
            HTTPResponse with content and metadata
        """
        start_time = time.time()

        # Check cache
        if use_cache:
            cached = await self.cache.get(url)
            if cached:
                fetch_time = time.time() - start_time
                return HTTPResponse(
                    url=url,
                    html=cached,
                    status_code=200,
                    fetch_time=fetch_time,
                    from_cache=True,
                )

        # Rate limiting
        if not bypass_rate_limit:
            domain = self._extract_domain(url)
            await self.rate_limiter.acquire(domain)

        # Fetch with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                html, status_code = await self._fetch_url(url)
                fetch_time = time.time() - start_time

                # Cache successful response
                if use_cache and status_code == 200:
                    await self.cache.set(url, html)

                return HTTPResponse(
                    url=url,
                    html=html,
                    status_code=status_code,
                    fetch_time=fetch_time,
                )

            except asyncio.TimeoutError:
                last_error = "Request timeout"
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{self.max_retries})")

            except aiohttp.ClientError as e:
                last_error = str(e)
                logger.warning(f"HTTP error fetching {url}: {e} (attempt {attempt + 1}/{self.max_retries})")

            except Exception as e:
                last_error = str(e)
                logger.error(f"Error fetching {url}: {e}")

            # Exponential backoff before retry
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)

        # All retries failed
        fetch_time = time.time() - start_time
        return HTTPResponse(
            url=url,
            html='',
            status_code=0,
            fetch_time=fetch_time,
            error=last_error,
        )

    async def _fetch_url(self, url: str) -> tuple:
        """
        Fetch URL using aiohttp.

        Args:
            url: URL to fetch

        Returns:
            Tuple of (html_content, status_code)
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        async with self.session.get(url) as response:
            html = await response.text()
            return html, response.status

    async def fetch_many(
        self,
        urls: list,
        max_concurrent: int = 10,
        use_cache: bool = True,
    ) -> list:
        """
        Fetch multiple URLs concurrently.

        Args:
            urls: List of URLs to fetch
            max_concurrent: Maximum concurrent requests
            use_cache: Use cached responses

        Returns:
            List of HTTPResponse objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(url):
            async with semaphore:
                return await self.fetch(url, use_cache=use_cache)

        tasks = [fetch_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)


# Convenience function for one-off requests
async def fetch_url(url: str, timeout: int = 30) -> str:
    """
    Fetch a single URL (convenience function).

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        HTML content
    """
    async with AsyncHTTPClient(timeout=timeout) as client:
        response = await client.fetch(url)
        if response.error:
            raise Exception(f"Failed to fetch {url}: {response.error}")
        return response.html
