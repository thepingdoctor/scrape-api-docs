"""
Async documentation scraper with JavaScript rendering support.

This module extends the original scraper with async capabilities and
automatic JavaScript rendering for SPA sites.
"""

import asyncio
import logging
import re
from urllib.parse import urljoin, urlparse
from collections import deque
from typing import Set, List, Optional

from bs4 import BeautifulSoup
import markdownify

from .hybrid_renderer import HybridRenderer

logger = logging.getLogger(__name__)


class AsyncDocScraper:
    """
    Async documentation scraper with intelligent rendering.

    Features:
    - Async crawling for better performance
    - Automatic SPA detection and JavaScript rendering
    - Rate limiting and caching
    - Concurrent page processing
    """

    def __init__(
        self,
        force_javascript: bool = False,
        auto_detect: bool = True,
        max_concurrent: int = 5,
        timeout: int = 30,
    ):
        """
        Initialize async scraper.

        Args:
            force_javascript: Always use JavaScript rendering
            auto_detect: Auto-detect if JavaScript needed
            max_concurrent: Maximum concurrent page fetches
            timeout: Request timeout in seconds
        """
        self.force_javascript = force_javascript
        self.auto_detect = auto_detect
        self.max_concurrent = max_concurrent
        self.timeout = timeout

        self.renderer: Optional[HybridRenderer] = None

    async def __aenter__(self):
        """Initialize renderer on context entry."""
        self.renderer = HybridRenderer(
            force_javascript=self.force_javascript,
            auto_detect=self.auto_detect,
        )
        await self.renderer.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup renderer on context exit."""
        if self.renderer:
            await self.renderer.__aexit__(exc_type, exc_val, exc_tb)

    async def get_all_site_links(self, base_url: str) -> List[str]:
        """
        Crawl website to find all unique internal pages.

        Args:
            base_url: Starting URL of the documentation site

        Returns:
            Sorted list of unique absolute URLs
        """
        to_visit = deque([base_url])
        visited: Set[str] = {base_url}
        all_links: Set[str] = {base_url}

        base_netloc = urlparse(base_url).netloc
        base_path = urlparse(base_url).path

        logger.info(f"Crawling {base_url} to find all pages...")

        while to_visit:
            current_url = to_visit.popleft()

            try:
                # Render page
                result = await self.renderer.render(current_url)

                if result.error:
                    logger.warning(f"Error crawling {current_url}: {result.error}")
                    continue

                logger.info(
                    f"Visited: {current_url} "
                    f"(js={result.rendered_with_javascript})"
                )

                # Parse HTML for links
                soup = BeautifulSoup(result.html, 'html.parser')

                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    absolute_link = urljoin(current_url, href)

                    # Clean URL (remove query params and fragments)
                    parsed_link = urlparse(absolute_link)
                    clean_link = parsed_link._replace(query="", fragment="").geturl()

                    # Check if link is internal and not yet visited
                    if (
                        urlparse(clean_link).netloc == base_netloc
                        and urlparse(clean_link).path.startswith(base_path)
                        and clean_link not in visited
                    ):
                        visited.add(clean_link)
                        all_links.add(clean_link)
                        to_visit.append(clean_link)

            except Exception as e:
                logger.error(f"Unexpected error crawling {current_url}: {e}")

        logger.info(f"Found {len(all_links)} unique pages")
        return sorted(list(all_links))

    async def scrape_page(self, url: str) -> dict:
        """
        Scrape a single page and extract content.

        Args:
            url: URL to scrape

        Returns:
            Dictionary with page data (title, content, url, etc.)
        """
        try:
            # Render page
            result = await self.renderer.render(url)

            if result.error:
                logger.error(f"Failed to render {url}: {result.error}")
                return {
                    'url': url,
                    'title': '',
                    'markdown': '',
                    'error': result.error,
                }

            # Parse HTML
            soup = BeautifulSoup(result.html, 'html.parser')

            # Extract title
            title = soup.title.string if soup.title else url
            # Clean title (remove site suffix)
            title = re.sub(r'\|.*$| - .*$', '', title).strip()

            # Extract main content
            main_content_html = self._extract_main_content(soup)

            if not main_content_html:
                logger.warning(f"No main content found on {url}")
                markdown = ''
            else:
                # Convert to markdown
                markdown = markdownify.markdownify(
                    main_content_html,
                    heading_style="ATX",
                    bullets="*"
                )

            return {
                'url': url,
                'title': title,
                'markdown': markdown,
                'rendered_with_js': result.rendered_with_javascript,
                'render_time': result.render_time,
            }

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {
                'url': url,
                'title': '',
                'markdown': '',
                'error': str(e),
            }

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main documentation content from page.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Main content HTML string
        """
        # Try common selectors for doc content
        selectors = [
            'main',
            'article',
            '.main-content',
            '#content',
            '.content',
            '.documentation',
            '.markdown-body',
        ]

        for selector in selectors:
            if selector.startswith('.') or selector.startswith('#'):
                # CSS selector
                element = soup.select_one(selector)
            else:
                # Tag name
                element = soup.find(selector)

            if element:
                return str(element)

        # Fallback: return full body
        body = soup.find('body')
        return str(body) if body else ''

    async def scrape_site(
        self,
        base_url: str,
        output_file: Optional[str] = None,
    ) -> str:
        """
        Scrape entire documentation site and combine into markdown.

        Args:
            base_url: Base URL of documentation site
            output_file: Output file path (auto-generated if None)

        Returns:
            Path to output markdown file
        """
        logger.info(f"Starting scrape for: {base_url}")

        # Find all pages
        all_page_urls = await self.get_all_site_links(base_url)

        # Scrape pages concurrently
        logger.info(f"Scraping {len(all_page_urls)} pages...")
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def scrape_with_semaphore(url):
            async with semaphore:
                return await self.scrape_page(url)

        tasks = [scrape_with_semaphore(url) for url in all_page_urls]
        page_data_list = await asyncio.gather(*tasks)

        # Combine into single markdown document
        full_documentation = self._combine_pages(base_url, page_data_list)

        # Generate output filename
        if output_file is None:
            output_file = self._generate_filename(base_url)

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(full_documentation)

        logger.info(f"Success! Documentation saved to: {output_file}")

        # Log statistics
        stats = self.renderer.get_stats()
        logger.info(
            f"Render stats: "
            f"total={stats['total_renders']}, "
            f"static={stats['static_renders']}, "
            f"js={stats['js_renders']}, "
            f"auto_switches={stats['auto_switches']}"
        )

        return output_file

    def _combine_pages(self, base_url: str, page_data_list: List[dict]) -> str:
        """
        Combine scraped pages into single markdown document.

        Args:
            base_url: Base URL
            page_data_list: List of page data dictionaries

        Returns:
            Combined markdown string
        """
        # Generate title
        parsed = urlparse(base_url)
        main_title = " ".join(
            part.capitalize()
            for part in parsed.path.strip('/').split('/')
        )
        if not main_title:
            main_title = parsed.netloc

        # Start document
        doc = f"# Documentation for {main_title}\n"
        doc += f"**Source:** {base_url}\n\n"

        # Add pages
        for page_data in page_data_list:
            if page_data.get('error'):
                doc += f"## {page_data['title'] or 'Error'}\n\n"
                doc += f"**Original Page:** `{page_data['url']}`\n\n"
                doc += f"**Error:** {page_data['error']}\n\n"
                doc += "---\n\n"
                continue

            if not page_data['markdown']:
                continue

            doc += f"## {page_data['title']}\n\n"
            doc += f"**Original Page:** `{page_data['url']}`\n\n"

            # Add render info if JavaScript was used
            if page_data.get('rendered_with_js'):
                doc += f"*Rendered with JavaScript (took {page_data['render_time']:.2f}s)*\n\n"

            doc += page_data['markdown']
            doc += "\n\n---\n\n"

        return doc

    def _generate_filename(self, base_url: str) -> str:
        """
        Generate output filename from URL.

        Args:
            base_url: Base URL

        Returns:
            Sanitized filename
        """
        parsed = urlparse(base_url)
        path_part = parsed.path.strip('/').replace('/', '_')
        domain_part = parsed.netloc.replace(".", "_")

        if not path_part:
            return f"{domain_part}_documentation.md"

        return f"{domain_part}_{path_part}_documentation.md"


# Convenience function
async def scrape_documentation(
    base_url: str,
    force_javascript: bool = False,
    auto_detect: bool = True,
    output_file: Optional[str] = None,
) -> str:
    """
    Scrape documentation site (convenience function).

    Args:
        base_url: Base URL of documentation
        force_javascript: Always use JavaScript rendering
        auto_detect: Auto-detect SPA sites
        output_file: Output file path

    Returns:
        Path to output file
    """
    async with AsyncDocScraper(
        force_javascript=force_javascript,
        auto_detect=auto_detect,
    ) as scraper:
        return await scraper.scrape_site(base_url, output_file)
