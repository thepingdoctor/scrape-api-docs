"""
Rate Limiting & Request Throttling for Documentation Scraper
============================================================

This module provides advanced rate limiting capabilities to prevent
overwhelming target servers and ensure responsible scraping practices.

Features:
- Token bucket algorithm for smooth rate limiting
- Per-domain rate limiting
- Adaptive throttling based on server responses
- Exponential backoff for 429/503 errors
- Configurable limits per domain

Usage:
    from rate_limiter import RateLimiter

    limiter = RateLimiter(requests_per_second=2)

    with limiter.acquire('example.com'):
        response = requests.get(url)
"""

import time
import threading
from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Dict, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class TokenBucket:
    """
    Token bucket algorithm implementation for rate limiting.

    Allows bursts up to capacity while maintaining average rate.
    """

    def __init__(self, rate: float, capacity: float):
        """
        Initialize token bucket.

        Args:
            rate: Tokens added per second (requests per second)
            capacity: Maximum bucket size (max burst)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False otherwise
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait_time(self, tokens: int = 1) -> float:
        """
        Calculate time to wait until tokens are available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds to wait
        """
        with self.lock:
            if self.tokens >= tokens:
                return 0.0

            deficit = tokens - self.tokens
            return deficit / self.rate


class RateLimiter:
    """
    Multi-domain rate limiter with adaptive throttling.

    Features:
    - Per-domain rate limits
    - Automatic exponential backoff
    - 429/503 response handling
    - Configurable default limits
    """

    def __init__(
        self,
        requests_per_second: float = 2.0,
        burst_size: Optional[int] = None,
        max_retries: int = 3,
        backoff_factor: float = 2.0
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Default rate limit
            burst_size: Max burst (defaults to 2x rate)
            max_retries: Maximum retry attempts
            backoff_factor: Exponential backoff multiplier
        """
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size or int(requests_per_second * 2)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        # Per-domain buckets
        self.buckets: Dict[str, TokenBucket] = {}
        self.domain_stats: Dict[str, dict] = defaultdict(
            lambda: {
                'requests': 0,
                'throttled': 0,
                'errors': 0,
                'last_request': None
            }
        )

        # Adaptive throttling state
        self.backoff_until: Dict[str, float] = {}
        self.recent_errors: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10)
        )

        self.lock = threading.Lock()

    def _get_bucket(self, domain: str) -> TokenBucket:
        """Get or create token bucket for domain."""
        if domain not in self.buckets:
            with self.lock:
                if domain not in self.buckets:
                    self.buckets[domain] = TokenBucket(
                        self.requests_per_second,
                        self.burst_size
                    )
        return self.buckets[domain]

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        return urlparse(url).netloc

    def _is_backed_off(self, domain: str) -> Optional[float]:
        """
        Check if domain is in backoff period.

        Returns:
            Remaining backoff time in seconds, or None
        """
        if domain in self.backoff_until:
            remaining = self.backoff_until[domain] - time.time()
            if remaining > 0:
                return remaining
            else:
                del self.backoff_until[domain]
        return None

    def _trigger_backoff(self, domain: str, status_code: int):
        """Trigger exponential backoff for domain."""
        errors = self.recent_errors[domain]
        errors.append((time.time(), status_code))

        # Calculate backoff based on recent error count
        backoff_seconds = min(
            300,  # Max 5 minutes
            self.backoff_factor ** len(errors)
        )

        self.backoff_until[domain] = time.time() + backoff_seconds

        logger.warning(
            f"Rate limit exceeded for {domain}. "
            f"Backing off for {backoff_seconds:.1f}s"
        )

    def record_response(self, url: str, status_code: int):
        """
        Record response for adaptive throttling.

        Args:
            url: Request URL
            status_code: HTTP status code
        """
        domain = self._extract_domain(url)
        stats = self.domain_stats[domain]

        stats['last_request'] = time.time()
        stats['requests'] += 1

        # Handle rate limiting responses
        if status_code in (429, 503):
            stats['throttled'] += 1
            self._trigger_backoff(domain, status_code)
        elif status_code >= 500:
            stats['errors'] += 1
            # Don't backoff immediately on 5xx, but track
            self.recent_errors[domain].append((time.time(), status_code))

    @contextmanager
    def acquire(self, url: str, timeout: float = 60.0):
        """
        Acquire rate limit token for URL.

        Usage:
            with limiter.acquire(url) as waited:
                response = requests.get(url)
                limiter.record_response(url, response.status_code)

        Args:
            url: Target URL
            timeout: Max wait time in seconds

        Yields:
            Time waited in seconds
        """
        domain = self._extract_domain(url)
        bucket = self._get_bucket(domain)

        start_time = time.time()
        total_waited = 0.0

        # Check for backoff period
        backoff_remaining = self._is_backed_off(domain)
        if backoff_remaining:
            if backoff_remaining > timeout:
                raise TimeoutError(
                    f"Backoff period ({backoff_remaining:.1f}s) "
                    f"exceeds timeout ({timeout}s)"
                )
            logger.info(f"Waiting {backoff_remaining:.1f}s for backoff")
            time.sleep(backoff_remaining)
            total_waited += backoff_remaining

        # Wait for token
        while not bucket.consume():
            wait_time = bucket.wait_time()

            if time.time() - start_time + wait_time > timeout:
                raise TimeoutError(
                    f"Rate limit wait time exceeds timeout ({timeout}s)"
                )

            logger.debug(f"Rate limited, waiting {wait_time:.2f}s for {domain}")
            time.sleep(wait_time)
            total_waited += wait_time

        yield total_waited

    def get_stats(self, domain: Optional[str] = None) -> dict:
        """
        Get rate limiting statistics.

        Args:
            domain: Specific domain, or None for all domains

        Returns:
            Statistics dictionary
        """
        if domain:
            return {
                'domain': domain,
                **self.domain_stats[domain],
                'in_backoff': self._is_backed_off(domain) is not None
            }

        return {
            domain: {
                **stats,
                'in_backoff': self._is_backed_off(domain) is not None
            }
            for domain, stats in self.domain_stats.items()
        }

    def set_domain_limit(self, domain: str, requests_per_second: float):
        """
        Set custom rate limit for specific domain.

        Args:
            domain: Target domain
            requests_per_second: Custom rate limit
        """
        with self.lock:
            burst_size = int(requests_per_second * 2)
            self.buckets[domain] = TokenBucket(
                requests_per_second,
                burst_size
            )
        logger.info(f"Set rate limit for {domain}: {requests_per_second} req/s")


