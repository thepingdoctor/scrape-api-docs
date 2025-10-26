"""HTML export converter for static site generation."""

import time
import json
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from .base import ExportConverter, ExportOptions, ExportResult, PageResult

try:
    import jinja2
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

logger = logging.getLogger(__name__)


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
        """Initialize HTML converter with Jinja2 templates."""
        if not JINJA2_AVAILABLE:
            raise ImportError("Jinja2 is required for HTML export. Install with: pip install jinja2")

        if not MARKDOWN_AVAILABLE:
            raise ImportError("Markdown is required for HTML export. Install with: pip install markdown")

        # Setup template environment
        template_dir = Path(__file__).parent.parent.parent.parent / 'templates' / 'html'
        if template_dir.exists():
            self.template_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(template_dir))
            )
        else:
            # Use string templates if directory doesn't exist
            self.template_env = jinja2.Environment(
                loader=jinja2.DictLoader({
                    'index.html': self._get_index_template(),
                    'page.html': self._get_page_template()
                })
            )

    async def convert(
        self,
        pages: List[PageResult],
        output_path: Path,
        options: ExportOptions
    ) -> ExportResult:
        """Generate static HTML site."""
        start_time = time.time()

        try:
            # Create output directory structure
            site_dir = output_path.parent / output_path.stem
            site_dir.mkdir(exist_ok=True, parents=True)
            (site_dir / 'pages').mkdir(exist_ok=True)
            (site_dir / 'assets').mkdir(exist_ok=True)

            # Copy/create static assets
            self._create_assets(site_dir / 'assets', options)

            # Generate index page
            self._generate_index(pages, site_dir, options)

            # Generate individual pages
            page_files = []
            for page in pages:
                filename = self._generate_page(page, site_dir, pages, options)
                page_files.append(filename)

            # Generate search index
            self._generate_search_index(pages, site_dir, page_files)

            duration = time.time() - start_time

            # Calculate total size
            total_size = sum(
                f.stat().st_size
                for f in site_dir.rglob('*')
                if f.is_file()
            )

            return ExportResult(
                format=self.format_name,
                output_path=site_dir,
                size_bytes=total_size,
                duration=duration,
                page_count=len(pages),
                success=True,
                metadata={
                    'site_directory': str(site_dir),
                    'total_files': len(page_files) + 1,  # +1 for index
                    'has_search': True
                }
            )

        except Exception as e:
            logger.error(f"HTML export failed: {e}", exc_info=True)
            return ExportResult(
                format=self.format_name,
                success=False,
                error=str(e)
            )

    def _generate_index(
        self,
        pages: List[PageResult],
        site_dir: Path,
        options: ExportOptions
    ):
        """Generate index.html with navigation."""
        try:
            template = self.template_env.get_template('index.html')
        except jinja2.TemplateNotFound:
            template = self.template_env.from_string(self._get_index_template())

        # Build navigation tree
        nav_tree = self._build_navigation_tree(pages)

        html = template.render(
            title=options.title or 'Documentation',
            pages=pages,
            navigation=nav_tree,
            toc=self._generate_toc(pages) if options.include_toc else None
        )

        (site_dir / 'index.html').write_text(html, encoding='utf-8')

    def _generate_page(
        self,
        page: PageResult,
        site_dir: Path,
        all_pages: List[PageResult],
        options: ExportOptions
    ) -> str:
        """Generate individual page HTML."""
        try:
            template = self.template_env.get_template('page.html')
        except jinja2.TemplateNotFound:
            template = self.template_env.from_string(self._get_page_template())

        # Convert Markdown to HTML if needed
        if page.format == 'markdown':
            content = markdown.markdown(
                page.content,
                extensions=['extra', 'codehilite', 'toc', 'fenced_code', 'tables']
            )
        else:
            content = page.content

        # Build navigation
        nav_tree = self._build_navigation_tree(all_pages)

        html = template.render(
            page=page,
            content=content,
            all_pages=all_pages,
            navigation=nav_tree,
            title=options.title or 'Documentation'
        )

        # Sanitize filename
        filename = self._sanitize_filename(page.title) + '.html'
        (site_dir / 'pages' / filename).write_text(html, encoding='utf-8')

        return filename

    def _generate_search_index(
        self,
        pages: List[PageResult],
        site_dir: Path,
        page_files: List[str]
    ):
        """Generate search index for client-side search."""
        search_data = []

        for page, filename in zip(pages, page_files):
            soup = BeautifulSoup(page.content, 'html.parser')
            text = soup.get_text(strip=True)

            search_data.append({
                'title': page.title,
                'url': f'pages/{filename}',
                'content': text[:500],  # First 500 chars for preview
                'keywords': self._extract_keywords(text),
                'headings': [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])]
            })

        (site_dir / 'assets' / 'search-index.json').write_text(
            json.dumps(search_data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction - get unique words, lowercase
        words = text.lower().split()
        # Filter out common words and get unique ones
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = list(set(w for w in words if len(w) > 3 and w not in common_words))
        return keywords[:20]  # Limit to 20 keywords

    def _build_navigation_tree(self, pages: List[PageResult]) -> List[Dict]:
        """Build navigation tree from pages."""
        nav_items = []

        for page in pages:
            nav_items.append({
                'title': page.title,
                'url': f'pages/{self._sanitize_filename(page.title)}.html',
                'source_url': page.url
            })

        return nav_items

    def _generate_toc(self, pages: List[PageResult]) -> List[Dict]:
        """Generate table of contents."""
        toc = []

        for page in pages:
            soup = BeautifulSoup(page.content, 'html.parser')
            headings = soup.find_all(['h1', 'h2', 'h3'])

            toc.append({
                'page_title': page.title,
                'page_url': f'pages/{self._sanitize_filename(page.title)}.html',
                'headings': [
                    {
                        'level': int(h.name[1]),
                        'text': h.get_text(strip=True),
                        'id': h.get('id', '')
                    }
                    for h in headings
                ]
            })

        return toc

    def _create_assets(self, assets_dir: Path, options: ExportOptions):
        """Create static assets (CSS, JS)."""
        # Create CSS
        css_content = self._get_default_css()
        if options.custom_css:
            custom_css_path = Path(options.custom_css)
            if custom_css_path.exists():
                css_content += '\n\n/* Custom CSS */\n' + custom_css_path.read_text()

        (assets_dir / 'style.css').write_text(css_content, encoding='utf-8')

        # Create JavaScript for search
        (assets_dir / 'search.js').write_text(self._get_search_js(), encoding='utf-8')

    def _get_default_css(self) -> str:
        """Get default CSS."""
        return '''
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    background: #f5f5f5;
}

.container {
    display: flex;
    min-height: 100vh;
}

.sidebar {
    width: 280px;
    background: #2c3e50;
    color: white;
    padding: 20px;
    position: fixed;
    height: 100vh;
    overflow-y: auto;
}

.sidebar h1 {
    font-size: 1.5em;
    margin-bottom: 20px;
    color: #3498db;
}

.sidebar nav ul {
    list-style: none;
}

.sidebar nav li {
    margin: 8px 0;
}

.sidebar nav a {
    color: #ecf0f1;
    text-decoration: none;
    display: block;
    padding: 5px 10px;
    border-radius: 3px;
    transition: background 0.3s;
}

.sidebar nav a:hover {
    background: #34495e;
}

.content {
    margin-left: 280px;
    padding: 40px;
    max-width: 900px;
    background: white;
    min-height: 100vh;
}

.search-box {
    margin-bottom: 20px;
    padding: 10px;
    width: 100%;
    border: 1px solid #ddd;
    border-radius: 5px;
    font-size: 14px;
}

h1, h2, h3, h4, h5, h6 {
    color: #2c3e50;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
}

h1 { font-size: 2.5em; border-bottom: 2px solid #3498db; padding-bottom: 0.3em; }
h2 { font-size: 2em; }
h3 { font-size: 1.5em; }

a {
    color: #3498db;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

code {
    background: #f5f5f5;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
}

pre {
    background: #2c3e50;
    color: #ecf0f1;
    padding: 15px;
    border-radius: 5px;
    overflow-x: auto;
    margin: 1em 0;
}

pre code {
    background: none;
    color: inherit;
    padding: 0;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
}

table th, table td {
    border: 1px solid #ddd;
    padding: 10px;
    text-align: left;
}

table th {
    background: #3498db;
    color: white;
}

table tr:nth-child(even) {
    background: #f9f9f9;
}

img {
    max-width: 100%;
    height: auto;
}

.source-url {
    font-size: 0.9em;
    color: #666;
    margin-bottom: 2em;
}

blockquote {
    border-left: 4px solid #3498db;
    padding-left: 1em;
    margin: 1em 0;
    color: #555;
    font-style: italic;
}

@media (max-width: 768px) {
    .sidebar {
        width: 100%;
        position: static;
        height: auto;
    }

    .content {
        margin-left: 0;
    }
}
'''

    def _get_search_js(self) -> str:
        """Get search JavaScript."""
        return '''
let searchIndex = [];

// Load search index
fetch('assets/search-index.json')
    .then(response => response.json())
    .then(data => {
        searchIndex = data;
    });

// Search function
function search(query) {
    if (!query || query.length < 2) {
        return [];
    }

    query = query.toLowerCase();

    return searchIndex.filter(item => {
        return item.title.toLowerCase().includes(query) ||
               item.content.toLowerCase().includes(query) ||
               item.keywords.some(kw => kw.includes(query)) ||
               item.headings.some(h => h.toLowerCase().includes(query));
    });
}

// Attach to search box if present
document.addEventListener('DOMContentLoaded', () => {
    const searchBox = document.getElementById('search');
    const searchResults = document.getElementById('search-results');

    if (searchBox) {
        searchBox.addEventListener('input', (e) => {
            const results = search(e.target.value);

            if (searchResults && results.length > 0) {
                searchResults.innerHTML = results.map(r =>
                    `<li><a href="${r.url}">${r.title}</a></li>`
                ).join('');
                searchResults.style.display = 'block';
            } else if (searchResults) {
                searchResults.style.display = 'none';
            }
        });
    }
});
'''

    def _get_index_template(self) -> str:
        """Get default index template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <div class="container">
        <aside class="sidebar">
            <h1>{{ title }}</h1>
            <input type="text" id="search" class="search-box" placeholder="Search documentation...">
            <ul id="search-results" style="display: none; list-style: none;"></ul>
            <nav>
                <ul>
                {% for item in navigation %}
                    <li><a href="{{ item.url }}">{{ item.title }}</a></li>
                {% endfor %}
                </ul>
            </nav>
        </aside>
        <main class="content">
            <h1>{{ title }}</h1>
            <p>Welcome to the documentation. Select a page from the sidebar to get started.</p>

            {% if toc %}
            <h2>Table of Contents</h2>
            <ul>
            {% for item in toc %}
                <li>
                    <a href="{{ item.page_url }}">{{ item.page_title }}</a>
                    {% if item.headings %}
                    <ul>
                    {% for heading in item.headings %}
                        <li>{{ heading.text }}</li>
                    {% endfor %}
                    </ul>
                    {% endif %}
                </li>
            {% endfor %}
            </ul>
            {% endif %}
        </main>
    </div>
    <script src="assets/search.js"></script>
</body>
</html>'''

    def _get_page_template(self) -> str:
        """Get default page template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ page.title }} - {{ title }}</title>
    <link rel="stylesheet" href="../assets/style.css">
</head>
<body>
    <div class="container">
        <aside class="sidebar">
            <h1><a href="../index.html" style="color: #3498db;">{{ title }}</a></h1>
            <input type="text" id="search" class="search-box" placeholder="Search documentation...">
            <ul id="search-results" style="display: none; list-style: none;"></ul>
            <nav>
                <ul>
                {% for item in navigation %}
                    <li><a href="../{{ item.url }}">{{ item.title }}</a></li>
                {% endfor %}
                </ul>
            </nav>
        </aside>
        <main class="content">
            <h1>{{ page.title }}</h1>
            <p class="source-url">Source: <a href="{{ page.url }}">{{ page.url }}</a></p>
            {{ content | safe }}
        </main>
    </div>
    <script src="../assets/search.js"></script>
</body>
</html>'''
