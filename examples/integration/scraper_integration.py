"""
Integration Example: Enhanced Documentation Scraper
===================================================

This module demonstrates how to integrate rate limiting, caching, and
authentication into the existing documentation scraper.

Features:
- Rate-limited requests to prevent server overload
- Multi-tier caching to reduce redundant requests
- Authentication support for protected documentation
- Progress tracking and statistics
- Error handling and retry logic

Usage:
    from scraper_integration import EnhancedScraper

    scraper = EnhancedScraper(
        requests_per_second=2.0,
        cache_dir='.cache',
        enable_auth=True
    )

    scraper.scrape_site('https://api.example.com/docs')
"""

import sys
import time
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import urljoin, urlparse
from collections import deque
import logging

# Add examples directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup
import markdownify
import requests

# Import our enhanced modules
from rate_limiting.rate_limiter import RateLimiter
from caching.cache_manager import CacheManager
from auth.auth_manager import AuthManager, AuthType

logger = logging.getLogger(__name__)


class EnhancedScraper:
    """
    Enhanced documentation scraper with rate limiting, caching, and auth.
    """

    def __init__(
        self,
        requests_per_second: float = 2.0,
        cache_dir: str = '.cache',
        cache_ttl: int = 3600,
        max_memory_cache: int = 100,
        enable_auth: bool = False,
        timeout: int = 10
    ):
        """
        Initialize enhanced scraper.

        Args:
            requests_per_second: Rate limit (requests/second)
            cache_dir: Directory for disk cache
            cache_ttl: Cache time-to-live in seconds
            max_memory_cache: Max items in memory cache
            enable_auth: Enable authentication support
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            requests_per_second=requests_per_second,
            burst_size=int(requests_per_second * 3),
            max_retries=3
        )

        # Initialize cache
        self.cache_manager = CacheManager(
            max_memory_size=max_memory_cache,
            disk_cache_dir=cache_dir,
            default_ttl=cache_ttl
        )

        # Initialize auth (if enabled)
        self.auth_manager = AuthManager() if enable_auth else None

        # Statistics
        self.stats = {
            'pages_discovered': 0,
            'pages_processed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }

        logger.info("Enhanced scraper initialized")

    def _get_session(self, url: str) -> requests.Session:
        """Get appropriate session (authenticated or not)."""
        if self.auth_manager:
            return self.auth_manager.get_authenticated_session(url)
        return requests.Session()

    def _fetch_url(self, url: str) -> Optional[str]:
        """
        Fetch URL with rate limiting and caching.

        Args:
            url: Target URL

        Returns:
            HTML content or None
        """
        # Check cache first
        cached_content = self.cache_manager.get(url)
        if cached_content:
            self.stats['cache_hits'] += 1
            logger.debug(f"Cache hit: {url}")
            return cached_content

        self.stats['cache_misses'] += 1

        # Rate-limited fetch
        try:
            session = self._get_session(url)

            with self.rate_limiter.acquire(url, timeout=30) as wait_time:
                if wait_time > 0:
                    logger.info(f"Waited {wait_time:.2f}s for rate limit")

                response = session.get(url, timeout=self.timeout)
                self.rate_limiter.record_response(url, response.status_code)

                response.raise_for_status()
                content = response.text

                # Cache the result
                self.cache_manager.set(url, content)

                logger.info(f"Fetched: {url} ({response.status_code})")
                return content

        except requests.exceptions.RequestException as e:
            self.stats['errors'] += 1
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def get_all_site_links(self, base_url: str) -> List[str]:
        """
        Crawl website to find all unique internal pages.

        Args:
            base_url: Starting URL

        Returns:
            List of unique URLs
        """
        to_visit = deque([base_url])
        visited = {base_url}
        all_links = {base_url}

        base_netloc = urlparse(base_url).netloc
        base_path = urlparse(base_url).path

        logger.info(f"Crawling {base_url} to discover pages...")

        while to_visit:
            current_url = to_visit.popleft()

            html_content = self._fetch_url(current_url)
            if not html_content:
                continue

            soup = BeautifulSoup(html_content, 'html.parser')

            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                absolute_link = urljoin(current_url, href)

                parsed_link = urlparse(absolute_link)
                clean_link = parsed_link._replace(query="", fragment="").geturl()

                # Same domain and path check
                if (urlparse(clean_link).netloc == base_netloc and
                        urlparse(clean_link).path.startswith(base_path) and
                        clean_link not in visited):
                    visited.add(clean_link)
                    all_links.add(clean_link)
                    to_visit.append(clean_link)

            self.stats['pages_discovered'] = len(all_links)

        logger.info(f"Discovered {len(all_links)} unique pages")
        return sorted(list(all_links))

    def extract_main_content(self, html_content: str) -> str:
        """
        Extract main documentation content.

        Args:
            html_content: Full HTML content

        Returns:
            Main content HTML
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Try common content selectors
        main_content = soup.find('main')
        if main_content:
            return str(main_content)

        main_content = soup.select_one('article, .main-content, #content')
        if main_content:
            return str(main_content)

        return ""

    def convert_html_to_markdown(self, html_content: str) -> str:
        """
        Convert HTML to Markdown.

        Args:
            html_content: HTML string

        Returns:
            Markdown string
        """
        return markdownify.markdownify(
            html_content,
            heading_style="ATX",
            bullets="*"
        )

    def generate_filename(self, base_url: str) -> str:
        """
        Generate output filename from URL.

        Args:
            base_url: Source URL

        Returns:
            Filename string
        """
        parsed = urlparse(base_url)
        path_part = parsed.path.strip('/').replace('/', '_')
        domain_part = parsed.netloc.replace(".", "_")

        if not path_part:
            return f"{domain_part}_documentation.md"
        return f"{domain_part}_{path_part}_documentation.md"

    def scrape_site(
        self,
        base_url: str,
        output_filename: Optional[str] = None
    ) -> Dict:
        """
        Scrape entire documentation site.

        Args:
            base_url: Starting URL
            output_filename: Optional custom filename

        Returns:
            Statistics dictionary
        """
        self.stats['start_time'] = time.time()

        logger.info(f"Starting scrape: {base_url}")

        # Discover all pages
        all_page_urls = self.get_all_site_links(base_url)

        # Build documentation
        full_documentation = ""

        main_title = " ".join(
            part.capitalize()
            for part in urlparse(base_url).path.strip('/').split('/')
        )
        full_documentation += f"# Documentation for {main_title or urlparse(base_url).netloc}\n"
        full_documentation += f"**Source:** {base_url}\n"
        full_documentation += f"**Scraped:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # Process each page
        for url in all_page_urls:
            logger.info(f"Processing: {url}")

            html_content = self._fetch_url(url)
            if not html_content:
                continue

            try:
                soup = BeautifulSoup(html_content, 'html.parser')
                page_title = soup.title.string if soup.title else url

                # Clean title
                import re
                page_title = re.sub(r'\|.*$| - .*$', '', page_title).strip()

                main_content_html = self.extract_main_content(html_content)

                if main_content_html:
                    markdown_content = self.convert_html_to_markdown(
                        main_content_html
                    )

                    full_documentation += f"## {page_title}\n\n"
                    full_documentation += f"**Original Page:** `{url}`\n\n"
                    full_documentation += markdown_content
                    full_documentation += "\n\n---\n\n"

                    self.stats['pages_processed'] += 1
                else:
                    logger.warning(f"No main content found: {url}")

            except Exception as e:
                self.stats['errors'] += 1
                logger.error(f"Failed to process {url}: {e}")

        # Save output
        filename = output_filename or self.generate_filename(base_url)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(full_documentation)

        self.stats['end_time'] = time.time()
        duration = self.stats['end_time'] - self.stats['start_time']

        logger.info(f"✓ Scrape complete: {filename}")
        logger.info(f"  Duration: {duration:.1f}s")
        logger.info(f"  Pages: {self.stats['pages_processed']}/{self.stats['pages_discovered']}")
        logger.info(f"  Cache hits: {self.stats['cache_hits']}")
        logger.info(f"  Errors: {self.stats['errors']}")

        return {
            **self.stats,
            'duration': duration,
            'output_file': filename
        }

    def get_statistics(self) -> Dict:
        """Get comprehensive statistics."""
        return {
            'scraper': self.stats,
            'rate_limiter': self.rate_limiter.get_stats(),
            'cache': self.cache_manager.stats()
        }

    def cleanup(self):
        """Cleanup expired cache entries."""
        removed = self.cache_manager.cleanup()
        logger.info(f"Cleaned up {removed} expired cache entries")


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(
        description="Enhanced documentation scraper with rate limiting and caching"
    )
    parser.add_argument('url', help="Documentation site URL")
    parser.add_argument('--rate', type=float, default=2.0,
                        help="Requests per second (default: 2.0)")
    parser.add_argument('--cache-dir', default='.cache',
                        help="Cache directory (default: .cache)")
    parser.add_argument('--no-cache', action='store_true',
                        help="Disable caching")
    parser.add_argument('--auth', action='store_true',
                        help="Enable authentication")
    parser.add_argument('--output', help="Output filename")

    args = parser.parse_args()

    scraper = EnhancedScraper(
        requests_per_second=args.rate,
        cache_dir=args.cache_dir if not args.no_cache else '/tmp/no_cache',
        enable_auth=args.auth
    )

    try:
        stats = scraper.scrape_site(args.url, args.output)
        print("\n" + "="*60)
        print("SCRAPING COMPLETE")
        print("="*60)
        print(f"Output file: {stats['output_file']}")
        print(f"Duration: {stats['duration']:.1f}s")
        print(f"Pages processed: {stats['pages_processed']}/{stats['pages_discovered']}")
        print(f"Cache hit rate: {stats['cache_hits']/(stats['cache_hits']+stats['cache_misses'])*100:.1f}%")
        print(f"Errors: {stats['errors']}")

    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
        stats = scraper.get_statistics()
        print(f"Partial results: {stats['scraper']['pages_processed']} pages processed")