# Example integration with requests
def rate_limited_get(
    url: str,
    limiter: RateLimiter,
    session: Optional[object] = None,
    **kwargs
) -> object:
    """
    Make rate-limited HTTP GET request.

    Args:
        url: Target URL
        limiter: RateLimiter instance
        session: Optional requests.Session
        **kwargs: Additional arguments for requests.get

    Returns:
        requests.Response object
    """
    import requests

    session = session or requests
    retry_count = 0

    while retry_count <= limiter.max_retries:
        try:
            with limiter.acquire(url) as waited:
                if waited > 0:
                    logger.debug(f"Waited {waited:.2f}s for rate limit")

                response = session.get(url, **kwargs)
                limiter.record_response(url, response.status_code)

                # Handle rate limiting
                if response.status_code in (429, 503):
                    retry_count += 1
                    if retry_count <= limiter.max_retries:
                        logger.warning(
                            f"Retry {retry_count}/{limiter.max_retries} "
                            f"for {url}"
                        )
                        continue

                return response

        except TimeoutError as e:
            logger.error(f"Rate limit timeout: {e}")
            raise

    raise Exception(f"Max retries ({limiter.max_retries}) exceeded for {url}")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    limiter = RateLimiter(requests_per_second=2.0)

    # Set custom limit for specific domain
    limiter.set_domain_limit('slow-api.example.com', 0.5)

    # Make rate-limited requests
    urls = [
        'https://example.com/page1',
        'https://example.com/page2',
        'https://slow-api.example.com/data',
    ]

    for url in urls:
        try:
            response = rate_limited_get(url, limiter, timeout=10)
            print(f"✓ {url}: {response.status_code}")
        except Exception as e:
            print(f"✗ {url}: {e}")

    # Print statistics
    print("\nRate Limiting Statistics:")
    print(limiter.get_stats())
