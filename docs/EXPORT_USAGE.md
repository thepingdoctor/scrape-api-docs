# Multi-Format Export System Usage Guide

## Overview

The export system provides multiple output formats for scraped documentation, enabling flexible consumption and distribution. All exports are generated using a plugin-based architecture that supports parallel processing.

## Supported Formats

- **PDF** - Professional documents with styling, TOC, and page numbers (requires `weasyprint`)
- **EPUB** - E-reader compatible format for Kindle, Kobo, etc. (requires `ebooklib`)
- **JSON** - Structured data with full metadata and statistics
- **HTML** - Static website with search and responsive design

## Installation

### Basic Installation (JSON + HTML only)
```bash
pip install scrape-api-docs
# or with poetry
poetry install
```

### Install with PDF support
```bash
pip install scrape-api-docs[pdf]
# or
poetry install --extras pdf
```

### Install with EPUB support
```bash
pip install scrape-api-docs[epub]
# or
poetry install --extras epub
```

### Install all formats
```bash
pip install scrape-api-docs[all-formats]
# or
poetry install --extras all-formats
```

## Quick Start

```python
import asyncio
from pathlib import Path
from scrape_api_docs.exporters import (
    ExportOrchestrator,
    ExportOptions,
    PageResult
)

async def export_documentation():
    # Create pages (normally from scraper)
    pages = [
        PageResult(
            url="https://example.com/docs",
            title="Documentation",
            content="# Documentation\n\nContent here...",
            format="markdown"
        )
    ]

    # Initialize orchestrator
    orchestrator = ExportOrchestrator()

    # Configure options
    options = {
        'pdf': ExportOptions(
            title="My Documentation",
            author="Your Name",
            include_toc=True
        ),
        'json': ExportOptions(
            include_metadata=True
        )
    }

    # Generate exports
    results = await orchestrator.generate_exports(
        pages=pages,
        base_url="https://example.com/docs",
        formats=['pdf', 'json', 'html'],
        output_dir=Path("./exports"),
        options=options
    )

    # Check results
    for format_name, result in results.items():
        if result.success:
            print(f"✓ {format_name}: {result.output_path}")
        else:
            print(f"✗ {format_name}: {result.error}")

asyncio.run(export_documentation())
```

## Export Options

### Common Options (All Formats)

```python
from scrape_api_docs.exporters import ExportOptions

options = ExportOptions(
    title="Documentation Title",           # Document title
    author="Author Name",                  # Author name
    include_toc=True,                      # Include table of contents
    include_metadata=True,                 # Include metadata
    source_url="https://example.com",      # Source URL
    custom_css="/path/to/custom.css"       # Custom CSS (PDF/HTML)
)
```

### PDF-Specific Options

```python
pdf_options = ExportOptions(
    title="API Documentation",
    author="Engineering Team",
    include_toc=True,              # Generate TOC with page numbers
    custom_css="custom-pdf.css"    # Custom styling
)
```

### EPUB-Specific Options

```python
epub_options = ExportOptions(
    title="User Guide",
    author="Documentation Team",
    cover_image="cover.jpg",       # Cover image path
    include_toc=True               # Chapter navigation
)
```

### HTML-Specific Options

```python
html_options = ExportOptions(
    title="Documentation Site",
    include_toc=True,              # Generate navigation
    custom_css="theme.css"         # Custom theme
)
```

## Advanced Usage

### Parallel Export Generation

Generate multiple formats simultaneously for optimal performance:

```python
async def parallel_exports():
    orchestrator = ExportOrchestrator()

    # All formats will be generated in parallel
    results = await orchestrator.generate_exports(
        pages=pages,
        base_url="https://example.com",
        formats=['pdf', 'epub', 'json', 'html'],  # All formats
        output_dir=Path("./exports")
    )
```

### Single Format Export

Export to a specific format:

```python
async def single_export():
    orchestrator = ExportOrchestrator()

    result = await orchestrator.generate_single_export(
        pages=pages,
        format_name='pdf',
        output_path=Path("./output.pdf"),
        options=ExportOptions(title="Documentation")
    )

    if result.success:
        print(f"Export successful: {result.output_path}")
```

### Check Available Formats

```python
orchestrator = ExportOrchestrator()
available = orchestrator.list_available_formats()
print(f"Available formats: {available}")
# Output: ['json', 'html', 'pdf', 'epub']
```

### Get Format Information

```python
info = orchestrator.get_format_info('pdf')
print(info)
# {
#     'format': 'pdf',
#     'file_extension': '.pdf',
#     'mime_type': 'application/pdf',
#     'capabilities': {
#         'supports_toc': True,
#         'supports_images': True,
#         'supports_styling': True
#     }
# }
```

## Output Structure

