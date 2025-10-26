"""
Async HTTP Client for Documentation Scraper
============================================

High-performance async HTTP client with connection pooling, retry logic,
and exponential backoff for concurrent documentation scraping.

Features:
- aiohttp-based async requests
- Connection pooling with configurable limits
- DNS caching for performance
- Retry logic with exponential backoff
- Timeout management
- Session persistence
- Context manager interface

Usage:
    async with AsyncHTTPClient(max_connections=100) as client:
        html = await client.get('https://example.com/docs')
"""

import asyncio
import aiohttp
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class AsyncHTTPClient:
    """
    Async HTTP client with connection pooling and retry logic.

    Provides high-performance HTTP requests for concurrent scraping operations.
    """

    def __init__(
        self,
        max_connections: int = 100,
        max_per_host: int = 10,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        dns_ttl: int = 300
    ):
        """
        Initialize async HTTP client.

        Args:
            max_connections: Total connection pool limit
            max_per_host: Per-domain connection limit
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            backoff_factor: Exponential backoff multiplier
            dns_ttl: DNS cache TTL in seconds
        """
        self.max_connections = max_connections
        self.max_per_host = max_per_host
        self.timeout_seconds = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        # Create timeout configuration
        self.timeout = aiohttp.ClientTimeout(total=timeout)

        # Create TCP connector with pooling
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=max_per_host,
            ttl_dns_cache=dns_ttl,
            enable_cleanup_closed=True,
            force_close=False  # Reuse connections
        )

        self.session: Optional[aiohttp.ClientSession] = None

        # Statistics
        self.stats = {
            'requests': 0,
            'retries': 0,
            'errors': 0,
            'timeouts': 0
        }

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout
        )
        logger.info(
            f"AsyncHTTPClient initialized: "
            f"max_connections={self.max_connections}, "
            f"max_per_host={self.max_per_host}"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            # Give time for connections to close
            await asyncio.sleep(0.25)
        logger.info(f"AsyncHTTPClient closed. Stats: {self.stats}")

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """
        Perform async HTTP GET request with retry logic.

        Args:
            url: Target URL
            headers: Optional custom headers
            **kwargs: Additional aiohttp request parameters

        Returns:
            Response text content

        Raises:
            aiohttp.ClientError: On request failure after retries
        """
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        retry_count = 0
        last_exception = None

        while retry_count <= self.max_retries:
            try:
                self.stats['requests'] += 1

                async with self.session.get(
                    url,
                    headers=headers,
                    **kwargs
                ) as response:
                    response.raise_for_status()
                    text = await response.text()

                    logger.debug(
                        f"GET {url} -> {response.status} "
                        f"({len(text)} bytes)"
                    )

                    return text

            except asyncio.TimeoutError as e:
                self.stats['timeouts'] += 1
                last_exception = e
                logger.warning(
                    f"Timeout for {url} (attempt {retry_count + 1}/{self.max_retries + 1})"
                )

            except aiohttp.ClientError as e:
                self.stats['errors'] += 1
                last_exception = e

                # Don't retry on 4xx errors (except 429)
                if hasattr(e, 'status') and 400 <= e.status < 500 and e.status != 429:
                    logger.error(f"Client error for {url}: {e}")
                    raise

                logger.warning(
                    f"Error fetching {url}: {e} "
                    f"(attempt {retry_count + 1}/{self.max_retries + 1})"
                )

            except Exception as e:
                self.stats['errors'] += 1
                logger.error(f"Unexpected error for {url}: {e}")
                raise

            # Increment retry counter
            retry_count += 1

            if retry_count <= self.max_retries:
                self.stats['retries'] += 1
                # Exponential backoff
                backoff_time = self.backoff_factor ** retry_count
                logger.debug(f"Backing off for {backoff_time:.2f}s")
                await asyncio.sleep(backoff_time)

        # All retries exhausted
        logger.error(
            f"Failed to fetch {url} after {self.max_retries + 1} attempts"
        )
        raise last_exception

    async def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """
        Perform async HTTP POST request.

        Args:
            url: Target URL
            data: Form data
            json: JSON data
            headers: Optional custom headers
            **kwargs: Additional aiohttp request parameters

        Returns:
            Response text content
        """
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        self.stats['requests'] += 1

        try:
            async with self.session.post(
                url,
                data=data,
                json=json,
                headers=headers,
                **kwargs
            ) as response:
                response.raise_for_status()
                return await response.text()

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"POST request failed for {url}: {e}")
            raise

    def get_stats(self) -> Dict[str, int]:
        """
        Get client statistics.

        Returns:
            Dictionary of statistics
        """
        return self.stats.copy()


# Example usage
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def main():
        """Example async HTTP client usage."""
        async with AsyncHTTPClient(max_connections=50) as client:
            # Fetch multiple URLs concurrently
            urls = [
                'https://docs.python.org/3/',
                'https://docs.python.org/3/library/',
                'https://docs.python.org/3/tutorial/',
            ]

            tasks = [client.get(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for url, result in zip(urls, results):
                if isinstance(result, Exception):
                    print(f"✗ {url}: {result}")
                else:
                    print(f"✓ {url}: {len(result)} bytes")

            print(f"\nStats: {client.get_stats()}")

    # Run example
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
