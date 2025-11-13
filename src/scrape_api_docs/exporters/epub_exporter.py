"""EPUB export converter using ebooklib."""

import time
import logging
from pathlib import Path
from typing import List, Dict, TYPE_CHECKING
from datetime import datetime
from bs4 import BeautifulSoup

from .base import ExportConverter, ExportOptions, ExportResult, PageResult

if TYPE_CHECKING:
    from ebooklib import epub

try:
    from ebooklib import epub
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False
    epub = None  # type: ignore

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

logger = logging.getLogger(__name__)


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

    def __init__(self):
        """Initialize EPUB converter."""
        if not EBOOKLIB_AVAILABLE:
            raise ImportError("ebooklib is required for EPUB export. Install with: pip install ebooklib")

        if not MARKDOWN_AVAILABLE:
            raise ImportError("Markdown is required for EPUB export. Install with: pip install markdown")

    async def convert(
        self,
        pages: List[PageResult],
        output_path: Path,
        options: ExportOptions
    ) -> ExportResult:
        """Generate EPUB from pages."""
        start_time = time.time()

        try:
            # Create EPUB book
            book = epub.EpubBook()

            # Set metadata
            book_id = f'docs-{hash(options.source_url or pages[0].url if pages else "unknown")}'
            book.set_identifier(book_id)
            book.set_title(options.title or 'Documentation')
            book.set_language('en')

            if options.author:
                book.add_author(options.author)

            book.add_metadata('DC', 'date', datetime.now().isoformat())
            if options.source_url:
                book.add_metadata('DC', 'source', options.source_url)

            # Add cover if provided
            if options.cover_image:
                cover_path = Path(options.cover_image)
                if cover_path.exists():
                    with open(cover_path, 'rb') as cover_file:
                        book.set_cover('cover.jpg', cover_file.read())

            # Create chapters
            chapters = []
            spine = ['nav']

            for idx, page in enumerate(pages):
                chapter = self._create_chapter(page, idx)
                book.add_item(chapter)
                chapters.append(chapter)
                spine.append(chapter)

            # Add table of contents
            book.toc = self._generate_toc(chapters, pages)

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
                success=True,
                metadata={
                    'title': options.title or 'Documentation',
                    'author': options.author,
                    'chapter_count': len(chapters)
                }
            )

        except Exception as e:
            logger.error(f"EPUB export failed: {e}", exc_info=True)
            return ExportResult(
                format=self.format_name,
                success=False,
                error=str(e)
            )

    def _create_chapter(
        self,
        page: PageResult,
        idx: int
    ) -> "epub.EpubHtml":
        """Create EPUB chapter from page."""
        chapter = epub.EpubHtml(
            title=page.title,
            file_name=f'chapter_{idx:04d}.xhtml',
            lang='en'
        )

        # Convert Markdown to HTML if needed
        if page.format == 'markdown':
            content = markdown.markdown(
                page.content,
                extensions=['extra', 'codehilite', 'toc', 'fenced_code']
            )
        else:
            content = page.content

        # Clean content
        soup = BeautifulSoup(content, 'html.parser')

        # Wrap in EPUB-compatible HTML
        chapter.content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>{page.title}</title>
    <link rel="stylesheet" href="style.css" type="text/css"/>
</head>
<body>
    <h1 class="chapter-title">{page.title}</h1>
    <p class="source-url">Source: <a href="{page.url}">{page.url}</a></p>
    {str(soup)}
</body>
</html>'''

        return chapter

    def _get_epub_css(self) -> "epub.EpubItem":
        """Get CSS for EPUB."""
        style = '''
body {
    font-family: Georgia, serif;
    line-height: 1.6;
    margin: 1em;
    color: #333;
}

.chapter-title {
    font-size: 1.8em;
    color: #2c3e50;
    border-bottom: 2px solid #3498db;
    padding-bottom: 0.3em;
    margin-bottom: 0.5em;
}

.source-url {
    font-size: 0.85em;
    color: #666;
    font-style: italic;
    margin-bottom: 1.5em;
}

.source-url a {
    color: #3498db;
    text-decoration: none;
}

h1, h2, h3, h4, h5, h6 {
    color: #2c3e50;
    font-weight: bold;
    margin-top: 1em;
    margin-bottom: 0.5em;
}

h1 { font-size: 1.8em; }
h2 { font-size: 1.5em; }
h3 { font-size: 1.3em; }
h4 { font-size: 1.1em; }

code {
    background: #f5f5f5;
    padding: 2px 5px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
}

pre {
    background: #f5f5f5;
    padding: 10px;
    border-radius: 5px;
    overflow-x: auto;
    border-left: 3px solid #3498db;
    margin: 1em 0;
}

pre code {
    background: none;
    padding: 0;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
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
    text-decoration: underline;
}

img {
    max-width: 100%;
    height: auto;
}

blockquote {
    border-left: 4px solid #3498db;
    margin: 1em 0;
    padding-left: 1em;
    color: #555;
    font-style: italic;
}

ul, ol {
    margin: 0.5em 0;
    padding-left: 2em;
}

li {
    margin: 0.3em 0;
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
        chapters: List["epub.EpubHtml"],
        pages: List[PageResult]
    ) -> List:
        """Generate table of contents."""
        toc = []

        for chapter, page in zip(chapters, pages):
            toc.append(chapter)

        return toc
