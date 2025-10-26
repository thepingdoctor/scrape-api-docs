"""
Scraper Service
===============

Core scraping logic and integration with scraper module.
"""

import asyncio
import logging
from typing import Dict, Any
from urllib.parse import urlparse
import aiohttp

logger = logging.getLogger(__name__)


class ScraperService:
    """
    Service for executing scraping operations.

    Integrates with the core scraper module and provides async interface.
    """

    async def validate_url(self, url: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate URL accessibility and scraping options.

        Args:
            url: URL to validate
            options: Scraping options

        Returns:
            Validation result with recommendations
        """
        warnings = []
        recommendations = {}
        valid = True

        try:
            # Check URL accessibility
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.head(url, timeout=aiohttp.ClientTimeout(total=10), allow_redirects=True) as response:
                        if response.status >= 400:
                            valid = False
                            warnings.append(f"URL returned status code {response.status}")

                        # Check if JavaScript rendering might be needed
                        content_type = response.headers.get('content-type', '')
                        if 'text/html' in content_type and not options.get('render_javascript'):
                            warnings.append(
                                "Site may use JavaScript rendering. Consider enabling render_javascript option."
                            )
                            recommendations['render_javascript'] = True

                except asyncio.TimeoutError:
                    valid = False
                    warnings.append("URL request timed out. Site may be slow or unreachable.")
                except aiohttp.ClientError as e:
                    valid = False
                    warnings.append(f"Unable to connect to URL: {str(e)}")

            # Estimate page count (simple heuristic)
            estimated_pages = self._estimate_page_count(url, options)

            # Estimate duration
            estimated_duration = estimated_pages * 2  # 2 seconds per page estimate

            # Check if rate limit is appropriate
            rate_limit = options.get('rate_limit', 2.0)
            if rate_limit > 5.0:
                warnings.append("High rate limit may overwhelm target server. Consider reducing.")
                recommendations['rate_limit'] = 2.0

            return {
                "valid": valid,
                "estimated_pages": estimated_pages,
                "estimated_duration": estimated_duration,
                "warnings": warnings,
                "recommendations": recommendations
            }

        except Exception as e:
            logger.error(f"Validation failed for {url}: {e}", exc_info=True)
            return {
                "valid": False,
                "warnings": [f"Validation error: {str(e)}"],
                "recommendations": {}
            }

    async def estimate_job(self, url: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate job parameters without execution.

        Args:
            url: URL to scrape
            options: Scraping options

        Returns:
            Estimation results
        """
        page_count = self._estimate_page_count(url, options)
        duration = page_count * 2  # 2 seconds per page
        size_mb = page_count * 0.5  # 0.5 MB per page average

        recommendations = {}

        # Check cache settings
        if not options.get('cache_enabled'):
            recommendations['cache_enabled'] = True
            recommendations['cache_ttl'] = 3600

        # Check depth
        max_depth = options.get('max_depth', 10)
        if max_depth > 20:
            recommendations['max_depth'] = 20
            recommendations['note'] = "Deep crawling can be very slow. Consider reducing max_depth."

        return {
            "page_count": page_count,
            "duration": duration,
            "size_mb": size_mb,
            "recommendations": recommendations
        }

    def _estimate_page_count(self, url: str, options: Dict[str, Any]) -> int:
        """
        Estimate number of pages to scrape.

        Simple heuristic based on max_depth.
        """
        max_depth = options.get('max_depth', 10)

        # Simple estimation: exponential growth with depth
        # But capped at reasonable limits
        estimated = min(max_depth * 10, 500)

        return estimated
