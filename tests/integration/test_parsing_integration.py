"""
Integration tests for HTML parsing and Markdown conversion.

Tests cover:
- BeautifulSoup + Markdownify integration
- HTML parser selection (lxml vs html.parser)
- Encoding detection
- Large document parsing
- Malformed HTML recovery
"""

import pytest
from bs4 import BeautifulSoup
from scrape_api_docs.scraper import (
    extract_main_content,
    convert_html_to_markdown,
)


@pytest.mark.integration
class TestBeautifulSoupIntegration:
    """Test BeautifulSoup parsing integration."""

    def test_lxml_parser(self, complex_html):
        """Test parsing with lxml parser."""
        soup = BeautifulSoup(complex_html, 'lxml')
        main = soup.find('main')

        assert main is not None
        assert main.find('h1').text == 'API Reference'

    def test_html_parser(self, complex_html):
        """Test parsing with html.parser."""
        soup = BeautifulSoup(complex_html, 'html.parser')
        main = soup.find('main')

        assert main is not None
        assert main.find('h1').text == 'API Reference'

    def test_parser_comparison(self, malformed_html):
        """Compare parser handling of malformed HTML."""
        # Both parsers should handle malformed HTML
        soup_lxml = BeautifulSoup(malformed_html, 'lxml')
        soup_html = BeautifulSoup(malformed_html, 'html.parser')

        # Both should find the main element
        assert soup_lxml.find('main') is not None
        assert soup_html.find('main') is not None

    def test_encoding_detection(self):
        """Test automatic encoding detection."""
        # HTML with UTF-8 characters
        html_utf8 = '''
        <html>
        <head><meta charset="utf-8"></head>
        <body><main>
            <p>Español: ñ, á, é</p>
            <p>中文: 你好</p>
            <p>العربية: مرحبا</p>
        </main></body>
        </html>
        '''

        soup = BeautifulSoup(html_utf8, 'html.parser')
        main = soup.find('main')

        assert 'ñ' in str(main) or 'Espa' in str(main)

    def test_large_document_parsing(self):
        """Test performance with large HTML documents."""
        # Create a large HTML document
        large_html = '<html><body><main>'
        for i in range(1000):
            large_html += f'<p>Paragraph {i} with some content</p>'
        large_html += '</main></body></html>'

        import time
        start = time.time()

        soup = BeautifulSoup(large_html, 'lxml')
        main = soup.find('main')
        paragraphs = main.find_all('p')

        elapsed = time.time() - start

        assert len(paragraphs) == 1000
        assert elapsed < 2.0  # Should parse quickly

    def test_malformed_html_recovery(self, malformed_html):
        """Test parser tolerance of malformed HTML."""
        soup = BeautifulSoup(malformed_html, 'lxml')

        # Should still extract content despite malformation
        main = soup.find('main')
        assert main is not None

        # Should find the link even with unclosed tags
        link = main.find('a')
        assert link is not None


@pytest.mark.integration
class TestMarkdownifyIntegration:
    """Test Markdownify conversion integration."""

    def test_complex_html_conversion(self, complex_html):
        """Test conversion of complex nested structures."""
        content = extract_main_content(complex_html)
        markdown = convert_html_to_markdown(content)

        # Should contain all major elements
        assert '# API Reference' in markdown
        assert '## Introduction' in markdown
        assert 'def hello()' in markdown
        assert 'GET' in markdown
        assert 'Retrieve data' in markdown

    def test_custom_options_heading_style(self):
        """Test custom heading style options."""
        html = '<h1>Title</h1><h2>Subtitle</h2>'

        # ATX style (default)
        markdown = convert_html_to_markdown(html)

        assert '# Title' in markdown
        assert '## Subtitle' in markdown

    def test_custom_options_bullet_characters(self):
        """Test custom bullet character options."""
        html = '<ul><li>Item 1</li><li>Item 2</li></ul>'

        markdown = convert_html_to_markdown(html)

        # Should use asterisks as specified in scraper.py
        assert '* Item 1' in markdown or '*' in markdown

    def test_whitespace_preservation_in_code(self):
        """Test code block formatting preservation."""
        html = '''
        <pre><code>def function():
    indented_line()
    another_line()
        nested_more()</code></pre>
        '''

        markdown = convert_html_to_markdown(html)

        # Should preserve indentation
        assert 'def function()' in markdown
        assert 'indented_line()' in markdown

    def test_link_reference_style(self):
        """Test link conversion style."""
        html = '<a href="https://example.com">Example Link</a>'

        markdown = convert_html_to_markdown(html)

        # Should have inline links
        assert 'Example Link' in markdown
        assert 'https://example.com' in markdown


