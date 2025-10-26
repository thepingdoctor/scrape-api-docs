# Multi-Format Export Architecture
## PDF, EPUB, JSON, and HTML Export System

**Version:** 2.0.0
**Date:** 2025-10-26
**Status:** Design Phase

---

## Overview

The export system provides multiple output formats for scraped documentation, enabling users to consume content in their preferred format. The architecture is designed to be extensible, allowing easy addition of new export formats.

---

## Supported Export Formats

### 1. Markdown (Existing)
- **Use case**: Version control, plain text editing, GitHub rendering
- **Implementation**: Already implemented with markdownify
- **Status**: Production-ready

### 2. PDF (New)
- **Use case**: Offline reading, printing, archival, distribution
- **Implementation**: WeasyPrint or ReportLab
- **Features**: Table of contents, page numbers, bookmarks, styling

### 3. EPUB (New)
- **Use case**: E-readers (Kindle, Kobo), mobile devices
- **Implementation**: ebooklib
- **Features**: Chapter navigation, metadata, cover image, TOC

### 4. JSON (New)
- **Use case**: Data processing, API integration, analysis
- **Implementation**: Custom structured format
- **Features**: Full metadata, hierarchy, timestamps, statistics

### 5. HTML (New)
- **Use case**: Static site generation, offline browsing
- **Implementation**: Jinja2 templates
- **Features**: Navigation, search, responsive design

---

## Architecture Design

### Export System Components

```
┌──────────────────────────────────────────────┐
│         Export Orchestrator                  │
│  - Format selection                          │
│  - Parallel export generation                │
│  - Result aggregation                        │
└──────────────┬───────────────────────────────┘
               │
   ┌───────────┴────────────┐
   │                        │
   ▼                        ▼
┌─────────────┐      ┌─────────────┐
│  Converter  │      │  Generator  │
│   Factory   │      │   Registry  │
└──────┬──────┘      └──────┬──────┘
       │                    │
       └──────────┬─────────┘
                  │
    ┌─────────────┴─────────────┐
    │                           │
    ▼                           ▼
┌─────────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐
│Markdown │  │ PDF  │  │ EPUB │  │ JSON │  │ HTML │
│Converter│  │Conv. │  │Conv. │  │Conv. │  │Conv. │
└─────────┘  └──────┘  └──────┘  └──────┘  └──────┘
```

### Plugin Architecture
Each export format is implemented as a plugin with common interface:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class ExportOptions:
    """Common export options."""
    include_metadata: bool = True
    include_toc: bool = True
    template: Optional[str] = None
    custom_css: Optional[str] = None
    author: Optional[str] = None
    title: Optional[str] = None

class ExportConverter(ABC):
    """Base class for export converters."""

    format_name: str  # e.g., "pdf", "epub"
    file_extension: str  # e.g., ".pdf", ".epub"
    mime_type: str  # e.g., "application/pdf"

    @abstractmethod
    async def convert(
        self,
        pages: List[PageResult],
        output_path: Path,
        options: ExportOptions
    ) -> ExportResult:
        """
        Convert pages to target format.

        Args:
            pages: List of scraped page results
            output_path: Output file path
            options: Export configuration

        Returns:
            ExportResult with metadata
        """
        pass

    @abstractmethod
    def validate_options(self, options: ExportOptions) -> bool:
        """Validate export options for this format."""
        pass

    def get_capabilities(self) -> Dict[str, Any]:
        """Return converter capabilities."""
        return {
            'format': self.format_name,
            'supports_toc': True,
            'supports_images': True,
            'supports_styling': True
        }
```

---

## PDF Export Implementation

### PDF Generator Architecture

```python
from weasyprint import HTML, CSS
from pathlib import Path
import jinja2

