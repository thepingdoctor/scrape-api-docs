"""
Async Rate Limiter for Documentation Scraper
=============================================

Async wrapper for the existing rate limiter, enabling non-blocking
rate limiting in async contexts.

Features:
- Async/await compatible rate limiting
- Integration with existing RateLimiter
- Non-blocking token acquisition
- Per-domain limits
- Exponential backoff for 429/503

Usage:
    from async_rate_limiter import AsyncRateLimiter
    from rate_limiter import RateLimiter

    limiter = AsyncRateLimiter(RateLimiter(requests_per_second=2))

    async with limiter.acquire(url):
        html = await client.get(url)
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional
from urllib.parse import urlparse
import logging

# Import the existing rate limiter
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / 'examples' / 'rate-limiting'))

try:
    from rate_limiter import RateLimiter, TokenBucket
except ImportError:
    # If not in examples, create a minimal version
    logger = logging.getLogger(__name__)
    logger.warning("Could not import RateLimiter from examples, using minimal version")

    class TokenBucket:
        """Minimal token bucket for standalone use."""
        def __init__(self, rate: float, capacity: float):
            self.rate = rate
            self.capacity = capacity
            self.tokens = capacity
            self.last_update = time.time()

        def consume(self, tokens: int = 1) -> bool:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

        def wait_time(self, tokens: int = 1) -> float:
            if self.tokens >= tokens:
                return 0.0
            deficit = tokens - self.tokens
            return deficit / self.rate

    class RateLimiter:
        """Minimal rate limiter for standalone use."""
        def __init__(self, requests_per_second: float = 2.0, burst_size: Optional[int] = None):
            self.requests_per_second = requests_per_second
            self.burst_size = burst_size or int(requests_per_second * 2)
            self.buckets = {}
            self.backoff_until = {}

        def _get_bucket(self, domain: str):
            if domain not in self.buckets:
                self.buckets[domain] = TokenBucket(self.requests_per_second, self.burst_size)
            return self.buckets[domain]

        def _extract_domain(self, url: str) -> str:
            return urlparse(url).netloc

        def _is_backed_off(self, domain: str) -> Optional[float]:
            if domain in self.backoff_until:
                remaining = self.backoff_until[domain] - time.time()
                if remaining > 0:
                    return remaining
                del self.backoff_until[domain]
            return None


logger = logging.getLogger(__name__)


class AsyncRateLimiter:
    """
    Async wrapper for RateLimiter.

    Provides non-blocking rate limiting using async/await.
    """

    def __init__(self, rate_limiter: RateLimiter):
        """
        Initialize async rate limiter.

        Args:
            rate_limiter: Underlying RateLimiter instance
        """
        self._rate_limiter = rate_limiter
        self._lock = asyncio.Lock()

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        return urlparse(url).netloc

    @asynccontextmanager
    async def acquire(self, url: str, timeout: float = 60.0):
        """
        Async context manager for rate limiting.

        Usage:
            async with limiter.acquire(url) as waited:
                html = await client.get(url)

        Args:
            url: Target URL
            timeout: Maximum wait time in seconds

        Yields:
            Time waited in seconds

        Raises:
            TimeoutError: If wait exceeds timeout
        """
        domain = self._extract_domain(url)
        bucket = self._rate_limiter._get_bucket(domain)

        start_time = asyncio.get_event_loop().time()
        total_waited = 0.0

        # Check for backoff period
        backoff_remaining = self._rate_limiter._is_backed_off(domain)
        if backoff_remaining:
            if backoff_remaining > timeout:
                raise TimeoutError(
                    f"Backoff period ({backoff_remaining:.1f}s) "
                    f"exceeds timeout ({timeout}s)"
                )

            logger.info(
                f"Waiting {backoff_remaining:.1f}s for backoff on {domain}"
            )
            await asyncio.sleep(backoff_remaining)
            total_waited += backoff_remaining

        # Wait for token availability
        while not bucket.consume():
            wait_time = bucket.wait_time()

            # Check timeout
            if asyncio.get_event_loop().time() - start_time + wait_time > timeout:
                raise TimeoutError(
                    f"Rate limit wait time exceeds timeout ({timeout}s)"
                )

            logger.debug(
                f"Rate limited, waiting {wait_time:.2f}s for {domain}"
            )
            await asyncio.sleep(wait_time)
            total_waited += wait_time

        # Token acquired
        try:
            yield total_waited
        finally:
            # Cleanup if needed
            pass

    def record_response(self, url: str, status_code: int):
        """
        Record response for adaptive throttling.

        Args:
            url: Request URL
            status_code: HTTP status code
        """
        if hasattr(self._rate_limiter, 'record_response'):
            self._rate_limiter.record_response(url, status_code)

    def get_stats(self, domain: Optional[str] = None) -> dict:
        """
        Get rate limiting statistics.

        Args:
            domain: Optional specific domain

        Returns:
            Statistics dictionary
        """
        if hasattr(self._rate_limiter, 'get_stats'):
            return self._rate_limiter.get_stats(domain)
        return {}


# Example usage
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def main():
        """Example async rate limiter usage."""
        # Create rate limiter
        rate_limiter = RateLimiter(requests_per_second=2.0)
        async_limiter = AsyncRateLimiter(rate_limiter)

        # Simulate multiple requests
        urls = [
            'https://example.com/page1',
            'https://example.com/page2',
            'https://example.com/page3',
            'https://example.com/page4',
            'https://example.com/page5',
        ]

        async def fetch_with_limit(url: str):
            """Fetch URL with rate limiting."""
            async with async_limiter.acquire(url) as waited:
                if waited > 0:
                    print(f"Waited {waited:.2f}s for {url}")
                print(f"Fetching {url}")
                # Simulate request
                await asyncio.sleep(0.1)

        # Execute concurrently (rate limiter will throttle)
        start = time.time()
        await asyncio.gather(*[fetch_with_limit(url) for url in urls])
        duration = time.time() - start

        print(f"\nCompleted {len(urls)} requests in {duration:.2f}s")

    # Run example
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
