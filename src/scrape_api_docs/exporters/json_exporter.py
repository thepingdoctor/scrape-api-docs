"""JSON export converter for LLM-optimized structured data output."""

import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from .base import ExportConverter, ExportOptions, ExportResult, PageResult
from .content_parser import ContentParser
from .api_detector import APIDetector

logger = logging.getLogger(__name__)


class JSONExportConverter(ExportConverter):
    """
    JSON export optimized for LLM context and data processing.

    Format:
    {
        "metadata": {...},
        "pages": [
            {
                "id": "page_001",
                "url": "...",
                "title": "...",
                "description": "...",
                "sections": [...],
                "quick_reference": {...},
                "links": {...},
                "metadata": {...}
            }
        ],
        "global_index": {...},
        "statistics": {...}
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
        """Generate LLM-optimized structured JSON."""
        start_time = time.time()

        try:
            # Process pages
            processed_pages = []
            all_endpoints = []
            all_code_languages = set()
            
            for idx, page in enumerate(pages):
                # Parse content
                parser = ContentParser(base_url=page.url)
                parsed = parser.parse_content(page.content)
                
                # Detect API endpoints
                api_detector = APIDetector()
                page_endpoints = []
                for section in parsed['sections']:
                    endpoints = api_detector.extract_api_endpoints(section)
                    page_endpoints.extend(endpoints)
                    all_endpoints.extend(endpoints)
                
                # Collect code languages
                languages = self._collect_languages(parsed['sections'])
                all_code_languages.update(languages)
                
                # Build quick reference
                quick_ref = self._build_quick_reference(parsed['sections'], page_endpoints)
                
                # Calculate metadata
                page_text = self._extract_all_text(parsed['sections'])
                estimated_tokens = parser.estimate_tokens(page_text)
                
                # Build page structure
                page_data = {
                    'id': f'page_{idx + 1:03d}',
                    'url': page.url,
                    'title': page.title,
                    'description': parsed['description'],
                    'sections': parsed['sections'],
                    'quick_reference': quick_ref,
                    'links': parsed['links'],
                    'metadata': {
                        'word_count': len(page_text.split()),
                        'character_count': len(page_text),
                        'estimated_tokens': estimated_tokens,
                        'section_count': len(parsed['sections']),
                        'code_example_count': quick_ref['code_example_count'],
                        'api_endpoint_count': len(page_endpoints),
                        'render_time': page.render_time,
                        'cached': page.from_cache,
                        **page.metadata
                    }
                }
                
                processed_pages.append(page_data)
            
            # Build global index
            global_index = self._build_global_index(
                all_endpoints,
                all_code_languages,
                processed_pages
            )
            
            # Build complete structure
            data = {
                'metadata': self._build_metadata(pages, options),
                'pages': processed_pages,
                'global_index': global_index,
                'statistics': self._calculate_statistics(processed_pages),
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'version': '3.0.0',
                    'format': 'json',
                    'exporter': 'scrape-api-docs',
                    'optimized_for': 'llm_context'
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
                    'total_size': output_path.stat().st_size,
                    'total_endpoints': len(all_endpoints),
                    'languages': list(all_code_languages)
                }
            )

        except Exception as e:
            logger.error(f"JSON export failed: {e}", exc_info=True)
            return ExportResult(
                format=self.format_name,
                success=False,
                error=str(e)
            )

    def _collect_languages(self, sections: List[Dict[str, Any]]) -> set:
        """Collect all programming languages used in code examples."""
        languages = set()
        
        def collect_from_section(section: Dict[str, Any]):
            for code_block in section.get('code_examples', []):
                lang = code_block.get('language', '')
                if lang and lang != 'plaintext':
                    languages.add(lang)
            
            for subsection in section.get('subsections', []):
                collect_from_section(subsection)
        
        for section in sections:
            collect_from_section(section)
        
        return languages

    def _build_quick_reference(
        self,
        sections: List[Dict[str, Any]],
        endpoints: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build quick reference for easy access to key elements."""
        all_code_examples = []
        key_concepts = []
        
        def extract_from_section(section: Dict[str, Any]):
            # Collect code examples
            for code_block in section.get('code_examples', []):
                all_code_examples.append({
                    'section': section.get('heading', ''),
                    'language': code_block.get('language', ''),
                    'code': code_block.get('code', ''),
                    'title': code_block.get('title', '')
                })
            
            # Extract key concepts (sections with short, meaningful names)
            heading = section.get('heading', '')
            if heading and len(heading) < 100:
                key_concepts.append(heading)
            
            for subsection in section.get('subsections', []):
                extract_from_section(subsection)
        
        for section in sections:
            extract_from_section(section)
        
        return {
            'all_endpoints': endpoints,
            'all_code_examples': all_code_examples,
            'key_concepts': key_concepts,
            'code_example_count': len(all_code_examples)
        }

    def _extract_all_text(self, sections: List[Dict[str, Any]]) -> str:
        """Extract all text content from sections."""
        text_parts = []
        
        def extract_from_section(section: Dict[str, Any]):
            if section.get('content'):
                text_parts.append(section['content'])
            
            for subsection in section.get('subsections', []):
                extract_from_section(subsection)
        
        for section in sections:
            extract_from_section(section)
        
        return ' '.join(text_parts)

    def _build_global_index(
        self,
        all_endpoints: List[Dict[str, Any]],
        all_code_languages: set,
        pages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build global index across all pages."""
        # Group endpoints by resource
        api_detector = APIDetector()
        categorized_endpoints = api_detector.categorize_endpoints(all_endpoints)
        
        # Extract all topics/concepts
        all_topics = set()
        for page in pages:
            all_topics.update(page['quick_reference']['key_concepts'])
        
        return {
            'total_pages': len(pages),
            'total_endpoints': len(all_endpoints),
            'endpoints_by_resource': categorized_endpoints,
            'code_languages': sorted(list(all_code_languages)),
            'topics': sorted(list(all_topics)),
            'endpoint_methods': self._count_methods(all_endpoints)
        }

    def _count_methods(self, endpoints: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count endpoints by HTTP method."""
        method_counts = {}
        for endpoint in endpoints:
            method = endpoint.get('method', 'UNKNOWN')
            method_counts[method] = method_counts.get(method, 0) + 1
        return method_counts

    def _build_metadata(
        self,
        pages: List[PageResult],
        options: ExportOptions
    ) -> Dict[str, Any]:
        """Build export metadata."""
        return {
            'title': options.title or 'API Documentation',
            'author': options.author,
            'source_url': options.source_url or (pages[0].url if pages else None),
            'generated_at': datetime.now().isoformat(),
            'total_pages': len(pages),
            'export_options': {
                'include_metadata': options.include_metadata,
                'include_toc': options.include_toc
            }
        }

    def _calculate_statistics(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics across all pages."""
        total_words = 0
        total_chars = 0
        total_tokens = 0
        total_sections = 0
        total_code_examples = 0
        total_endpoints = 0
        total_render_time = 0.0
        cached_pages = 0
        
        for page in pages:
            meta = page['metadata']
            total_words += meta.get('word_count', 0)
            total_chars += meta.get('character_count', 0)
            total_tokens += meta.get('estimated_tokens', 0)
            total_sections += meta.get('section_count', 0)
            total_code_examples += meta.get('code_example_count', 0)
            total_endpoints += meta.get('api_endpoint_count', 0)
            total_render_time += meta.get('render_time', 0)
            if meta.get('cached', False):
                cached_pages += 1
        
        page_count = len(pages)
        
        return {
            'totals': {
                'pages': page_count,
                'words': total_words,
                'characters': total_chars,
                'estimated_tokens': total_tokens,
                'sections': total_sections,
                'code_examples': total_code_examples,
                'api_endpoints': total_endpoints
            },
            'averages': {
                'words_per_page': round(total_words / page_count, 2) if page_count else 0,
                'tokens_per_page': round(total_tokens / page_count, 2) if page_count else 0,
                'sections_per_page': round(total_sections / page_count, 2) if page_count else 0,
                'render_time': round(total_render_time / page_count, 3) if page_count else 0
            },
            'performance': {
                'total_render_time': round(total_render_time, 3),
                'cached_pages': cached_pages,
                'cache_hit_rate': round(cached_pages / page_count * 100, 2) if page_count else 0
            }
        }