class PDFExportConverter(ExportConverter):
    """
    PDF export using WeasyPrint.

    Features:
    - Professional styling with CSS
    - Table of contents with page numbers
    - Bookmarks for navigation
    - Header/footer with page numbers
    - Syntax highlighting for code blocks
    """

    format_name = "pdf"
    file_extension = ".pdf"
    mime_type = "application/pdf"

    def __init__(self):
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('templates/pdf')
        )

    async def convert(
        self,
        pages: List[PageResult],
        output_path: Path,
        options: ExportOptions
    ) -> ExportResult:
        """Generate PDF from pages."""
        start_time = time.time()

        # Prepare content
        content = self._prepare_content(pages, options)

        # Render HTML template
        template = self.template_env.get_template('document.html')
        html_content = template.render(
            pages=pages,
            title=options.title or "Documentation",
            author=options.author,
            toc=self._generate_toc(pages) if options.include_toc else None,
            metadata=self._extract_metadata(pages) if options.include_metadata else None
        )

        # Load custom CSS
        css_files = [
            'templates/pdf/base.css',
            'templates/pdf/syntax.css',
            'templates/pdf/print.css'
        ]

        if options.custom_css:
            css_files.append(options.custom_css)

        stylesheets = [CSS(filename=css) for css in css_files]

        # Generate PDF
        html = HTML(string=html_content)
        html.write_pdf(
            output_path,
            stylesheets=stylesheets,
            optimize_size=('fonts', 'images')
        )

        duration = time.time() - start_time

        return ExportResult(
            format=self.format_name,
            output_path=output_path,
            size_bytes=output_path.stat().st_size,
            duration=duration,
            page_count=len(pages),
            success=True
        )

    def _prepare_content(
        self,
        pages: List[PageResult],
        options: ExportOptions
    ) -> str:
        """Prepare and clean content for PDF."""
        # Process each page
        processed = []

        for page in pages:
            # Convert Markdown to HTML if needed
            if page.format == 'markdown':
                html = markdown.markdown(
                    page.content,
                    extensions=[
                        'fenced_code',
                        'codehilite',
                        'tables',
                        'toc'
                    ]
                )
            else:
                html = page.content

            # Clean and enhance HTML
            soup = BeautifulSoup(html, 'html.parser')

            # Add syntax highlighting
            for code_block in soup.find_all('pre'):
                self._highlight_code(code_block)

            # Fix images for PDF
            for img in soup.find_all('img'):
                self._fix_image_path(img)

            # Add page breaks
            soup.insert(0, BeautifulSoup(
                '<div class="page-break"></div>',
                'html.parser'
            ))

            processed.append(str(soup))

        return '\n'.join(processed)

    def _generate_toc(self, pages: List[PageResult]) -> List[Dict]:
        """Generate table of contents."""
        toc = []

        for page in pages:
            soup = BeautifulSoup(page.content, 'html.parser')

            # Extract headings
            headings = soup.find_all(['h1', 'h2', 'h3'])

            for heading in headings:
                toc.append({
                    'title': heading.get_text(strip=True),
                    'level': int(heading.name[1]),
                    'id': heading.get('id', ''),
                    'page_url': page.url
                })

        return toc
```

### PDF Templates

**templates/pdf/document.html:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        @page {
            size: A4;
            margin: 2cm;

            @top-center {
                content: "{{ title }}";
                font-size: 10pt;
                color: #666;
            }

            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
            }
        }

        /* Page breaks */
        .page-break {
            page-break-after: always;
        }

        /* TOC */
        .toc {
            page-break-after: always;
        }

        .toc-item {
            margin: 5px 0;
        }

        .toc-item a {
            text-decoration: none;
            color: #333;
        }

        /* Code blocks */
        pre {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }

        code {
            font-family: 'Courier New', monospace;
            font-size: 9pt;
        }
    </style>
</head>
<body>
    <!-- Cover page -->
    <div class="cover">
        <h1>{{ title }}</h1>
        {% if author %}<p>By {{ author }}</p>{% endif %}
        <p>Generated on {{ now().strftime('%Y-%m-%d') }}</p>
    </div>
    <div class="page-break"></div>

    <!-- Table of Contents -->
    {% if toc %}
    <div class="toc">
        <h2>Table of Contents</h2>
        {% for item in toc %}
        <div class="toc-item toc-level-{{ item.level }}">
            <a href="#{{ item.id }}">{{ item.title }}</a>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <!-- Content -->
    {% for page in pages %}
    <div class="page-content">
        <h2>{{ page.title }}</h2>
        <p class="page-url">Source: <code>{{ page.url }}</code></p>
        {{ page.content | safe }}
    </div>
    <div class="page-break"></div>
    {% endfor %}
</body>
</html>
```

