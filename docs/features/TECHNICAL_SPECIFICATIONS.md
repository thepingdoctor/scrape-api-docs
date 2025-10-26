# Technical Specifications: Feature Implementations

**Project:** scrape-api-docs
**Version:** 1.0.0 Specification
**Date:** 2025-10-26
**Status:** Draft for Implementation

---

## Document Purpose

This document provides detailed technical specifications for all proposed features in the scrape-api-docs roadmap. Each feature includes architecture, implementation details, API interfaces, and technical requirements.

---

## Table of Contents

1. [Robots.txt Compliance](#1-robotstxt-compliance)
2. [Rate Limiting & Politeness](#2-rate-limiting--politeness)
3. [SSRF Protection](#3-ssrf-protection)
4. [Async/Concurrent Requests](#4-asyncconcurrent-requests)
5. [Resume Capability](#5-resume-capability)
6. [Multiple Export Formats](#6-multiple-export-formats)
7. [Content Filtering](#7-content-filtering)
8. [Configuration System](#8-configuration-system)
9. [Error Handling & Retry](#9-error-handling--retry)
10. [REST API Interface](#10-rest-api-interface)

---

## 1. Robots.txt Compliance

### 1.1 Overview
Implement RFC 9309 compliant robots.txt parsing and enforcement to ensure ethical and legal scraping.

### 1.2 Architecture

```python
# Core Components
class RobotsManager:
    """Manages robots.txt parsing and compliance checking."""

    def __init__(self, user_agent: str = "scrape-api-docs/1.0.0"):
        self.user_agent = user_agent
        self.cache: dict[str, RobotFileParser] = {}
        self.cache_ttl = 3600  # 1 hour

    def is_allowed(self, url: str) -> tuple[bool, str]:
        """Check if URL is allowed by robots.txt."""
        pass

    def get_crawl_delay(self, url: str) -> int:
        """Get crawl delay for domain from robots.txt."""
        pass

    def _get_robots_parser(self, domain: str) -> RobotFileParser:
        """Get or create robots parser for domain."""
        pass

    def clear_cache(self):
        """Clear robots.txt cache."""
        pass
```

### 1.3 Implementation Details

**File:** `src/scrape_api_docs/robots_manager.py`

```python
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
import requests
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class RobotsManager:
    """RFC 9309 compliant robots.txt manager."""

    def __init__(self, user_agent: str = "scrape-api-docs/1.0.0"):
        self.user_agent = user_agent
        self.cache: dict[str, tuple[RobotFileParser, datetime]] = {}
        self.cache_ttl = timedelta(hours=1)

    def is_allowed(self, url: str) -> tuple[bool, str]:
        """
        Check if URL is allowed by robots.txt.

        Args:
            url: Target URL to check

        Returns:
            Tuple of (is_allowed: bool, reason: str)
        """
        try:
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"

            parser = self._get_robots_parser(domain)
            if parser is None:
                logger.warning(f"No robots.txt found for {domain}, allowing by default")
                return True, "No robots.txt found"

            allowed = parser.can_fetch(self.user_agent, url)

            if not allowed:
                reason = f"Disallowed by robots.txt for user-agent '{self.user_agent}'"
                logger.info(f"Blocked: {url} - {reason}")
                return False, reason

            return True, "Allowed by robots.txt"

        except Exception as e:
            logger.error(f"Error checking robots.txt for {url}: {e}")
            return True, f"Error checking robots.txt: {e}"

    def get_crawl_delay(self, url: str) -> int:
        """
        Get crawl delay in seconds from robots.txt.

        Args:
            url: Target URL

        Returns:
            Crawl delay in seconds (default: 1)
        """
        try:
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"

            parser = self._get_robots_parser(domain)
            if parser is None:
                return 1  # Default delay

            delay = parser.crawl_delay(self.user_agent)
            return int(delay) if delay else 1

        except Exception as e:
            logger.error(f"Error getting crawl delay: {e}")
            return 1

    def _get_robots_parser(self, domain: str) -> RobotFileParser | None:
        """
        Get or create robots.txt parser for domain.

        Args:
            domain: Domain URL (e.g., https://example.com)

        Returns:
            RobotFileParser instance or None if not available
        """
        # Check cache
        if domain in self.cache:
            parser, cached_at = self.cache[domain]
            if datetime.now() - cached_at < self.cache_ttl:
                return parser

        # Fetch and parse robots.txt
        try:
            robots_url = f"{domain}/robots.txt"
            parser = RobotFileParser()
            parser.set_url(robots_url)

            # Use requests for better control
            response = requests.get(robots_url, timeout=5)
            if response.status_code == 200:
                parser.parse(response.text.splitlines())
                self.cache[domain] = (parser, datetime.now())
                logger.info(f"Fetched robots.txt from {robots_url}")
                return parser
            else:
                logger.warning(f"robots.txt not found at {robots_url} (status {response.status_code})")
                return None

        except requests.RequestException as e:
            logger.error(f"Failed to fetch robots.txt from {domain}: {e}")
            return None

    def clear_cache(self):
        """Clear robots.txt cache."""
        self.cache.clear()
        logger.info("Robots.txt cache cleared")
```

### 1.4 Integration Points

**Scraper Integration:**
```python
# In scraper.py
from scrape_api_docs.robots_manager import RobotsManager

def scrape_site(base_url: str, respect_robots: bool = True):
    """Scrape site with robots.txt compliance."""
    robots = RobotsManager() if respect_robots else None

    for url in urls_to_scrape:
        if robots:
            allowed, reason = robots.is_allowed(url)
            if not allowed:
                logger.warning(f"Skipping {url}: {reason}")
                continue

            crawl_delay = robots.get_crawl_delay(url)
            time.sleep(crawl_delay)

        # Continue with scraping...
```

### 1.5 Configuration

**CLI:**
```bash
scrape-docs https://example.com --respect-robots --user-agent "MyBot/1.0"
```

**Config File:**
```yaml
scraper:
  respect_robots_txt: true
  user_agent: "scrape-api-docs/1.0.0"
  robots_cache_ttl: 3600
```

**UI:**
- Checkbox: "Respect robots.txt" (default: checked)
- Input: "User-Agent" (default: scrape-api-docs/1.0.0)

### 1.6 Testing Requirements

```python
# tests/unit/test_robots_manager.py

def test_robots_allows_url():
    """Test robots.txt allows specific URL."""
    # Mock robots.txt response
    # Verify URL is allowed

def test_robots_blocks_url():
    """Test robots.txt blocks specific URL."""
    # Mock robots.txt with disallow
    # Verify URL is blocked

def test_robots_missing():
    """Test behavior when robots.txt is missing."""
    # Mock 404 response
    # Verify default allow behavior

def test_crawl_delay_extraction():
    """Test crawl delay extraction from robots.txt."""
    # Mock robots.txt with crawl-delay directive
    # Verify correct delay returned

def test_robots_cache():
    """Test robots.txt caching mechanism."""
    # Verify cache hit/miss behavior
    # Test TTL expiration
```

---

## 2. Rate Limiting & Politeness

### 2.1 Overview
Implement configurable rate limiting and politeness delays to prevent overwhelming target servers.

### 2.2 Architecture

```python
class RateLimiter:
    """Token bucket rate limiter with politeness delays."""

    def __init__(
        self,
        requests_per_minute: int = 10,
        politeness_delay: float = 1.0
    ):
        self.rate = requests_per_minute
        self.delay = politeness_delay
        self.last_request_time: dict[str, float] = {}

    def wait_if_needed(self, domain: str):
        """Wait if rate limit requires delay."""
        pass

    def reset(self):
        """Reset rate limiter state."""
        pass
```

### 2.3 Implementation Details

**File:** `src/scrape_api_docs/rate_limiter.py`

```python
import time
from collections import defaultdict
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Token bucket rate limiter with per-domain tracking.

    Implements:
    - Requests per minute limit
    - Politeness delay between requests
    - Per-domain rate tracking
    - Thread-safe operation
    """

    def __init__(
        self,
        requests_per_minute: int = 10,
        politeness_delay: float = 1.0
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute per domain
            politeness_delay: Minimum seconds between requests to same domain
        """
        self.rate = requests_per_minute
        self.delay = politeness_delay
        self.last_request_time: dict[str, float] = defaultdict(float)
        self.request_times: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()

    def wait_if_needed(self, domain: str):
        """
        Wait if rate limit requires delay.

        Args:
            domain: Target domain for rate limiting
        """
        with self.lock:
            current_time = time.time()

            # Apply politeness delay
            time_since_last = current_time - self.last_request_time[domain]
            if time_since_last < self.delay:
                wait_time = self.delay - time_since_last
                logger.debug(f"Politeness delay: waiting {wait_time:.2f}s for {domain}")
                time.sleep(wait_time)
                current_time = time.time()

            # Apply rate limit
            self._apply_rate_limit(domain, current_time)

            # Update last request time
            self.last_request_time[domain] = time.time()

    def _apply_rate_limit(self, domain: str, current_time: float):
        """
        Apply requests-per-minute rate limit.

        Args:
            domain: Target domain
            current_time: Current timestamp
        """
        # Remove requests older than 1 minute
        cutoff = current_time - 60
        self.request_times[domain] = [
            t for t in self.request_times[domain] if t > cutoff
        ]

        # Check if rate limit exceeded
        if len(self.request_times[domain]) >= self.rate:
            # Calculate wait time until oldest request expires
            oldest_request = min(self.request_times[domain])
            wait_time = 60 - (current_time - oldest_request)

            if wait_time > 0:
                logger.info(f"Rate limit: waiting {wait_time:.2f}s for {domain}")
                time.sleep(wait_time)

        # Record this request
        self.request_times[domain].append(time.time())

    def reset(self):
        """Reset all rate limiter state."""
        with self.lock:
            self.last_request_time.clear()
            self.request_times.clear()
            logger.info("Rate limiter reset")

    def get_stats(self, domain: str) -> dict:
        """
        Get rate limiting statistics for domain.

        Args:
            domain: Target domain

        Returns:
            Dictionary with request counts and timing
        """
        with self.lock:
            current_time = time.time()
            cutoff = current_time - 60

            recent_requests = [
                t for t in self.request_times[domain] if t > cutoff
            ]

            return {
                "domain": domain,
                "requests_last_minute": len(recent_requests),
                "rate_limit": self.rate,
                "politeness_delay": self.delay,
                "last_request": self.last_request_time.get(domain, 0)
            }
```

### 2.4 Integration

```python
# In scraper.py
from urllib.parse import urlparse
from scrape_api_docs.rate_limiter import RateLimiter

def scrape_site(base_url: str, rate_limit: int = 10, politeness: float = 1.0):
    """Scrape with rate limiting."""
    limiter = RateLimiter(rate_limit, politeness)

    for url in urls:
        domain = urlparse(url).netloc
        limiter.wait_if_needed(domain)

        # Make request...
```

### 2.5 Configuration

**CLI:**
```bash
scrape-docs https://example.com --rate-limit 20 --delay 0.5
```

**Config File:**
```yaml
scraper:
  rate_limit: 10  # requests per minute
  politeness_delay: 1.0  # seconds
```

**UI:**
- Slider: "Requests per minute" (1-60, default: 10)
- Slider: "Politeness delay" (0.1-5.0s, default: 1.0)

### 2.6 Testing

```python
def test_rate_limiter_enforces_delay():
    """Test politeness delay is enforced."""
    limiter = RateLimiter(politeness_delay=1.0)

    start = time.time()
    limiter.wait_if_needed("example.com")
    limiter.wait_if_needed("example.com")
    elapsed = time.time() - start

    assert elapsed >= 1.0

def test_rate_limiter_per_minute():
    """Test requests per minute limit."""
    limiter = RateLimiter(requests_per_minute=5, politeness_delay=0)

    for _ in range(5):
        limiter.wait_if_needed("example.com")

    # 6th request should trigger rate limit wait
    start = time.time()
    limiter.wait_if_needed("example.com")
    elapsed = time.time() - start

    assert elapsed > 0  # Should have waited
```

---

## 3. SSRF Protection

### 3.1 Overview
Prevent Server-Side Request Forgery attacks by validating and blocking dangerous URLs.

### 3.2 Architecture

```python
class URLValidator:
    """Validates URLs for SSRF and injection attacks."""

    BLOCKED_NETWORKS = [
        ipaddress.ip_network('127.0.0.0/8'),      # Localhost
        ipaddress.ip_network('10.0.0.0/8'),       # Private
        ipaddress.ip_network('172.16.0.0/12'),    # Private
        ipaddress.ip_network('192.168.0.0/16'),   # Private
        ipaddress.ip_network('169.254.0.0/16'),   # Link-local
    ]

    def validate_url(self, url: str) -> tuple[bool, str]:
        """Validate URL for security issues."""
        pass

    def is_safe_ip(self, ip: str) -> bool:
        """Check if IP address is safe."""
        pass
```

### 3.3 Implementation Details

**File:** `src/scrape_api_docs/url_validator.py`

```python
import ipaddress
import socket
from urllib.parse import urlparse
import re
import logging

logger = logging.getLogger(__name__)

class URLValidator:
    """
    Comprehensive URL validation for security.

    Prevents:
    - SSRF (Server-Side Request Forgery)
    - Internal network access
    - Cloud metadata endpoint access
    - Invalid URL formats
    - Dangerous protocols
    """

    BLOCKED_NETWORKS = [
        ipaddress.ip_network('127.0.0.0/8'),      # Localhost
        ipaddress.ip_network('10.0.0.0/8'),       # RFC 1918 private
        ipaddress.ip_network('172.16.0.0/12'),    # RFC 1918 private
        ipaddress.ip_network('192.168.0.0/16'),   # RFC 1918 private
        ipaddress.ip_network('169.254.0.0/16'),   # Link-local
        ipaddress.ip_network('::1/128'),          # IPv6 localhost
        ipaddress.ip_network('fc00::/7'),         # IPv6 private
        ipaddress.ip_network('fe80::/10'),        # IPv6 link-local
    ]

    ALLOWED_SCHEMES = ['http', 'https']

    def validate_url(self, url: str) -> tuple[bool, str]:
        """
        Comprehensive URL validation.

        Args:
            url: URL to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        # Check URL format
        if not url or not isinstance(url, str):
            return False, "URL must be a non-empty string"

        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            return False, f"Invalid URL format: {e}"

        # Validate scheme
        if parsed.scheme not in self.ALLOWED_SCHEMES:
            return False, f"Only {', '.join(self.ALLOWED_SCHEMES)} protocols allowed"

        # Validate hostname
        if not parsed.hostname:
            return False, "URL must include a hostname"

        # Check for dangerous hostnames
        if self._is_dangerous_hostname(parsed.hostname):
            return False, f"Access to {parsed.hostname} is blocked"

        # Resolve and check IP
        try:
            ip_address = socket.gethostbyname(parsed.hostname)
            if not self.is_safe_ip(ip_address):
                return False, f"Access to IP {ip_address} is blocked (internal network)"
        except socket.gaierror:
            return False, f"Could not resolve hostname: {parsed.hostname}"

        return True, ""

    def is_safe_ip(self, ip: str) -> bool:
        """
        Check if IP address is safe (not in blocked networks).

        Args:
            ip: IP address string

        Returns:
            True if IP is safe, False if blocked
        """
        try:
            ip_obj = ipaddress.ip_address(ip)

            for network in self.BLOCKED_NETWORKS:
                if ip_obj in network:
                    logger.warning(f"Blocked IP {ip} in network {network}")
                    return False

            return True

        except ValueError:
            logger.error(f"Invalid IP address: {ip}")
            return False

    def _is_dangerous_hostname(self, hostname: str) -> bool:
        """
        Check if hostname is dangerous (localhost, metadata endpoints).

        Args:
            hostname: Hostname to check

        Returns:
            True if dangerous, False otherwise
        """
        dangerous_patterns = [
            r'^localhost$',
            r'^127\.',
            r'^10\.',
            r'^192\.168\.',
            r'^172\.(1[6-9]|2[0-9]|3[01])\.',
            r'^169\.254\.',  # Link-local
            r'^metadata\.google\.internal$',  # GCP metadata
            r'^169\.254\.169\.254$',  # AWS/Azure metadata
        ]

        hostname_lower = hostname.lower()

        for pattern in dangerous_patterns:
            if re.match(pattern, hostname_lower):
                return True

        return False

    def validate_filename(self, filename: str) -> tuple[bool, str]:
        """
        Validate and sanitize filename for security.

        Args:
            filename: Proposed filename

        Returns:
            Tuple of (sanitized_filename: str, error_message: str)
        """
        if not filename:
            return "", "Filename cannot be empty"

        # Remove path traversal attempts
        sanitized = filename.replace('../', '').replace('..\\', '')
        sanitized = sanitized.replace('/', '_').replace('\\', '_')

        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')

        # Limit length
        max_length = 255
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        # Ensure .md extension
        if not sanitized.endswith('.md'):
            sanitized += '.md'

        return sanitized, ""
```

### 3.4 Integration

```python
# In scraper.py
from scrape_api_docs.url_validator import URLValidator

def scrape_site(base_url: str):
    """Scrape with URL validation."""
    validator = URLValidator()

    # Validate base URL
    is_valid, error = validator.validate_url(base_url)
    if not is_valid:
        raise ValueError(f"Invalid URL: {error}")

    # Continue with scraping...
```

### 3.5 Testing

```python
def test_blocks_localhost():
    """Test localhost URLs are blocked."""
    validator = URLValidator()

    invalid_urls = [
        "http://localhost/api",
        "http://127.0.0.1/admin",
        "http://127.0.0.2:8080",
    ]

    for url in invalid_urls:
        is_valid, _ = validator.validate_url(url)
        assert not is_valid

def test_blocks_private_ips():
    """Test private IP ranges are blocked."""
    validator = URLValidator()

    blocked = [
        "http://10.0.0.1",
        "http://192.168.1.1",
        "http://172.16.0.1",
        "http://169.254.169.254",  # AWS metadata
    ]

    for url in blocked:
        is_valid, _ = validator.validate_url(url)
        assert not is_valid

def test_allows_public_urls():
    """Test public URLs are allowed."""
    validator = URLValidator()

    valid_urls = [
        "https://example.com",
        "http://docs.python.org",
        "https://api.github.com",
    ]

    for url in valid_urls:
        is_valid, _ = validator.validate_url(url)
        assert is_valid
```

---

## 4. Async/Concurrent Requests

### 4.1 Overview
Refactor to async/await pattern for 2-10x performance improvement through concurrent requests.

### 4.2 Architecture

```python
class AsyncScraper:
    """Async scraper with concurrent request handling."""

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def scrape_site(self, base_url: str) -> str:
        """Scrape site asynchronously."""
        pass

    async def fetch_page(self, url: str) -> str:
        """Fetch single page asynchronously."""
        pass
```

### 4.3 Implementation Details

**File:** `src/scrape_api_docs/async_scraper.py`

```python
import asyncio
import aiohttp
from typing import List, Dict, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class AsyncScraper:
    """
    Asynchronous web scraper with concurrent request handling.

    Features:
    - Concurrent page fetching (configurable concurrency)
    - Rate limiting per domain
    - Progress tracking
    - Error handling and retry
    - Session management
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        timeout: int = 10,
        max_retries: int = 3
    ):
        """
        Initialize async scraper.

        Args:
            max_concurrent: Maximum concurrent requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts per URL
        """
        self.max_concurrent = max_concurrent
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def scrape_site(
        self,
        base_url: str,
        max_pages: int = 0,
        progress_callback=None
    ) -> Dict[str, str]:
        """
        Scrape entire site asynchronously.

        Args:
            base_url: Starting URL
            max_pages: Maximum pages to scrape (0 = unlimited)
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary mapping URLs to content
        """
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            # Discover all URLs
            all_urls = await self._discover_urls(session, base_url, max_pages)

            # Scrape pages concurrently
            results = {}
            total = len(all_urls)

            tasks = []
            for i, url in enumerate(all_urls):
                task = self._fetch_with_semaphore(session, url, i, total, progress_callback)
                tasks.append(task)

            # Gather results
            contents = await asyncio.gather(*tasks, return_exceptions=True)

            for url, content in zip(all_urls, contents):
                if isinstance(content, Exception):
                    logger.error(f"Failed to fetch {url}: {content}")
                else:
                    results[url] = content

            return results

    async def _discover_urls(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        max_pages: int
    ) -> List[str]:
        """
        Discover all URLs on site using BFS.

        Args:
            session: aiohttp session
            base_url: Starting URL
            max_pages: Maximum pages to discover

        Returns:
            List of discovered URLs
        """
        visited: Set[str] = set()
        to_visit = [base_url]
        base_parsed = urlparse(base_url)

        while to_visit and (max_pages == 0 or len(visited) < max_pages):
            url = to_visit.pop(0)

            if url in visited:
                continue

            visited.add(url)

            try:
                async with self.semaphore:
                    async with session.get(url) as response:
                        html = await response.text()

                soup = BeautifulSoup(html, 'html.parser')

                for link in soup.find_all('a', href=True):
                    absolute_url = urljoin(url, link['href'])
                    parsed = urlparse(absolute_url)

                    # Same domain check
                    if parsed.netloc == base_parsed.netloc:
                        # Remove fragments and queries
                        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

                        if clean_url not in visited:
                            to_visit.append(clean_url)

            except Exception as e:
                logger.error(f"Error discovering links from {url}: {e}")

        return list(visited)

    async def _fetch_with_semaphore(
        self,
        session: aiohttp.ClientSession,
        url: str,
        index: int,
        total: int,
        progress_callback
    ) -> str:
        """
        Fetch page with semaphore rate limiting.

        Args:
            session: aiohttp session
            url: URL to fetch
            index: Current index
            total: Total URLs
            progress_callback: Progress callback function

        Returns:
            Page content as string
        """
        async with self.semaphore:
            content = await self._fetch_page_with_retry(session, url)

            if progress_callback:
                progress = (index + 1) / total
                progress_callback(url, progress)

            return content

    async def _fetch_page_with_retry(
        self,
        session: aiohttp.ClientSession,
        url: str
    ) -> str:
        """
        Fetch page with exponential backoff retry.

        Args:
            session: aiohttp session
            url: URL to fetch

        Returns:
            Page HTML content
        """
        for attempt in range(self.max_retries):
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.text()

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == self.max_retries - 1:
                    raise

                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Retry {attempt + 1}/{self.max_retries} for {url} after {wait_time}s")
                await asyncio.sleep(wait_time)

        raise Exception(f"Failed to fetch {url} after {self.max_retries} attempts")

```

### 4.4 Integration

```python
# In scraper.py
from scrape_api_docs.async_scraper import AsyncScraper

async def scrape_site_async(base_url: str) -> str:
    """Async scraping entry point."""
    scraper = AsyncScraper(max_concurrent=5)

    def progress_callback(url, progress):
        print(f"[{progress*100:.1f}%] {url}")

    results = await scraper.scrape_site(base_url, progress_callback=progress_callback)

    # Convert to markdown...
    return content

# Sync wrapper
def scrape_site(base_url: str) -> str:
    """Synchronous wrapper for async scraper."""
    return asyncio.run(scrape_site_async(base_url))
```

### 4.5 Performance Targets

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| 10 pages | ~15s | ~3s | 5x faster |
| 100 pages | ~150s | ~20s | 7.5x faster |
| Memory (100 pages) | ~150MB | ~100MB | 33% reduction |

---

## Summary

This document provides detailed technical specifications for the first 4 critical features. The remaining features (Resume, Export Formats, Filtering, Configuration, REST API) follow similar structure with:

- Architecture overview
- Implementation details
- Integration points
- Configuration options
- Testing requirements

Each specification is designed to be implementation-ready with clear interfaces, error handling, and testing criteria.

---

**Document Status:** Draft for Implementation
**Next Review:** After Phase 1 development begins
**Owner:** Development Team
