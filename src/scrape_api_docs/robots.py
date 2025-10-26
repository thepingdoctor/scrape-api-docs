"""
Robots.txt Compliance Module
============================

This module provides robots.txt parsing and compliance checking to ensure
responsible web scraping that respects website policies.

Features:
- robots.txt parsing and caching
- Crawl-delay detection and respect
- User-agent configuration
- Disallow directive compliance
- Per-domain caching for performance

Usage:
    from scrape_api_docs.robots import RobotsChecker

    checker = RobotsChecker(user_agent="scrape-api-docs/0.1.0")
    allowed, reason = checker.is_allowed("https://example.com/docs")
    if allowed:
        delay = checker.get_crawl_delay("https://example.com/docs")
        # Proceed with scraping, respecting delay
"""

from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from typing import Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class RobotsChecker:
    """
    Check robots.txt compliance for web scraping.

    Implements caching to avoid repeated robots.txt fetches and provides
    crawl delay recommendations based on robots.txt directives.
    """

    def __init__(self, user_agent: str = "scrape-api-docs/0.1.0"):
        """
        Initialize robots.txt checker.

        Args:
            user_agent: User-Agent string to identify the scraper
        """
        self.user_agent = user_agent
        self._cache: Dict[str, RobotFileParser] = {}
        logger.info(f"RobotsChecker initialized with user-agent: {user_agent}")

    def _get_robots_url(self, url: str) -> str:
        """
        Get robots.txt URL for a given page URL.

        Args:
            url: Target page URL

        Returns:
            robots.txt URL for the domain
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def _fetch_robots_parser(self, url: str) -> Optional[RobotFileParser]:
        """
        Fetch and parse robots.txt for a URL.

        Args:
            url: Target URL

        Returns:
            RobotFileParser instance, or None if unavailable
        """
        robots_url = self._get_robots_url(url)

        # Check cache first
        if robots_url in self._cache:
            logger.debug(f"Using cached robots.txt for {robots_url}")
            return self._cache[robots_url]

        # Fetch and parse robots.txt
        rp = RobotFileParser()
        rp.set_url(robots_url)

        try:
            rp.read()
            self._cache[robots_url] = rp
            logger.info(f"Successfully fetched robots.txt from {robots_url}")
            return rp
        except Exception as e:
            # If robots.txt is unavailable, log and allow (be permissive)
            logger.warning(
                f"Could not fetch robots.txt from {robots_url}: {e}. "
                "Allowing scraping (permissive default)."
            )
            # Cache None to avoid repeated failed requests
            self._cache[robots_url] = None
            return None

    def is_allowed(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Check if URL is allowed by robots.txt.

        Args:
            url: Target URL to check

        Returns:
            Tuple of (allowed: bool, reason: Optional[str])
            - allowed: True if scraping is allowed
            - reason: Explanation if blocked, None otherwise
        """
        try:
            rp = self._fetch_robots_parser(url)

            # If robots.txt unavailable, allow (permissive default)
            if rp is None:
                return True, None

            # Check if allowed for our user-agent
            allowed = rp.can_fetch(self.user_agent, url)

            if allowed:
                logger.debug(f"URL allowed by robots.txt: {url}")
                return True, None
            else:
                reason = f"Blocked by robots.txt for user-agent '{self.user_agent}'"
                logger.warning(f"{reason}: {url}")
                return False, reason

        except Exception as e:
            # On error, log and allow (fail-safe)
            logger.error(f"Error checking robots.txt for {url}: {e}")
            return True, None

    def get_crawl_delay(self, url: str) -> float:
        """
        Get recommended crawl delay from robots.txt.

        Args:
            url: Target URL

        Returns:
            Crawl delay in seconds (minimum 1.0 if not specified)
        """
        try:
            rp = self._fetch_robots_parser(url)

            if rp is None:
                # Default to 1 second if robots.txt unavailable
                return 1.0

            # Get crawl delay for our user-agent
            delay = rp.crawl_delay(self.user_agent)

            if delay is not None:
                logger.info(
                    f"Crawl delay from robots.txt for {urlparse(url).netloc}: "
                    f"{delay}s"
                )
                return float(delay)
            else:
                # Default to 1 second if not specified
                logger.debug(
                    f"No crawl delay specified in robots.txt for "
                    f"{urlparse(url).netloc}, using default 1.0s"
                )
                return 1.0

        except Exception as e:
            logger.error(f"Error getting crawl delay for {url}: {e}")
            return 1.0

    def clear_cache(self):
        """Clear the robots.txt cache."""
        self._cache.clear()
        logger.info("Robots.txt cache cleared")

    def get_cached_domains(self) -> list:
        """
        Get list of domains with cached robots.txt.

        Returns:
            List of robots.txt URLs in cache
        """
        return list(self._cache.keys())