---

## EPUB Export Implementation

### EPUB Generator

```python
from ebooklib import epub
import markdown

class EPUBExportConverter(ExportConverter):
    """
    EPUB export using ebooklib.

    Features:
    - Standard EPUB3 format
    - Chapter navigation
    - Embedded metadata
    - Cover image support
    - CSS styling
    """

    format_name = "epub"
    file_extension = ".epub"
    mime_type = "application/epub+zip"

    async def convert(
        self,
        pages: List[PageResult],
        output_path: Path,
        options: ExportOptions
    ) -> ExportResult:
        """Generate EPUB from pages."""
        start_time = time.time()

        # Create EPUB book
        book = epub.EpubBook()

        # Set metadata
        book.set_identifier(f'docs-{hash(pages[0].url)}')
        book.set_title(options.title or 'Documentation')
        book.set_language('en')

        if options.author:
            book.add_author(options.author)

        # Add cover if provided
        if hasattr(options, 'cover_image') and options.cover_image:
            book.set_cover('cover.jpg', open(options.cover_image, 'rb').read())

        # Create chapters
        chapters = []
        spine = ['nav']

        for idx, page in enumerate(pages):
            chapter = self._create_chapter(page, idx)
            book.add_item(chapter)
            chapters.append(chapter)
            spine.append(chapter)

        # Add table of contents
        book.toc = self._generate_toc(chapters)

        # Add navigation files
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Add CSS
        style = self._get_epub_css()
        book.add_item(style)

        # Set spine
        book.spine = spine

        # Write EPUB file
        epub.write_epub(str(output_path), book)

        duration = time.time() - start_time

        return ExportResult(
            format=self.format_name,
            output_path=output_path,
            size_bytes=output_path.stat().st_size,
            duration=duration,
            page_count=len(pages),
            success=True
        )

    def _create_chapter(
        self,
        page: PageResult,
        idx: int
    ) -> epub.EpubHtml:
        """Create EPUB chapter from page."""
        chapter = epub.EpubHtml(
            title=page.title,
            file_name=f'chapter_{idx}.xhtml',
            lang='en'
        )

        # Convert Markdown to HTML
        if page.format == 'markdown':
            content = markdown.markdown(
                page.content,
                extensions=['extra', 'codehilite', 'toc']
            )
        else:
            content = page.content

        # Wrap in EPUB-compatible HTML
        chapter.content = f'''
            <html>
            <head>
                <title>{page.title}</title>
                <link rel="stylesheet" href="style.css" type="text/css"/>
            </head>
            <body>
                <h1>{page.title}</h1>
                <p class="source">Source: <a href="{page.url}">{page.url}</a></p>
                {content}
            </body>
            </html>
        '''

        return chapter

    def _get_epub_css(self) -> epub.EpubItem:
        """Get CSS for EPUB."""
        style = '''
        body {
            font-family: Georgia, serif;
            line-height: 1.6;
            margin: 1em;
        }

        h1, h2, h3, h4 {
            color: #333;
            font-weight: bold;
        }

        code {
            background: #f5f5f5;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }

        pre {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }

        .source {
            font-size: 0.9em;
            color: #666;
            font-style: italic;
        }
        '''

        css = epub.EpubItem(
            uid="style",
            file_name="style.css",
            media_type="text/css",
            content=style
        )

        return css

    def _generate_toc(
        self,
        chapters: List[epub.EpubHtml]
    ) -> List:
        """Generate table of contents."""
        return [
            (chapter, [])
            for chapter in chapters
        ]
```

---

## JSON Export Implementation

### Structured JSON Format

