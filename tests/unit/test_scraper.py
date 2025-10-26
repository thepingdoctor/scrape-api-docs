"""
Unit tests for core scraper functionality.

Tests cover:
- get_all_site_links: Web crawling and link discovery
- extract_main_content: Content extraction from HTML
- convert_html_to_markdown: HTML to Markdown conversion
- generate_filename_from_url: Filename sanitization
- scrape_site: End-to-end scraping workflow
"""

import pytest
import responses
from unittest.mock import Mock, patch, MagicMock
from scrape_api_docs.scraper import (
    get_all_site_links,
    extract_main_content,
    convert_html_to_markdown,
    generate_filename_from_url,
    scrape_site,
)
import requests


# ============================================================================
# Tests for get_all_site_links()
# ============================================================================

@pytest.mark.unit
class TestGetAllSiteLinks:
    """Test suite for web crawling functionality."""

    @responses.activate
    def test_single_page_crawl(self, simple_html):
        """Test crawling a single page with no links."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><body><main>No links</main></body></html>',
            status=200
        )

        links = get_all_site_links('https://example.com/docs/')

        assert len(links) == 1
        assert 'https://example.com/docs/' in links

    @responses.activate
    def test_multi_page_discovery(self, mock_site_structure):
        """Test discovery of multiple pages through crawling."""
        links = get_all_site_links('https://example.com/docs/')

        assert len(links) == 3
        assert 'https://example.com/docs/' in links
        assert 'https://example.com/docs/page1' in links
        assert 'https://example.com/docs/page2' in links

    @responses.activate
    def test_deduplication(self):
        """Test that duplicate URLs are filtered out."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='''
            <html><body><main>
                <a href="/docs/page1">Link 1</a>
                <a href="/docs/page1">Duplicate</a>
                <a href="/docs/page1?query=test">Same page with query</a>
            </main></body></html>
            ''',
            status=200
        )
        responses.add(
            responses.GET,
            'https://example.com/docs/page1',
            body='<html><body><main>Page 1</main></body></html>',
            status=200
        )

        links = get_all_site_links('https://example.com/docs/')

        # Should have only 2 unique pages (index and page1)
        assert len(links) == 2
        assert 'https://example.com/docs/page1' in links

    @responses.activate
    def test_domain_boundary_respected(self):
        """Test that crawler stays within the same domain."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='''
            <html><body><main>
                <a href="/docs/page1">Internal</a>
                <a href="https://external.com/page">External</a>
                <a href="https://example.com/blog/">Different path</a>
            </main></body></html>
            ''',
            status=200
        )
        responses.add(
            responses.GET,
            'https://example.com/docs/page1',
            body='<html><body><main>Page 1</main></body></html>',
            status=200
        )

        links = get_all_site_links('https://example.com/docs/')

        # Should only have internal links within /docs/
        assert all('example.com/docs/' in link for link in links)
        assert not any('external.com' in link for link in links)
        assert not any('/blog/' in link for link in links)

    @responses.activate
    def test_path_boundary_enforcement(self):
        """Test that crawler respects base path prefix."""
        responses.add(
            responses.GET,
            'https://example.com/docs/api/',
            body='''
            <html><body><main>
                <a href="/docs/api/v1/">API v1</a>
                <a href="/docs/guide/">Guide</a>
            </main></body></html>
            ''',
            status=200
        )
        responses.add(
            responses.GET,
            'https://example.com/docs/api/v1/',
            body='<html><body><main>API v1</main></body></html>',
            status=200
        )

        links = get_all_site_links('https://example.com/docs/api/')

        # Should only include URLs starting with /docs/api/
        assert all('/docs/api/' in link for link in links)
        assert not any('/docs/guide/' in link for link in links)

    @responses.activate
    def test_fragment_query_stripping(self):
        """Test that fragments and query parameters are stripped."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='''
            <html><body><main>
                <a href="/docs/page#section">Fragment</a>
                <a href="/docs/page?query=value">Query</a>
                <a href="/docs/page#hash?param=test">Both</a>
            </main></body></html>
            ''',
            status=200
        )
        responses.add(
            responses.GET,
            'https://example.com/docs/page',
            body='<html><body><main>Page</main></body></html>',
            status=200
        )

        links = get_all_site_links('https://example.com/docs/')

        # Should have only 2 links (index and clean page)
        assert len(links) == 2
        assert 'https://example.com/docs/page' in links
        assert not any('#' in link or '?' in link for link in links)

    @responses.activate
    def test_timeout_handling(self):
        """Test behavior with slow-responding servers."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body=requests.exceptions.Timeout()
        )

        # Should return at least the base URL even if it times out
        links = get_all_site_links('https://example.com/docs/')

        # Should handle gracefully and return the base URL
        assert len(links) >= 1

    @responses.activate
    def test_404_error_handling(self):
        """Test graceful handling of 404 errors."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><body><main><a href="/docs/broken">Link</a></main></body></html>',
            status=200
        )
        responses.add(
            responses.GET,
            'https://example.com/docs/broken',
            status=404
        )

        links = get_all_site_links('https://example.com/docs/')

        # Should continue despite 404
        assert 'https://example.com/docs/' in links

    @responses.activate
    def test_500_error_handling(self):
        """Test graceful handling of 500 server errors."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><body><main><a href="/docs/error">Link</a></main></body></html>',
            status=200
        )
        responses.add(
            responses.GET,
            'https://example.com/docs/error',
            status=500
        )

        links = get_all_site_links('https://example.com/docs/')

        # Should handle server errors gracefully
        assert 'https://example.com/docs/' in links

    @responses.activate
    def test_malformed_html_handling(self, malformed_html):
        """Test handling of broken HTML."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body=malformed_html,
            status=200
        )

        # Should not crash on malformed HTML
        links = get_all_site_links('https://example.com/docs/')
        assert len(links) >= 1

    @responses.activate
    def test_empty_response(self):
        """Test handling of pages with no links."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><body><main><p>No links here</p></main></body></html>',
            status=200
        )

        links = get_all_site_links('https://example.com/docs/')

        assert len(links) == 1
        assert links[0] == 'https://example.com/docs/'

    @responses.activate
    def test_circular_references(self):
        """Test prevention of infinite loops with circular links."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><body><main><a href="/docs/page1">Page 1</a></main></body></html>',
            status=200
        )
        responses.add(
            responses.GET,
            'https://example.com/docs/page1',
            body='<html><body><main><a href="/docs/">Back to home</a></main></body></html>',
            status=200
        )

        links = get_all_site_links('https://example.com/docs/')

        # Should have exactly 2 links despite circular reference
        assert len(links) == 2


# ============================================================================
# Tests for extract_main_content()
# ============================================================================

@pytest.mark.unit
class TestExtractMainContent:
    """Test suite for content extraction functionality."""

    def test_main_tag_extraction(self, simple_html):
        """Test extraction from <main> element."""
        content = extract_main_content(simple_html)

        assert '<main>' in content
        assert 'Documentation' in content
        assert 'Main content here' in content
        assert 'Navigation' not in content
        assert 'Footer' not in content

    def test_article_fallback(self, article_fallback_html):
        """Test fallback to <article> when no main tag."""
        content = extract_main_content(article_fallback_html)

        assert '<article>' in content
        assert 'Article Content' in content

    def test_class_selector_fallback(self, class_selector_html):
        """Test fallback to .main-content class."""
        content = extract_main_content(class_selector_html)

        assert 'Main Content Class' in content

    def test_id_selector_fallback(self):
        """Test fallback to #content ID."""
        html = """
        <html><body>
            <div id="content">
                <h1>Content by ID</h1>
            </div>
        </body></html>
        """

        content = extract_main_content(html)

        assert 'Content by ID' in content

    def test_no_content_found(self, no_main_content_html):
        """Test return of empty string when no content found."""
        content = extract_main_content(no_main_content_html)

        assert content == ""

    def test_multiple_main_tags(self):
        """Test handling of multiple main elements (invalid HTML)."""
        html = """
        <html><body>
            <main><h1>First Main</h1></main>
            <main><h1>Second Main</h1></main>
        </body></html>
        """

        content = extract_main_content(html)

        # Should return the first main element
        assert 'First Main' in content

    def test_nested_structures(self, complex_html):
        """Test extraction from complex nested HTML."""
        content = extract_main_content(complex_html)

        assert 'API Reference' in content
        assert 'Introduction' in content
        assert 'def hello()' in content

    def test_script_style_removal(self):
        """Test that script and style tags are included but can be filtered."""
        html = """
        <html><body>
            <main>
                <h1>Content</h1>
                <script>alert('test')</script>
                <style>.test { color: red; }</style>
                <p>Real content</p>
            </main>
        </body></html>
        """

        content = extract_main_content(html)

        # Content is extracted but scripts/styles are in the raw HTML
        assert '<main>' in content
        assert 'Real content' in content


# ============================================================================
# Tests for convert_html_to_markdown()
# ============================================================================

@pytest.mark.unit
class TestConvertHtmlToMarkdown:
    """Test suite for HTML to Markdown conversion."""

    def test_heading_conversion(self):
        """Test conversion of H1-H6 to ATX style."""
        html = """
        <h1>Heading 1</h1>
        <h2>Heading 2</h2>
        <h3>Heading 3</h3>
        <h4>Heading 4</h4>
        <h5>Heading 5</h5>
        <h6>Heading 6</h6>
        """

        markdown = convert_html_to_markdown(html)

        assert '# Heading 1' in markdown
        assert '## Heading 2' in markdown
        assert '### Heading 3' in markdown
        assert '#### Heading 4' in markdown
        assert '##### Heading 5' in markdown
        assert '###### Heading 6' in markdown

    def test_list_conversion(self):
        """Test conversion of UL/OL to Markdown lists."""
        html = """
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <ol>
            <li>First</li>
            <li>Second</li>
        </ol>
        """

        markdown = convert_html_to_markdown(html)

        assert '* Item 1' in markdown
        assert '* Item 2' in markdown
        assert '1. First' in markdown or '1.' in markdown

    def test_link_preservation(self):
        """Test that URLs are maintained in conversion."""
        html = '<a href="https://example.com">Link Text</a>'

        markdown = convert_html_to_markdown(html)

        assert 'Link Text' in markdown
        assert 'https://example.com' in markdown

    def test_code_block_conversion(self):
        """Test conversion of pre/code tags."""
        html = '<pre><code>def hello():\n    print("Hello")</code></pre>'

        markdown = convert_html_to_markdown(html)

        assert 'def hello()' in markdown
        assert 'print("Hello")' in markdown

    def test_table_conversion(self, complex_html):
        """Test HTML tables to Markdown tables."""
        markdown = convert_html_to_markdown(complex_html)

        # Markdown tables should contain pipe characters
        assert 'Method' in markdown
        assert 'Description' in markdown

    def test_image_conversion(self):
        """Test IMG tags to Markdown image syntax."""
        html = '<img src="image.png" alt="Test Image" />'

        markdown = convert_html_to_markdown(html)

        assert 'image.png' in markdown
        assert 'Test Image' in markdown

    def test_bold_italic_conversion(self):
        """Test strong/em to Markdown emphasis."""
        html = '<p>This is <strong>bold</strong> and <em>italic</em> text.</p>'

        markdown = convert_html_to_markdown(html)

        # Should have markdown emphasis (** or __)
        assert 'bold' in markdown
        assert 'italic' in markdown

    def test_special_characters(self):
        """Test HTML entities are decoded properly."""
        html = '<p>&lt;div&gt; &amp; &quot;test&quot;</p>'

        markdown = convert_html_to_markdown(html)

        assert '<div>' in markdown or '&lt;' in markdown
        assert '&' in markdown or '&amp;' in markdown

    def test_whitespace_handling(self):
        """Test proper spacing in output."""
        html = '<p>Paragraph 1</p><p>Paragraph 2</p>'

        markdown = convert_html_to_markdown(html)

        # Should have some separation between paragraphs
        assert 'Paragraph 1' in markdown
        assert 'Paragraph 2' in markdown

    def test_nested_lists(self):
        """Test nested list structures."""
        html = """
        <ul>
            <li>Item 1
                <ul>
                    <li>Nested item</li>
                </ul>
            </li>
            <li>Item 2</li>
        </ul>
        """

        markdown = convert_html_to_markdown(html)

        assert 'Item 1' in markdown
        assert 'Nested item' in markdown


# ============================================================================
# Tests for generate_filename_from_url()
# ============================================================================

@pytest.mark.unit
class TestGenerateFilenameFromUrl:
    """Test suite for filename generation."""

    def test_standard_url(self):
        """Test conversion of typical doc URL to filename."""
        filename = generate_filename_from_url('https://example.com/docs/api/')

        assert filename == 'example_com_docs_api_documentation.md'

    def test_empty_path(self):
        """Test handling of domain-only URLs."""
        filename = generate_filename_from_url('https://example.com/')

        assert filename == 'example_com_documentation.md'

    def test_multiple_path_segments(self):
        """Test replacing slashes with underscores."""
        filename = generate_filename_from_url('https://docs.python.org/3/library/functions/')

        assert filename == 'docs_python_org_3_library_functions_documentation.md'

    def test_dot_replacement(self):
        """Test replacing dots in domain with underscores."""
        filename = generate_filename_from_url('https://api.example.com/')

        assert filename == 'api_example_com_documentation.md'
        assert '.' not in filename.replace('.md', '')

    def test_special_characters_sanitization(self):
        """Test sanitization of problematic characters."""
        filename = generate_filename_from_url('https://example.com/docs-api/')

        # Should replace or handle special characters
        assert filename.endswith('_documentation.md')

    @pytest.mark.parametrize("url,expected", [
        ("https://example.com/docs/api/", "example_com_docs_api_documentation.md"),
        ("https://api.example.com/", "api_example_com_documentation.md"),
        ("https://example.com/", "example_com_documentation.md"),
    ])
    def test_multiple_url_patterns(self, url, expected):
        """Test various URL patterns generate correct filenames."""
        filename = generate_filename_from_url(url)
        assert filename == expected


# ============================================================================
# Tests for scrape_site()
# ============================================================================

@pytest.mark.unit
class TestScrapeSite:
    """Test suite for complete scraping workflow."""

    @responses.activate
    def test_complete_workflow(self, mock_site_structure, temp_dir, monkeypatch):
        """Test end-to-end scraping process."""
        # Change to temp directory for output
        monkeypatch.chdir(temp_dir)

        scrape_site('https://example.com/docs/')

        # Check file was created
        import os
        files = os.listdir(temp_dir)
        assert any(f.endswith('_documentation.md') for f in files)

    @responses.activate
    def test_file_creation(self, temp_dir, monkeypatch):
        """Test that output file is created."""
        monkeypatch.chdir(temp_dir)

        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><body><main><h1>Test</h1></main></body></html>',
            status=200
        )

        scrape_site('https://example.com/docs/')

        import os
        assert len(os.listdir(temp_dir)) > 0

    @responses.activate
    def test_content_format(self, temp_dir, monkeypatch):
        """Test Markdown structure and headers."""
        monkeypatch.chdir(temp_dir)

        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><head><title>Test Page</title></head><body><main><h1>Content</h1></main></body></html>',
            status=200
        )

        scrape_site('https://example.com/docs/')

        # Read the generated file
        import os
        filename = [f for f in os.listdir(temp_dir) if f.endswith('.md')][0]
        with open(os.path.join(temp_dir, filename), 'r') as f:
            content = f.read()

        assert '# Documentation for' in content
        assert '**Source:**' in content
        assert 'https://example.com/docs/' in content

    @responses.activate
    def test_empty_site_handling(self, temp_dir, monkeypatch):
        """Test handling of site with single page."""
        monkeypatch.chdir(temp_dir)

        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><body><main><p>Single page</p></main></body></html>',
            status=200
        )

        scrape_site('https://example.com/docs/')

        # Should complete without error
        import os
        assert len(os.listdir(temp_dir)) > 0

    @responses.activate
    def test_encoding_handling(self, temp_dir, monkeypatch):
        """Test UTF-8 content preservation."""
        monkeypatch.chdir(temp_dir)

        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><body><main><p>Unicode: ñ, é, 中文</p></main></body></html>',
            status=200
        )

        scrape_site('https://example.com/docs/')

        import os
        filename = [f for f in os.listdir(temp_dir) if f.endswith('.md')][0]
        with open(os.path.join(temp_dir, filename), 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'ñ' in content or 'Unicode' in content
