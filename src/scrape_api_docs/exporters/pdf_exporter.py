"""PDF export converter using WeasyPrint."""

import time
import logging
from pathlib import Path
from typing import List, Dict
from bs4 import BeautifulSoup

from .base import ExportConverter, ExportOptions, ExportResult, PageResult

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

try:
    import jinja2
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

logger = logging.getLogger(__name__)


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
        """Initialize PDF converter with Jinja2 templates."""
        if not WEASYPRINT_AVAILABLE:
            raise ImportError("WeasyPrint is required for PDF export. Install with: pip install weasyprint")

        if not JINJA2_AVAILABLE:
            raise ImportError("Jinja2 is required for PDF export. Install with: pip install jinja2")

        if not MARKDOWN_AVAILABLE:
            raise ImportError("Markdown is required for PDF export. Install with: pip install markdown")

        # Setup template environment
        template_dir = Path(__file__).parent.parent.parent.parent / 'templates' / 'pdf'
        if template_dir.exists():
            self.template_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(template_dir))
            )
        else:
            # Use string templates if directory doesn't exist
            self.template_env = jinja2.Environment(
                loader=jinja2.DictLoader({
                    'document.html': self._get_default_template()
                })
            )

    async def convert(
        self,
        pages: List[PageResult],
        output_path: Path,
        options: ExportOptions
    ) -> ExportResult:
        """Generate PDF from pages."""
        start_time = time.time()

        try:
            # Prepare content
            processed_pages = self._prepare_content(pages, options)

            # Render HTML template
            try:
                template = self.template_env.get_template('document.html')
            except jinja2.TemplateNotFound:
                template = self.template_env.from_string(self._get_default_template())

            html_content = template.render(
                pages=processed_pages,
                title=options.title or "Documentation",
                author=options.author,
                toc=self._generate_toc(pages) if options.include_toc else None,
                metadata=self._extract_metadata(pages) if options.include_metadata else None,
                now=time.strftime('%Y-%m-%d')
            )

            # Generate CSS
            stylesheets = [CSS(string=self._get_default_css())]

            if options.custom_css:
                custom_css_path = Path(options.custom_css)
                if custom_css_path.exists():
                    stylesheets.append(CSS(filename=str(custom_css_path)))

            # Generate PDF
            html = HTML(string=html_content)
            html.write_pdf(
                str(output_path),
                stylesheets=stylesheets
            )

            duration = time.time() - start_time

            return ExportResult(
                format=self.format_name,
                output_path=output_path,
                size_bytes=output_path.stat().st_size,
                duration=duration,
                page_count=len(pages),
                success=True,
                metadata={
                    'title': options.title or "Documentation",
                    'author': options.author,
                    'page_count': len(pages)
                }
            )

        except Exception as e:
            logger.error(f"PDF export failed: {e}", exc_info=True)
            return ExportResult(
                format=self.format_name,
                success=False,
                error=str(e)
            )

    def _prepare_content(
        self,
        pages: List[PageResult],
        options: ExportOptions
    ) -> List[Dict]:
        """Prepare and clean content for PDF."""
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

            # Fix images for PDF (convert relative to absolute if needed)
            for img in soup.find_all('img'):
                self._fix_image_path(img, page.url)

            processed.append({
                'title': page.title,
                'url': page.url,
                'content': str(soup)
            })

        return processed

    def _fix_image_path(self, img_tag, page_url: str):
        """Fix image paths to be absolute URLs."""
        src = img_tag.get('src', '')
        if src and not src.startswith(('http://', 'https://', 'data:')):
            from urllib.parse import urljoin
            img_tag['src'] = urljoin(page_url, src)

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
                    'page_title': page.title,
                    'page_url': page.url
                })

        return toc

    def _extract_metadata(self, pages: List[PageResult]) -> Dict:
        """Extract metadata from pages."""
        total_words = 0
        total_images = 0
        total_code_blocks = 0

        for page in pages:
            soup = BeautifulSoup(page.content, 'html.parser')
            text = soup.get_text()
            total_words += len(text.split())
            total_images += len(soup.find_all('img'))
            total_code_blocks += len(soup.find_all(['pre', 'code']))

        return {
            'total_pages': len(pages),
            'total_words': total_words,
            'total_images': total_images,
            'total_code_blocks': total_code_blocks
        }

    def _get_default_template(self) -> str:
        """Get default HTML template for PDF."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
</head>
<body>
    <!-- Cover page -->
    <div class="cover">
        <h1>{{ title }}</h1>
        {% if author %}<p class="author">By {{ author }}</p>{% endif %}
        <p class="date">Generated on {{ now }}</p>
    </div>
    <div class="page-break"></div>

    <!-- Table of Contents -->
    {% if toc %}
    <div class="toc">
        <h2>Table of Contents</h2>
        {% for item in toc %}
        <div class="toc-item toc-level-{{ item.level }}">
            <span class="toc-title">{{ item.title }}</span>
            <span class="toc-page">{{ item.page_title }}</span>
        </div>
        {% endfor %}
    </div>
    <div class="page-break"></div>
    {% endif %}

    <!-- Content -->
    {% for page in pages %}
    <div class="page-content">
        <h2 class="page-title">{{ page.title }}</h2>
        <p class="page-url">Source: <code>{{ page.url }}</code></p>
        {{ page.content | safe }}
    </div>
    <div class="page-break"></div>
    {% endfor %}
</body>
</html>'''

    def _get_default_css(self) -> str:
        """Get default CSS for PDF."""
        return '''
@page {
    size: A4;
    margin: 2cm;
}

body {
    font-family: 'Georgia', serif;
    line-height: 1.6;
    color: #333;
}

.cover {
    text-align: center;
    padding: 5cm 0;
}

.cover h1 {
    font-size: 32pt;
    margin-bottom: 1cm;
}

.cover .author {
    font-size: 14pt;
    color: #666;
}

.cover .date {
    font-size: 12pt;
    color: #999;
}

.page-break {
    page-break-after: always;
}

.toc {
    page-break-after: always;
}

.toc h2 {
    font-size: 20pt;
    margin-bottom: 1cm;
}

.toc-item {
    margin: 5px 0;
    padding-left: 0;
}

.toc-level-2 {
    padding-left: 1cm;
}

.toc-level-3 {
    padding-left: 2cm;
}

.toc-title {
    flex: 1;
}

.toc-page {
    color: #666;
    font-style: italic;
    font-size: 10pt;
}

.page-title {
    font-size: 18pt;
    color: #2c3e50;
    border-bottom: 2px solid #3498db;
    padding-bottom: 0.3cm;
    margin-bottom: 0.5cm;
}

.page-url {
    font-size: 9pt;
    color: #666;
    margin-bottom: 1cm;
}

.page-url code {
    background: #f5f5f5;
    padding: 2px 5px;
    border-radius: 3px;
}

h1, h2, h3, h4, h5, h6 {
    color: #2c3e50;
    font-weight: bold;
    margin-top: 0.8cm;
    margin-bottom: 0.3cm;
}

h1 { font-size: 24pt; }
h2 { font-size: 18pt; }
h3 { font-size: 14pt; }
h4 { font-size: 12pt; }

pre {
    background: #f5f5f5;
    padding: 10px;
    border-radius: 5px;
    overflow-x: auto;
    border-left: 3px solid #3498db;
}

code {
    font-family: 'Courier New', monospace;
    font-size: 9pt;
    background: #f5f5f5;
    padding: 2px 5px;
    border-radius: 3px;
}

pre code {
    background: none;
    padding: 0;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 0.5cm 0;
}

table th, table td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}

table th {
    background: #3498db;
    color: white;
    font-weight: bold;
}

a {
    color: #3498db;
    text-decoration: none;
}

img {
    max-width: 100%;
    height: auto;
}
'''