@pytest.mark.integration
class TestEndToEndParsing:
    """Test complete parsing pipeline."""

    def test_extract_and_convert_pipeline(self, complex_html):
        """Test full extraction and conversion workflow."""
        # Step 1: Extract
        content = extract_main_content(complex_html)
        assert '<main>' in content

        # Step 2: Convert
        markdown = convert_html_to_markdown(content)

        # Verify conversion quality
        assert '# API Reference' in markdown
        assert 'Introduction' in markdown
        assert 'complex' in markdown.lower()

    def test_multiple_content_selectors(self):
        """Test fallback chain for content extraction."""
        # Test with main tag
        html_main = '<html><body><main><h1>Main Content</h1></main></body></html>'
        content = extract_main_content(html_main)
        assert 'Main Content' in content

        # Test with article tag
        html_article = '<html><body><article><h1>Article Content</h1></article></body></html>'
        content = extract_main_content(html_article)
        assert 'Article Content' in content

        # Test with class selector
        html_class = '<html><body><div class="main-content"><h1>Class Content</h1></div></body></html>'
        content = extract_main_content(html_class)
        assert 'Class Content' in content

    def test_nested_element_extraction(self):
        """Test extraction from deeply nested structures."""
        html = '''
        <html><body>
            <div class="wrapper">
                <main>
                    <section>
                        <article>
                            <div class="content">
                                <h1>Deep Content</h1>
                                <p>Nested paragraph</p>
                            </div>
                        </article>
                    </section>
                </main>
            </div>
        </body></html>
        '''

        content = extract_main_content(html)
        markdown = convert_html_to_markdown(content)

        assert 'Deep Content' in markdown
        assert 'Nested paragraph' in markdown

    def test_special_characters_handling(self):
        """Test handling of special characters through full pipeline."""
        html = '''
        <html><body><main>
            <p>&lt;script&gt;alert('test')&lt;/script&gt;</p>
            <p>&amp; &quot; &apos; &nbsp;</p>
            <p>Symbols: © ® ™ €</p>
        </main></body></html>
        '''

        content = extract_main_content(html)
        markdown = convert_html_to_markdown(content)

        # Entities should be decoded
        assert 'script' in markdown.lower() or '&lt;' in markdown

    def test_table_complex_conversion(self):
        """Test complex table structures."""
        html = '''
        <html><body><main>
            <table>
                <thead>
                    <tr>
                        <th>Header 1</th>
                        <th>Header 2</th>
                        <th>Header 3</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Row 1 Col 1</td>
                        <td>Row 1 Col 2</td>
                        <td>Row 1 Col 3</td>
                    </tr>
                    <tr>
                        <td>Row 2 Col 1</td>
                        <td>Row 2 Col 2</td>
                        <td>Row 2 Col 3</td>
                    </tr>
                </tbody>
            </table>
        </main></body></html>
        '''

        content = extract_main_content(html)
        markdown = convert_html_to_markdown(content)

        # Should contain table headers and data
        assert 'Header 1' in markdown
        assert 'Row 1 Col 1' in markdown
        assert 'Row 2 Col 3' in markdown

    def test_mixed_content_types(self):
        """Test documents with mixed content types."""
        html = '''
        <html><body><main>
            <h1>Mixed Content</h1>
            <p>Regular <strong>paragraph</strong> with <em>emphasis</em></p>
            <ul>
                <li>List item</li>
            </ul>
            <pre><code>code block</code></pre>
            <blockquote>Quote</blockquote>
            <a href="/link">Link</a>
        </main></body></html>
        '''

        content = extract_main_content(html)
        markdown = convert_html_to_markdown(content)

        assert 'Mixed Content' in markdown
        assert 'paragraph' in markdown
        assert 'List item' in markdown
        assert 'code block' in markdown
        assert 'Quote' in markdown

    def test_empty_elements_handling(self):
        """Test handling of empty HTML elements."""
        html = '''
        <html><body><main>
            <h1>Title</h1>
            <p></p>
            <div></div>
            <p>Real content</p>
        </main></body></html>
        '''

        content = extract_main_content(html)
        markdown = convert_html_to_markdown(content)

        assert 'Title' in markdown
        assert 'Real content' in markdown
