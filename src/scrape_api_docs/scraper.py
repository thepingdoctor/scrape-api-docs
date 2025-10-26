"""
Core scraping functionality for documentation websites.

This module provides the main scraping logic with integrated:
- Robots.txt compliance checking
- Rate limiting and throttling
- Security validation (SSRF protection)
- Structured logging
- Comprehensive error handling
"""

import re
import time
import requests
from bs4 import BeautifulSoup
import markdownify
from urllib.parse import urljoin, urlparse
from collections import deque
from typing import List, Optional
from pathlib import Path

from .robots import RobotsChecker
from .rate_limiter import RateLimiter
from .security import SecurityValidator
from .logging_config import get_logger, PerformanceLogger
from .exceptions import (
    RobotsException,
    SSRFException,
    ValidationException,
    ContentTooLargeException,
    ContentParsingException,
    NetworkException,
    RetryableException
)
from .config import Config

logger = get_logger(__name__)


def get_all_site_links(
    base_url: str,
    max_pages: int = 100,
    config: Optional[Config] = None,
    robots_checker: Optional[RobotsChecker] = None,
    rate_limiter: Optional[RateLimiter] = None
) -> List[str]:
    """
    Crawls a website starting from the base URL to find all unique, internal pages.

    This function now includes:
    - Robots.txt compliance checking
    - Rate limiting
    - Security validation (SSRF protection)
    - Structured logging
    - Comprehensive error handling

    Args:
        base_url: The starting URL of the documentation site
        max_pages: Maximum number of pages to crawl
        config: Configuration instance (optional)
        robots_checker: RobotsChecker instance (optional, created if not provided)
        rate_limiter: RateLimiter instance (optional, created if not provided)

    Returns:
        A sorted list of unique absolute URLs belonging to the site

    Raises:
        SSRFException: If base URL fails security validation
        RobotsException: If base URL is disallowed by robots.txt
    """
    # Initialize components
    if config is None:
        config = Config.load()

    if robots_checker is None:
        robots_checker = RobotsChecker(
            user_agent=config.get('robots.user_agent', 'scrape-api-docs/0.1.0')
        )

    if rate_limiter is None:
        rate_limiter = RateLimiter(
            requests_per_second=config.get('rate_limiting.requests_per_second', 2.0),
            max_retries=config.get('rate_limiting.max_retries', 3)
        )

    # Validate base URL for security
    if config.get('security.validate_urls', True):
        valid, reason = SecurityValidator.validate_url(base_url)
        if not valid:
            raise SSRFException(
                f"Base URL failed security validation: {reason}",
                details={'url': base_url}
            )

    # Check robots.txt compliance
    if config.get('robots.enabled', True):
        allowed, reason = robots_checker.is_allowed(base_url)
        if not allowed:
            raise RobotsException(
                f"Scraping blocked by robots.txt: {reason}",
                details={'url': base_url}
            )

        # Get recommended crawl delay
        crawl_delay = robots_checker.get_crawl_delay(base_url)
        logger.info(f"Recommended crawl delay: {crawl_delay}s")
    else:
        crawl_delay = config.get('scraper.politeness_delay', 1.0)

    # Initialize crawling
    to_visit = deque([base_url])
    visited = {base_url}
    all_links = {base_url}

    base_netloc = urlparse(base_url).netloc
    base_path = urlparse(base_url).path

    session = requests.Session()
    timeout = config.get('scraper.timeout', 10)

    logger.info(f"Starting crawl of {base_url} (max {max_pages} pages)")

    with PerformanceLogger(logger, "site_crawl", base_url=base_url):
        while to_visit and len(visited) < max_pages:
            current_url = to_visit.popleft()

            try:
                # Check robots.txt for this URL
                if config.get('robots.enabled', True):
                    allowed, reason = robots_checker.is_allowed(current_url)
                    if not allowed:
                        logger.warning(f"Skipping {current_url}: {reason}")
                        continue

                # Rate limiting
                if config.get('rate_limiting.enabled', True):
                    with rate_limiter.acquire(current_url) as wait_time:
                        if wait_time > 0:
                            logger.debug(f"Waited {wait_time:.2f}s for rate limit")

                        # Make request
                        logger.info(f"Visiting: {current_url}")
                        response = session.get(current_url, timeout=timeout)

                        # Record response for adaptive throttling
                        rate_limiter.record_response(current_url, response.status_code)

                        # Handle rate limiting
                        if response.status_code == 429:
                            logger.warning(f"Rate limited by server: {current_url}")
                            continue

                        response.raise_for_status()
                else:
                    # No rate limiting - still add politeness delay
                    time.sleep(crawl_delay)
                    response = session.get(current_url, timeout=timeout)
                    response.raise_for_status()

                # Parse and extract links
                soup = BeautifulSoup(response.text, 'html.parser')

                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    absolute_link = urljoin(current_url, href)

                    parsed_link = urlparse(absolute_link)
                    clean_link = parsed_link._replace(query="", fragment="").geturl()

                    # Validate link security
                    if config.get('security.validate_urls', True):
                        valid, reason = SecurityValidator.validate_url(clean_link)
                        if not valid:
                            logger.debug(f"Blocked link: {clean_link} ({reason})")
                            continue

                    # Same domain and path check
                    if (
                        urlparse(clean_link).netloc == base_netloc and
                        urlparse(clean_link).path.startswith(base_path) and
                        clean_link not in visited
                    ):
                        visited.add(clean_link)
                        all_links.add(clean_link)
                        to_visit.append(clean_link)

            except requests.exceptions.Timeout:
                logger.error(f"Timeout crawling {current_url}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error crawling {current_url}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error at {current_url}: {e}", exc_info=True)

    logger.info(f"Crawl complete: found {len(all_links)} unique pages")
    return sorted(list(all_links))