```python
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

        # Build JSON structure
        data = {
            'metadata': self._extract_metadata(pages, options),
            'pages': [self._page_to_dict(page) for page in pages],
            'statistics': self._calculate_statistics(pages),
            'structure': self._extract_structure(pages),
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'version': '2.0.0',
                'format': 'json'
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
            success=True
        )

    def _page_to_dict(self, page: PageResult) -> Dict:
        """Convert page to dictionary."""
        soup = BeautifulSoup(page.content, 'html.parser')

        return {
            'url': page.url,
            'title': page.title,
            'content': {
                'markdown': page.content if page.format == 'markdown' else None,
                'html': page.content if page.format == 'html' else None,
                'text': soup.get_text(strip=True)
            },
            'headings': self._extract_headings(soup),
            'links': self._extract_links(soup),
            'images': self._extract_images(soup),
            'code_blocks': self._extract_code_blocks(soup),
            'metadata': {
                'word_count': len(soup.get_text().split()),
                'render_time': page.render_time,
                'cached': page.from_cache
            }
        }

    def _extract_structure(self, pages: List[PageResult]) -> Dict:
        """Extract document structure."""
        return {
            'total_pages': len(pages),
            'hierarchy': self._build_hierarchy(pages),
            'navigation': self._extract_navigation(pages)
        }
```

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Documentation Export",
  "type": "object",
  "required": ["metadata", "pages", "statistics"],
  "properties": {
    "metadata": {
      "type": "object",
      "properties": {
        "title": {"type": "string"},
        "source_url": {"type": "string"},
        "author": {"type": "string"},
        "generated_at": {"type": "string", "format": "date-time"}
      }
    },
    "pages": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["url", "title", "content"],
        "properties": {
          "url": {"type": "string"},
          "title": {"type": "string"},
          "content": {
            "type": "object",
            "properties": {
              "markdown": {"type": ["string", "null"]},
              "html": {"type": ["string", "null"]},
              "text": {"type": "string"}
            }
          }
        }
      }
    }
  }
}
```

---

## HTML Export Implementation

### Static Site Generator

```python
class HTMLExportConverter(ExportConverter):
    """
    HTML export for offline browsing.

    Features:
    - Responsive design
    - Client-side search
    - Navigation sidebar
    - Syntax highlighting
    """

    format_name = "html"
    file_extension = ".html"
    mime_type = "text/html"

    def __init__(self):
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('templates/html')
        )

    async def convert(
        self,
        pages: List[PageResult],
        output_path: Path,
        options: ExportOptions
    ) -> ExportResult:
        """Generate static HTML site."""
        start_time = time.time()

        # Create output directory structure
        site_dir = output_path.parent / output_path.stem
        site_dir.mkdir(exist_ok=True)
        (site_dir / 'pages').mkdir(exist_ok=True)
        (site_dir / 'assets').mkdir(exist_ok=True)

        # Copy static assets
        self._copy_assets(site_dir / 'assets')

        # Generate index page
        self._generate_index(pages, site_dir, options)

        # Generate individual pages
        for page in pages:
            self._generate_page(page, site_dir, pages, options)

        # Generate search index
        self._generate_search_index(pages, site_dir)

        duration = time.time() - start_time

        return ExportResult(
            format=self.format_name,
            output_path=site_dir,
            size_bytes=self._calculate_dir_size(site_dir),
            duration=duration,
            page_count=len(pages),
            success=True
        )

    def _generate_index(
        self,
        pages: List[PageResult],
        site_dir: Path,
        options: ExportOptions
    ):
        """Generate index.html with navigation."""
        template = self.template_env.get_template('index.html')

        html = template.render(
            title=options.title or 'Documentation',
            pages=pages,
            toc=self._generate_toc(pages)
        )

        (site_dir / 'index.html').write_text(html, encoding='utf-8')

    def _generate_page(
        self,
        page: PageResult,
        site_dir: Path,
        all_pages: List[PageResult],
        options: ExportOptions
    ):
        """Generate individual page HTML."""
        template = self.template_env.get_template('page.html')

        # Convert Markdown to HTML if needed
        if page.format == 'markdown':
            content = markdown.markdown(
                page.content,
                extensions=['extra', 'codehilite', 'toc', 'fenced_code']
            )
        else:
            content = page.content

        html = template.render(
            page=page,
            content=content,
            all_pages=all_pages,
            navigation=self._build_navigation(all_pages, page)
        )

        # Sanitize filename
        filename = self._sanitize_filename(page.title) + '.html'
        (site_dir / 'pages' / filename).write_text(html, encoding='utf-8')

    def _generate_search_index(
        self,
        pages: List[PageResult],
        site_dir: Path
    ):
        """Generate search index for client-side search."""
        search_data = []

        for page in pages:
            soup = BeautifulSoup(page.content, 'html.parser')
            text = soup.get_text(strip=True)

            search_data.append({
                'title': page.title,
                'url': f'pages/{self._sanitize_filename(page.title)}.html',
                'content': text[:500],  # First 500 chars for preview
                'keywords': self._extract_keywords(text)
            })

        (site_dir / 'assets' / 'search-index.json').write_text(
            json.dumps(search_data, indent=2),
            encoding='utf-8'
        )
