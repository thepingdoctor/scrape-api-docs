"""
Stoplight.io Documentation Scraper
===================================

This module provides functionality to scrape documentation from Stoplight.io hosted sites.
Stoplight is a platform for API documentation that uses dynamic rendering, making it
challenging for traditional scrapers.

Key Features:
- Automatic Stoplight URL detection
- Dynamic content rendering using Playwright (headless browser)
- Intelligent page discovery through navigation tree
- API endpoint and model extraction
- Structured JSON and Markdown output
- Rate limiting and error recovery
- Progress feedback during scraping

Architecture:
- Follows the same pattern as github_scraper.py
- Integrates with existing hybrid_renderer for JavaScript support
- Uses BeautifulSoup for HTML parsing
- Leverages existing config, logging, and security infrastructure

Usage:
    from scrape_api_docs.stoplight_scraper import scrape_stoplight_site

    output_path = scrape_stoplight_site(
        url='https://example.stoplight.io/docs/api',
        output_dir='.',
        max_pages=100,
        output_format='markdown'
    )

Stoplight.io Architecture Notes:
- Uses client-side rendering (React-based)
- Navigation tree typically in a sidebar (class: sl-elements-api, sl-panel)
- Content rendered dynamically based on URL routing
- API models and endpoints in structured format
- Tables of contents generated client-side
"""

import re
import time
import asyncio
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from urllib.parse import urlparse, urljoin
import json

from bs4 import BeautifulSoup
import markdownify

from .config import Config
from .logging_config import get_logger, PerformanceLogger
from .exceptions import (
    ValidationException,
    NetworkException,
    ContentParsingException,
    ScraperException
)
from .security import SecurityValidator
from .user_agents import get_user_agent, UserAgents
from .hybrid_renderer import HybridRenderer


logger = get_logger(__name__)


