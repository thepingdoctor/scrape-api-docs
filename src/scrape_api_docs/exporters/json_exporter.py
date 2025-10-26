"""JSON export converter for structured data output."""

import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup

from .base import ExportConverter, ExportOptions, ExportResult, PageResult

logger = logging.getLogger(__name__)


class JSONExportConverter(ExportConverter):
    """
    JSON export for data processing and API integration.

    Format:
    {
        "metadata": {...},
        "pages": [...],
        "statistics": {...},
        "structure": {...}
    }
    """

    format_name = "json"
    file_extension = ".json"
    mime_type = "application/json"

    async def convert(
        self,
        pages: List[PageResult],
        output_path: Path,
        options: ExportOptions
    ) -> ExportResult:
        """Generate structured JSON."""
        start_time = time.time()

        try:
            # Build JSON structure
            data = {
                'metadata': self._extract_metadata(pages, options),
                'pages': [self._page_to_dict(page) for page in pages],
                'statistics': self._calculate_statistics(pages),
                'structure': self._extract_structure(pages),
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'version': '2.0.0',
                    'format': 'json',
                    'exporter': 'scrape-api-docs'
                }
            }

            # Write JSON file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            duration = time.time() - start_time

            return ExportResult(
                format=self.format_name,
                output_path=output_path,
                size_bytes=output_path.stat().st_size,
                duration=duration,
                page_count=len(pages),
                success=True,
                metadata={
                    'total_pages': len(pages),
                    'total_size': output_path.stat().st_size
                }
            )

        except Exception as e:
            logger.error(f"JSON export failed: {e}", exc_info=True)
            return ExportResult(
                format=self.format_name,
                success=False,
                error=str(e)
            )

    def _page_to_dict(self, page: PageResult) -> Dict:
        """Convert page to dictionary."""
        soup = BeautifulSoup(page.content, 'html.parser')
        text = soup.get_text(strip=True)

        return {
            'url': page.url,
            'title': page.title,
            'content': {
                'markdown': page.content if page.format == 'markdown' else None,
                'html': page.content if page.format == 'html' else None,
                'text': text
            },
            'structure': {
                'headings': self._extract_headings(soup),
                'links': self._extract_links(soup),
                'images': self._extract_images(soup),
                'code_blocks': self._extract_code_blocks(soup),
                'tables': len(soup.find_all('table'))
            },
            'metadata': {
                'word_count': len(text.split()),
                'character_count': len(text),
                'heading_count': len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
                'link_count': len(soup.find_all('a')),
                'image_count': len(soup.find_all('img')),
                'render_time': page.render_time,
                'cached': page.from_cache,
                **page.metadata
            }
        }

    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract all headings with hierarchy."""
        headings = []
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            headings.append({
                'level': int(heading.name[1]),
                'text': heading.get_text(strip=True),
                'id': heading.get('id', '')
            })
        return headings

    def _extract_links(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract all links."""
        links = []
        for link in soup.find_all('a', href=True):
            links.append({
                'text': link.get_text(strip=True),
                'href': link['href'],
                'title': link.get('title', '')
            })
        return links

    def _extract_images(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract all images."""
        images = []
        for img in soup.find_all('img'):
            images.append({
                'src': img.get('src', ''),
                'alt': img.get('alt', ''),
                'title': img.get('title', '')
            })
        return images

    def _extract_code_blocks(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract code blocks with language detection."""
        code_blocks = []
        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code:
                # Try to detect language from class
                language = ''
                classes = code.get('class', [])
                for cls in classes:
                    if cls.startswith('language-') or cls.startswith('lang-'):
                        language = cls.split('-', 1)[1]
                        break

                code_blocks.append({
                    'language': language,
                    'code': code.get_text(),
                    'line_count': len(code.get_text().splitlines())
                })
        return code_blocks

    def _extract_metadata(
        self,
        pages: List[PageResult],
        options: ExportOptions
    ) -> Dict[str, Any]:
        """Extract metadata from pages and options."""
        return {
            'title': options.title or 'Documentation',
            'author': options.author,
            'source_url': options.source_url or (pages[0].url if pages else None),
            'generated_at': datetime.now().isoformat(),
            'total_pages': len(pages),
            'options': {
                'include_metadata': options.include_metadata,
                'include_toc': options.include_toc
            }
        }

    def _calculate_statistics(self, pages: List[PageResult]) -> Dict[str, Any]:
        """Calculate statistics across all pages."""
        total_words = 0
        total_chars = 0
        total_headings = 0
        total_links = 0
        total_images = 0
        total_code_blocks = 0
        total_tables = 0
        total_render_time = 0.0

        for page in pages:
            soup = BeautifulSoup(page.content, 'html.parser')
            text = soup.get_text(strip=True)

            total_words += len(text.split())
            total_chars += len(text)
            total_headings += len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
            total_links += len(soup.find_all('a'))
            total_images += len(soup.find_all('img'))
            total_code_blocks += len(soup.find_all('pre'))
            total_tables += len(soup.find_all('table'))
            total_render_time += page.render_time

        avg_words_per_page = total_words / len(pages) if pages else 0
        avg_render_time = total_render_time / len(pages) if pages else 0

        return {
            'totals': {
                'pages': len(pages),
                'words': total_words,
                'characters': total_chars,
                'headings': total_headings,
                'links': total_links,
                'images': total_images,
                'code_blocks': total_code_blocks,
                'tables': total_tables
            },
            'averages': {
                'words_per_page': round(avg_words_per_page, 2),
                'render_time': round(avg_render_time, 3)
            },
            'performance': {
                'total_render_time': round(total_render_time, 3),
                'cached_pages': sum(1 for p in pages if p.from_cache)
            }
        }

    def _extract_structure(self, pages: List[PageResult]) -> Dict[str, Any]:
        """Extract document structure."""
        hierarchy = self._build_hierarchy(pages)

        return {
            'total_pages': len(pages),
            'hierarchy': hierarchy,
            'navigation': self._extract_navigation(pages),
            'depth': self._calculate_depth(hierarchy)
        }

    def _build_hierarchy(self, pages: List[PageResult]) -> List[Dict]:
        """Build page hierarchy based on URLs."""
        hierarchy = []

        for page in pages:
            from urllib.parse import urlparse
            parsed = urlparse(page.url)
            path_parts = [p for p in parsed.path.split('/') if p]

            hierarchy.append({
                'url': page.url,
                'title': page.title,
                'depth': len(path_parts),
                'path': path_parts
            })

        return hierarchy

    def _extract_navigation(self, pages: List[PageResult]) -> List[Dict]:
        """Extract navigation structure."""
        nav_items = []

        for page in pages:
            soup = BeautifulSoup(page.content, 'html.parser')

            # Find main headings as navigation points
            main_headings = soup.find_all(['h1', 'h2'])

            nav_items.append({
                'page_url': page.url,
                'page_title': page.title,
                'sections': [
                    {
                        'level': int(h.name[1]),
                        'title': h.get_text(strip=True),
                        'id': h.get('id', '')
                    }
                    for h in main_headings
                ]
            })

        return nav_items

    def _calculate_depth(self, hierarchy: List[Dict]) -> int:
        """Calculate maximum depth in hierarchy."""
        if not hierarchy:
            return 0
        return max(item['depth'] for item in hierarchy)