```

---

## Export Orchestration

### Parallel Export Generation

```python
class ExportOrchestrator:
    """
    Orchestrates multiple export format generation.

    Features:
    - Parallel export generation
    - Error handling per format
    - Progress tracking
    - Result aggregation
    """

    def __init__(self):
        self.converters: Dict[str, ExportConverter] = {
            'markdown': MarkdownExportConverter(),
            'pdf': PDFExportConverter(),
            'epub': EPUBExportConverter(),
            'json': JSONExportConverter(),
            'html': HTMLExportConverter()
        }

    async def generate_exports(
        self,
        pages: List[PageResult],
        base_url: str,
        formats: List[str],
        output_dir: Path,
        options: Optional[Dict[str, ExportOptions]] = None
    ) -> Dict[str, ExportResult]:
        """
        Generate multiple export formats concurrently.

        Args:
            pages: Scraped pages
            base_url: Source URL
            formats: List of format names
            output_dir: Output directory
            options: Per-format options

        Returns:
            Dictionary mapping format to export result
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create tasks for each format
        tasks = []
        for format_name in formats:
            if format_name not in self.converters:
                logger.warning(f"Unknown format: {format_name}")
                continue

            converter = self.converters[format_name]
            output_path = output_dir / f"output{converter.file_extension}"

            format_options = (options or {}).get(
                format_name,
                ExportOptions()
            )

            task = asyncio.create_task(
                converter.convert(pages, output_path, format_options)
            )
            tasks.append((format_name, task))

        # Execute in parallel
        results = {}
        for format_name, task in tasks:
            try:
                result = await task
                results[format_name] = result
                logger.info(
                    f"Export {format_name} completed: "
                    f"{result.size_bytes} bytes in {result.duration:.2f}s"
                )
            except Exception as e:
                logger.error(f"Export {format_name} failed: {e}")
                results[format_name] = ExportResult(
                    format=format_name,
                    success=False,
                    error=str(e)
                )

        return results
```

---

## Configuration & Usage

### Export Options
```python
# Configure export options
export_options = {
    'pdf': ExportOptions(
        title="API Documentation",
        author="Example Corp",
        include_toc=True,
        custom_css="custom.css"
    ),
    'epub': ExportOptions(
        title="API Documentation",
        author="Example Corp",
        cover_image="cover.jpg"
    ),
    'json': ExportOptions(
        include_metadata=True
    )
}

# Generate exports
orchestrator = ExportOrchestrator()
results = await orchestrator.generate_exports(
    pages=scraped_pages,
    base_url="https://docs.example.com",
    formats=['markdown', 'pdf', 'epub', 'json'],
    output_dir=Path('./exports'),
    options=export_options
)
```

---

## Next Steps

1. Implement base ExportConverter interface
2. Create PDF converter with WeasyPrint
3. Build EPUB converter with ebooklib
4. Develop JSON export with structured schema
5. Implement HTML static site generator
6. Create export templates (PDF, HTML)
7. Build ExportOrchestrator for parallel generation
8. Add comprehensive tests for each format
9. Optimize export performance
10. Document usage and configuration