def is_stoplight_url(url: str) -> bool:
    """
    Check if URL is a Stoplight.io documentation site.

    Stoplight sites can be identified by:
    - Hosted on *.stoplight.io domains
    - Custom domains with Stoplight elements (detected via content)

    Args:
        url: URL to check

    Returns:
        True if URL appears to be a Stoplight site
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)

        # Direct Stoplight domain
        if 'stoplight.io' in parsed.netloc:
            return True

        # Custom domains would need content inspection
        # For now, return False and rely on explicit flag
        return False

    except Exception:
        return False


def parse_stoplight_url(url: str) -> Dict[str, str]:
    """
    Parse Stoplight URL into components (base_url, project, path).

    Stoplight URLs typically follow patterns:
    - https://[workspace].stoplight.io/docs/[project]
    - https://[workspace].stoplight.io/docs/[project]/[section]/[page]

    Args:
        url: Stoplight URL to parse

    Returns:
        Dictionary with keys: base_url, workspace, project, path

    Raises:
        ValidationException: If URL is not a valid Stoplight URL
    """
    if not url:
        raise ValidationException(
            "URL cannot be empty",
            details={'url': url}
        )

    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]

    result = {
        'base_url': f"{parsed.scheme}://{parsed.netloc}",
        'workspace': None,
        'project': None,
        'path': '',
        'full_url': url
    }

    # Extract workspace from subdomain
    if 'stoplight.io' in parsed.netloc:
        subdomain_parts = parsed.netloc.split('.')
        if len(subdomain_parts) >= 3:  # e.g., workspace.stoplight.io
            result['workspace'] = subdomain_parts[0]

    # Extract project and path
    # Expected format: /docs/[project]/[optional/path]
    if len(path_parts) >= 2 and path_parts[0] == 'docs':
        result['project'] = path_parts[1]
        if len(path_parts) > 2:
            result['path'] = '/'.join(path_parts[2:])

    logger.debug(f"Parsed Stoplight URL: {result}")
    return result


async def discover_stoplight_pages(
    base_url: str,
    config: Optional[Config] = None,
    max_pages: int = 100
) -> List[str]:
    """
    Discover all documentation pages on a Stoplight site.

    Strategy:
    1. Load the base URL with JavaScript rendering
    2. Extract navigation links from sidebar/menu
    3. Follow internal links to discover more pages
    4. Use BFS to traverse the documentation tree

    Args:
        base_url: Base URL of the Stoplight documentation
        config: Configuration instance (optional)
        max_pages: Maximum number of pages to discover

    Returns:
        List of discovered page URLs

    Raises:
        NetworkException: If page loading fails
        ContentParsingException: If navigation extraction fails
    """
    if config is None:
        config = Config.load()

    logger.info(f"Starting page discovery for Stoplight site: {base_url}")

    discovered_urls: Set[str] = set()
    to_visit: List[str] = [base_url]
    visited: Set[str] = set()

    base_netloc = urlparse(base_url).netloc
    base_path = urlparse(base_url).path.rstrip('/')

    # Initialize renderer for JavaScript support
    renderer = HybridRenderer(
        force_javascript=True,  # Stoplight requires JS
        auto_detect=False,
        timeout=config.get('javascript.timeout', 30000)
    )

    try:
        await renderer.__aenter__()

        while to_visit and len(discovered_urls) < max_pages:
            current_url = to_visit.pop(0)

            if current_url in visited:
                continue

            visited.add(current_url)

            try:
                logger.info(f"Discovering pages from: {current_url}")

                # Render page with JavaScript
                result = await renderer.render(current_url)

                if result.error:
                    logger.warning(f"Error rendering {current_url}: {result.error}")
                    continue

                discovered_urls.add(current_url)

                # Parse HTML to find navigation links
                soup = BeautifulSoup(result.html, 'html.parser')

                # Stoplight-specific selectors for navigation
                # Common patterns: sl-elements-api, sl-panel, navigation menus
                nav_selectors = [
                    'nav a[href]',
                    '.sl-elements-api a[href]',
                    '.sl-panel a[href]',
                    '[role="navigation"] a[href]',
                    'aside a[href]',
                    '.sidebar a[href]',
                    '.nav-menu a[href]'
                ]

                links_found = 0
                for selector in nav_selectors:
                    nav_links = soup.select(selector)

                    for link in nav_links:
                        href = link.get('href', '')
                        if not href or href.startswith('#'):
                            continue

                        # Convert to absolute URL
                        absolute_url = urljoin(current_url, href)
                        parsed_link = urlparse(absolute_url)

                        # Remove fragments and query params
                        clean_url = f"{parsed_link.scheme}://{parsed_link.netloc}{parsed_link.path}"

                        # Only include URLs from same domain and base path
                        if (parsed_link.netloc == base_netloc and
                            parsed_link.path.startswith(base_path) and
                            clean_url not in discovered_urls and
                            clean_url not in visited):

                            to_visit.append(clean_url)
                            links_found += 1

                logger.debug(f"Found {links_found} new links on {current_url}")

                # Rate limiting - be polite
                await asyncio.sleep(config.get('scraper.politeness_delay', 1.0))

            except Exception as e:
                logger.error(f"Error discovering pages from {current_url}: {e}")
                continue

        logger.info(f"Page discovery complete: found {len(discovered_urls)} pages")
        return sorted(list(discovered_urls))

    finally:
        await renderer.__aexit__(None, None, None)


async def scrape_stoplight_page(
    url: str,
    config: Optional[Config] = None,
    renderer: Optional[HybridRenderer] = None
) -> Dict[str, any]:
    """
    Scrape a single Stoplight documentation page.

    Extracts:
    - Page title
    - Main content
    - API endpoints (if present)
    - Models/schemas (if present)
    - Code examples

    Args:
        url: URL of the page to scrape
        config: Configuration instance (optional)
        renderer: Hybrid renderer instance (optional, created if not provided)

    Returns:
        Dictionary with page data: {url, title, content, api_data, metadata}

    Raises:
        NetworkException: If page loading fails
        ContentParsingException: If content extraction fails
    """
    if config is None:
        config = Config.load()

    should_close_renderer = False
    if renderer is None:
        renderer = HybridRenderer(
            force_javascript=True,
            auto_detect=False,
            timeout=config.get('javascript.timeout', 30000)
        )
        await renderer.__aenter__()
        should_close_renderer = True

    try:
        logger.info(f"Scraping Stoplight page: {url}")

        # Render page
        result = await renderer.render(url)

        if result.error:
            raise NetworkException(
                f"Failed to render page: {result.error}",
                url=url
            )

        # Parse HTML
        soup = BeautifulSoup(result.html, 'html.parser')

        # Extract title
        title = soup.title.string if soup.title else ''
        title = re.sub(r'\|.*$| - .*$', '', title).strip()

        # Extract main content
        # Stoplight typically uses specific containers
        content_selectors = [
            'main',
            '.sl-elements-api',
            'article',
            '[role="main"]',
            '.content',
            '.documentation-content'
        ]

        main_content_html = ''
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                main_content_html = str(element)
                break

        if not main_content_html:
            logger.warning(f"No main content found on {url}, using body")
            body = soup.find('body')
            main_content_html = str(body) if body else ''

        # Convert to Markdown
        markdown_content = markdownify.markdownify(
            main_content_html,
            heading_style="ATX",
            bullets="*"
        ) if main_content_html else ''

        # Extract API-specific data (endpoints, models)
        api_data = extract_api_elements(soup)

        # Build page data
        page_data = {
            'url': url,
            'title': title,
            'markdown': markdown_content,
            'api_endpoints': api_data.get('endpoints', []),
            'api_models': api_data.get('models', []),
            'code_examples': api_data.get('code_examples', []),
            'metadata': {
                'render_time': result.render_time,
                'rendered_with_js': result.rendered_with_javascript,
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
            }
        }

        logger.debug(f"Scraped page: {title} ({len(markdown_content)} chars)")
        return page_data

    finally:
        if should_close_renderer and renderer:
            await renderer.__aexit__(None, None, None)


def extract_api_elements(soup: BeautifulSoup) -> Dict[str, List]:
    """
    Extract API-specific elements from Stoplight page.

    Looks for:
    - HTTP endpoints (GET, POST, PUT, DELETE, etc.)
    - Request/response schemas
    - Models and data types
    - Code examples

    Args:
        soup: BeautifulSoup parsed HTML

    Returns:
        Dictionary with lists of endpoints, models, and code examples
    """
    api_data = {
        'endpoints': [],
        'models': [],
        'code_examples': []
    }

    # Extract HTTP endpoints
    # Stoplight typically renders these in specific containers
    endpoint_selectors = [
        '.sl-http-operation',
        '.endpoint',
        '[data-testid*="endpoint"]',
        '.api-endpoint'
    ]

    for selector in endpoint_selectors:
        endpoints = soup.select(selector)
        for endpoint in endpoints:
            method_elem = endpoint.select_one('[class*="method"], [class*="http-method"]')
            path_elem = endpoint.select_one('[class*="path"], [class*="endpoint-path"]')

            if method_elem and path_elem:
                api_data['endpoints'].append({
                    'method': method_elem.get_text(strip=True),
                    'path': path_elem.get_text(strip=True),
                    'description': endpoint.select_one('[class*="description"]').get_text(strip=True)
                        if endpoint.select_one('[class*="description"]') else ''
                })

    # Extract code examples
    code_blocks = soup.select('pre code, .code-example, [class*="code-sample"]')
    for code_block in code_blocks:
        language = ''
        # Try to detect language from class names
        for cls in code_block.get('class', []):
            if cls.startswith('language-') or cls.startswith('lang-'):
                language = cls.split('-', 1)[1]
                break

        api_data['code_examples'].append({
            'language': language,
            'code': code_block.get_text(strip=True)
        })

    # Extract models/schemas
    # These are often in JSON schema format
    schema_selectors = [
        '[class*="schema"]',
        '[class*="model"]',
        '[data-testid*="schema"]'
    ]

    for selector in schema_selectors:
        schemas = soup.select(selector)
        for schema in schemas[:10]:  # Limit to avoid duplication
            schema_name = schema.select_one('[class*="name"], h3, h4')
            if schema_name:
                api_data['models'].append({
                    'name': schema_name.get_text(strip=True),
                    'schema': schema.get_text(strip=True)[:500]  # Limit length
                })

    return api_data


async def scrape_stoplight_site(
    url: str,
    output_dir: str = '.',
    max_pages: int = 100,
    output_format: str = 'markdown',
    config: Optional[Config] = None
) -> str:
    """
    Main function to scrape a Stoplight.io documentation site.

    Complete workflow:
    1. Parse and validate Stoplight URL
    2. Discover all documentation pages
    3. Scrape each page with JavaScript rendering
    4. Extract API elements and content
    5. Combine into structured output (Markdown or JSON)
    6. Save to file

    Args:
        url: Stoplight documentation URL
        output_dir: Output directory for documentation file
        max_pages: Maximum number of pages to scrape
        output_format: Output format ('markdown' or 'json')
        config: Configuration instance (optional)

    Returns:
        Path to the output file

    Raises:
        ValidationException: If URL is invalid
        NetworkException: If scraping fails

    Example:
        >>> output = await scrape_stoplight_site(
        ...     'https://acme.stoplight.io/docs/api',
        ...     output_dir='./docs',
        ...     max_pages=50,
        ...     output_format='markdown'
        ... )
        >>> print(f"Documentation saved to: {output}")
    """
    if config is None:
        config = Config.load()

    # Validate configuration
    config.validate()

    logger.info(f"Starting Stoplight scrape: {url}")

    with PerformanceLogger(logger, "stoplight_scrape", url=url):
        # Parse URL
        parsed = parse_stoplight_url(url)
        workspace = parsed.get('workspace', 'unknown')
        project = parsed.get('project', 'docs')

        logger.info(f"Stoplight workspace: {workspace}, project: {project}")

        # Discover all pages
        try:
            page_urls = await discover_stoplight_pages(url, config, max_pages)
            logger.info(f"Discovered {len(page_urls)} pages to scrape")
        except Exception as e:
            logger.error(f"Page discovery failed: {e}")
            raise NetworkException(
                f"Failed to discover Stoplight pages: {e}",
                url=url
            )

        # Initialize renderer for batch scraping
        renderer = HybridRenderer(
            force_javascript=True,
            auto_detect=False,
            timeout=config.get('javascript.timeout', 30000)
        )

        try:
            await renderer.__aenter__()

            # Scrape all pages
            pages_data = []
            pages_processed = 0
            pages_failed = 0

            for page_url in page_urls:
                try:
                    page_data = await scrape_stoplight_page(page_url, config, renderer)
                    pages_data.append(page_data)
                    pages_processed += 1

                    # Progress feedback
                    if pages_processed % 10 == 0:
                        logger.info(f"Progress: {pages_processed}/{len(page_urls)} pages scraped")

                    # Rate limiting
                    await asyncio.sleep(config.get('scraper.politeness_delay', 1.0))

                except Exception as e:
                    logger.error(f"Failed to scrape {page_url}: {e}")
                    pages_failed += 1
                    continue

            logger.info(
                f"Scraping complete: {pages_processed} pages processed, "
                f"{pages_failed} failed"
            )

        finally:
            await renderer.__aexit__(None, None, None)

        # Generate output based on format
        if output_format == 'json':
            output_path = save_as_json(pages_data, output_dir, workspace, project, config)
        else:  # markdown (default)
            output_path = save_as_markdown(pages_data, output_dir, workspace, project, config)

        logger.info(f"Stoplight scrape complete. Output saved to: {output_path}")
        return output_path


def save_as_markdown(
    pages_data: List[Dict],
    output_dir: str,
    workspace: str,
    project: str,
    config: Config
) -> str:
    """
    Save scraped pages as a single Markdown file.

    Args:
        pages_data: List of page data dictionaries
        output_dir: Output directory
        workspace: Stoplight workspace name
        project: Project name
        config: Configuration instance

    Returns:
        Path to output file
    """
    # Build combined markdown document
    full_documentation = f"# Documentation for {workspace}/{project}\n\n"
    full_documentation += f"**Scraped:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n"
    full_documentation += f"**Total Pages:** {len(pages_data)}\n\n"
    full_documentation += "---\n\n"

    for page_data in pages_data:
        full_documentation += f"## {page_data['title']}\n\n"
        full_documentation += f"**URL:** {page_data['url']}\n\n"

        # Add API endpoints if present
        if page_data.get('api_endpoints'):
            full_documentation += "### API Endpoints\n\n"
            for endpoint in page_data['api_endpoints']:
                full_documentation += f"- **{endpoint['method']}** `{endpoint['path']}`"
                if endpoint.get('description'):
                    full_documentation += f": {endpoint['description']}"
                full_documentation += "\n"
            full_documentation += "\n"

        # Add main content
        full_documentation += page_data['markdown']
        full_documentation += "\n\n---\n\n"

    # Generate output filename
    output_filename = f"{workspace}_{project}_stoplight_documentation.md"

    # Apply security sanitization
    if config.get('security.sanitize_filenames', True):
        output_filename = SecurityValidator.sanitize_filename(output_filename)

    output_path = Path(output_dir) / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to file
    encoding = config.get('output.encoding', 'utf-8')
    with open(output_path, 'w', encoding=encoding) as f:
        f.write(full_documentation)

    return str(output_path)


def save_as_json(
    pages_data: List[Dict],
    output_dir: str,
    workspace: str,
    project: str,
    config: Config
) -> str:
    """
    Save scraped pages as structured JSON.

    Provides LLM-optimized output with:
    - Clear structure
    - API endpoints separated
    - Models and schemas isolated
    - Code examples extracted

    Args:
        pages_data: List of page data dictionaries
        output_dir: Output directory
        workspace: Stoplight workspace name
        project: Project name
        config: Configuration instance

    Returns:
        Path to output file
    """
    # Build structured JSON
    output_data = {
        'metadata': {
            'workspace': workspace,
            'project': project,
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
            'total_pages': len(pages_data),
            'source': 'Stoplight.io'
        },
        'pages': pages_data
    }

    # Generate output filename
    output_filename = f"{workspace}_{project}_stoplight_documentation.json"

    # Apply security sanitization
    if config.get('security.sanitize_filenames', True):
        output_filename = SecurityValidator.sanitize_filename(output_filename)

    output_path = Path(output_dir) / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to file with pretty formatting
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    return str(output_path)


# Synchronous wrapper for compatibility
def scrape_stoplight_site_sync(
    url: str,
    output_dir: str = '.',
    max_pages: int = 100,
    output_format: str = 'markdown',
    config: Optional[Config] = None
) -> str:
    """
    Synchronous wrapper for scrape_stoplight_site.

    For compatibility with existing synchronous code.

    Args:
        url: Stoplight documentation URL
        output_dir: Output directory
        max_pages: Maximum pages to scrape
        output_format: Output format ('markdown' or 'json')
        config: Configuration instance

    Returns:
        Path to output file
    """
    return asyncio.run(
        scrape_stoplight_site(url, output_dir, max_pages, output_format, config)
    )