### PDF Output
- Single PDF file with:
  - Cover page
  - Table of contents
  - Styled content
  - Page numbers
  - Headers/footers

### EPUB Output
- Single EPUB file with:
  - Chapter structure
  - Navigation
  - Embedded styles
  - Metadata

### JSON Output
- Single JSON file with:
  ```json
  {
    "metadata": {...},
    "pages": [...],
    "statistics": {...},
    "structure": {...},
    "export_info": {...}
  }
  ```

### HTML Output
- Directory structure:
  ```
  html-export/
  ├── index.html          # Homepage with navigation
  ├── pages/              # Individual page HTML files
  │   ├── page1.html
  │   └── page2.html
  └── assets/
      ├── style.css       # Styles
      ├── search.js       # Search functionality
      └── search-index.json  # Search index
  ```

## Error Handling

```python
async def export_with_error_handling():
    orchestrator = ExportOrchestrator()

    results = await orchestrator.generate_exports(
        pages=pages,
        base_url="https://example.com",
        formats=['pdf', 'epub', 'json'],
        output_dir=Path("./exports")
    )

    for format_name, result in results.items():
        if result.success:
            print(f"✓ {format_name}")
            print(f"  Size: {result.size_bytes} bytes")
            print(f"  Duration: {result.duration:.2f}s")
        else:
            print(f"✗ {format_name}")
            print(f"  Error: {result.error}")
            # Handle error (log, retry, etc.)
```

## Integration with Scraper

```python
from scrape_api_docs.scraper import get_all_site_links
from scrape_api_docs.exporters import ExportOrchestrator, PageResult
import requests

async def scrape_and_export(base_url: str):
    # Scrape documentation
    urls = get_all_site_links(base_url)

    pages = []
    for url in urls:
        response = requests.get(url)
        # Convert to PageResult
        page = PageResult(
            url=url,
            title=extract_title(response.text),
            content=extract_content(response.text),
            format="html"
        )
        pages.append(page)

    # Export to multiple formats
    orchestrator = ExportOrchestrator()
    results = await orchestrator.generate_exports(
        pages=pages,
        base_url=base_url,
        formats=['pdf', 'json', 'html'],
        output_dir=Path("./exports"),
        options={
            'pdf': ExportOptions(
                title="Scraped Documentation",
                include_toc=True
            )
        }
    )

    return results
```

## Performance Considerations

- **Parallel Processing**: Multiple formats are generated concurrently
- **Memory Usage**: Large documentation may require significant memory for PDF/EPUB
- **Image Handling**: Images are embedded in PDF/EPUB, linked in HTML
- **Caching**: Export orchestrator caches converter instances

## Customization

### Custom CSS for PDF

```css
/* custom-pdf.css */
@page {
    size: A4;
    margin: 2.5cm;
}

h1 {
    color: #2c3e50;
    font-size: 24pt;
    border-bottom: 3px solid #3498db;
}

code {
    background: #f0f0f0;
    padding: 3px 6px;
    border-radius: 4px;
}
```

### Custom CSS for HTML

```css
/* custom-html.css */
.sidebar {
    background: #1a1a1a;
}

.content {
    max-width: 1200px;
}

h1 {
    color: #0066cc;
}
```

## Troubleshooting

### PDF Export Issues

**Issue**: `ImportError: WeasyPrint is required`
**Solution**: Install PDF dependencies: `pip install scrape-api-docs[pdf]`

**Issue**: Font rendering issues
**Solution**: Ensure system fonts are available or specify custom fonts in CSS

### EPUB Export Issues

**Issue**: `ImportError: ebooklib is required`
**Solution**: Install EPUB dependencies: `pip install scrape-api-docs[epub]`

### HTML Export Issues

**Issue**: Search not working
**Solution**: Ensure JavaScript is enabled and search-index.json is generated

## Examples

See `/home/ruhroh/scrape-api-docs/examples/export_example.py` for complete working examples.

## API Reference

### ExportOrchestrator

Main class for managing exports.

**Methods:**
- `list_available_formats() -> List[str]`
- `generate_exports(...) -> Dict[str, ExportResult]`
- `generate_single_export(...) -> ExportResult`
- `get_format_info(format_name: str) -> Dict`

### ExportOptions

Configuration for exports.

**Fields:**
- `title: Optional[str]`
- `author: Optional[str]`
- `include_toc: bool = True`
- `include_metadata: bool = True`
- `source_url: Optional[str]`
- `custom_css: Optional[str]`
- `cover_image: Optional[str]` (EPUB only)

### ExportResult

Result of an export operation.

**Fields:**
- `format: str`
- `output_path: Optional[Path]`
- `size_bytes: int`
- `duration: float`
- `page_count: int`
- `success: bool`
- `error: Optional[str]`
- `metadata: Dict[str, Any]`

## License

MIT License - See LICENSE file for details