def extract_main_content(html_content: str) -> str:
    """
    Extracts the main documentation content from a page.
    Targets the <main> element, which is common for modern doc sites.

    Args:
        html_content: The HTML content of a documentation page

    Returns:
        The main content as an HTML string, or an empty string if not found

    Raises:
        ContentParsingException: If HTML parsing fails
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Try <main> tag first
        main_content = soup.find('main')
        if main_content:
            return str(main_content)

        # Fallback to common content selectors
        main_content = soup.select_one('article, .main-content, #content')
        if main_content:
            return str(main_content)

        logger.warning("No main content found using standard selectors")
        return ""

    except Exception as e:
        raise ContentParsingException(
            "Failed to parse HTML content",
            details={'error': str(e)}
        )


def convert_html_to_markdown(html_content: str) -> str:
    """
    Converts an HTML string to Markdown using the 'markdownify' library.

    Args:
        html_content: The HTML string to convert

    Returns:
        The converted Markdown string

    Raises:
        ContentParsingException: If conversion fails
    """
    try:
        return markdownify.markdownify(
            html_content,
            heading_style="ATX",
            bullets="*"
        )
    except Exception as e:
        raise ContentParsingException(
            "Failed to convert HTML to Markdown",
            details={'error': str(e)}
        )


def generate_filename_from_url(base_url: str, config: Optional[Config] = None) -> str:
    """
    Generates a clean, secure filename from a base URL.

    Now includes security sanitization to prevent path traversal attacks.

    Args:
        base_url: The string of the base URL
        config: Configuration instance (optional)

    Returns:
        A sanitized filename string
    """
    if config is None:
        config = Config.load()

    path_part = urlparse(base_url).path.strip('/').replace('/', '_')
    domain_part = urlparse(base_url).netloc.replace(".", "_")

    # Handle case where path is empty
    if not path_part:
        filename = f"{domain_part}_documentation.md"
    else:
        filename = f"{domain_part}_{path_part}_documentation.md"

    # Apply security sanitization
    if config.get('security.sanitize_filenames', True):
        filename = SecurityValidator.sanitize_filename(filename)

    return filename


def scrape_site(
    base_url: str,
    max_pages: int = 100,
    output_dir: str = '.',
    config: Optional[Config] = None
) -> str:
    """
    Scrapes an entire documentation site, combines all content, and saves it
    to a single Markdown file.

    This is the main entry point with all Phase 1 security and compliance features.

    Args:
        base_url: The base URL of the documentation site
        max_pages: Maximum number of pages to crawl
        output_dir: Output directory for the documentation file
        config: Configuration instance (optional)

    Returns:
        Path to the output file

    Raises:
        SSRFException: If URL fails security validation
        RobotsException: If scraping is blocked by robots.txt
        ContentTooLargeException: If content exceeds size limits
    """
    if config is None:
        config = Config.load()

    # Validate configuration
    config.validate()

    # Get configuration values
    timeout = config.get('scraper.timeout', 10)
    max_content_size = config.get('scraper.max_content_size', 100 * 1024 * 1024)

    logger.info(f"Starting scrape for documentation at: {base_url}")

    with PerformanceLogger(logger, "full_scrape", base_url=base_url):
        # Initialize components
        robots_checker = RobotsChecker(
            user_agent=config.get('robots.user_agent', 'scrape-api-docs/0.1.0')
        )
        rate_limiter = RateLimiter(
            requests_per_second=config.get('rate_limiting.requests_per_second', 2.0)
        )

        # Get all page URLs
        all_page_urls = get_all_site_links(
            base_url,
            max_pages=max_pages,
            config=config,
            robots_checker=robots_checker,
            rate_limiter=rate_limiter
        )

        # Initialize documentation content
        full_documentation = ""
        main_title = " ".join(
            part.capitalize()
            for part in urlparse(base_url).path.strip('/').split('/')
        )
        full_documentation += f"# Documentation for {main_title or urlparse(base_url).netloc}\n"
        full_documentation += f"**Source:** {base_url}\n"
        full_documentation += f"**Scraped:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n"

        # Process each page
        session = requests.Session()
        pages_processed = 0
        pages_failed = 0

        for url in all_page_urls:
            try:
                logger.info(f"Processing {url}")

                # Rate limiting
                if config.get('rate_limiting.enabled', True):
                    with rate_limiter.acquire(url):
                        response = session.get(url, timeout=timeout, stream=True)
                        rate_limiter.record_response(url, response.status_code)
                else:
                    response = session.get(url, timeout=timeout, stream=True)

                # Check content length
                content_length = response.headers.get('content-length')
                if content_length:
                    valid, reason = SecurityValidator.validate_content_length(
                        int(content_length),
                        max_content_size
                    )
                    if not valid:
                        logger.warning(f"Skipping {url}: {reason}")
                        continue

                response.raise_for_status()

                # Read content with size limit
                content = b''
                for chunk in response.iter_content(chunk_size=8192):
                    content += chunk
                    if len(content) > max_content_size:
                        raise ContentTooLargeException(
                            "Content exceeded maximum size",
                            size=len(content),
                            max_size=max_content_size,
                            details={'url': url}
                        )

                page_html = content.decode('utf-8', errors='ignore')

                # Extract and convert content
                soup = BeautifulSoup(page_html, 'html.parser')
                page_title = soup.title.string if soup.title else url
                page_title = re.sub(r'\|.*$| - .*$', '', page_title).strip()

                main_content_html = extract_main_content(page_html)

                if main_content_html:
                    markdown_content = convert_html_to_markdown(main_content_html)

                    full_documentation += f"## {page_title}\n\n"
                    full_documentation += f"**Original Page:** `{url}`\n\n"
                    full_documentation += markdown_content
                    full_documentation += "\n\n---\n\n"

                    pages_processed += 1
                else:
                    logger.warning(f"No main content found on {url}")

            except ContentTooLargeException as e:
                logger.error(f"Content too large for {url}: {e}")
                pages_failed += 1
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to process {url}: {e}")
                pages_failed += 1
            except Exception as e:
                logger.error(f"Unexpected error processing {url}: {e}", exc_info=True)
                pages_failed += 1

        # Generate output filename and path
        output_filename = generate_filename_from_url(base_url, config)
        output_path = Path(output_dir) / output_filename

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write documentation to file
        encoding = config.get('output.encoding', 'utf-8')
        with open(output_path, 'w', encoding=encoding) as f:
            f.write(full_documentation)

        logger.info(
            f"Scrape complete: {pages_processed} pages processed, "
            f"{pages_failed} failed. Saved to: {output_path}"
        )

        # Log rate limiting statistics
        if config.get('rate_limiting.enabled', True):
            stats = rate_limiter.get_stats()
            logger.info(f"Rate limiting statistics: {stats}")

        return str(output_path)
