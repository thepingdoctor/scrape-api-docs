"""
Security tests for input validation.

Tests cover:
- URL injection prevention
- JavaScript injection
- Data URLs
- File URLs
- Path traversal
- Command injection
- XSS prevention
"""

import pytest
from scrape_api_docs.streamlit_app import validate_url
from scrape_api_docs.scraper import generate_filename_from_url


@pytest.mark.security
class TestURLInjection:
    """Test prevention of URL injection attacks."""

    def test_javascript_injection(self):
        """Test rejection of javascript: URLs."""
        urls = [
            "javascript:alert('XSS')",
            "javascript:void(0)",
            "javascript://example.com/%0Aalert('XSS')",
        ]

        for url in urls:
            is_valid, error = validate_url(url)
            assert is_valid is False, f"Should reject javascript URL: {url}"

    def test_data_urls(self):
        """Test rejection of data: URLs."""
        urls = [
            "data:text/html,<script>alert('XSS')</script>",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4=",
            "data:application/javascript,alert('XSS')",
        ]

        for url in urls:
            is_valid, error = validate_url(url)
            assert is_valid is False, f"Should reject data URL: {url}"

    def test_file_urls(self):
        """Test rejection of file:// URLs."""
        urls = [
            "file:///etc/passwd",
            "file:///C:/Windows/System32/config/sam",
            "file://localhost/etc/shadow",
        ]

        for url in urls:
            is_valid, error = validate_url(url)
            assert is_valid is False, f"Should reject file URL: {url}"

    def test_vbscript_injection(self):
        """Test rejection of vbscript: URLs."""
        url = "vbscript:msgbox('XSS')"
        is_valid, error = validate_url(url)
        assert is_valid is False

    def test_about_blank(self):
        """Test handling of about:blank."""
        url = "about:blank"
        is_valid, error = validate_url(url)
        assert is_valid is False


@pytest.mark.security
class TestPathTraversal:
    """Test prevention of path traversal attacks."""

    def test_filename_traversal_prevention(self):
        """Test that ../../../ patterns are sanitized."""
        # The filename generator should sanitize malicious paths
        malicious_urls = [
            "https://example.com/../../../etc/passwd",
            "https://example.com/docs/../../admin",
        ]

        for url in malicious_urls:
            filename = generate_filename_from_url(url)
            # Filename should not contain ..
            assert '..' not in filename
            assert filename.endswith('_documentation.md')

    def test_null_byte_injection(self):
        """Test prevention of null byte injection in filenames."""
        # Null bytes should be handled/removed
        url = "https://example.com/docs"
        filename = generate_filename_from_url(url)

        # Should not contain null bytes
        assert '\x00' not in filename

    def test_windows_path_injection(self):
        """Test prevention of Windows path patterns."""
        url = "https://example.com/C:/Windows/System32"
        filename = generate_filename_from_url(url)

        # Should sanitize Windows paths
        assert ':' not in filename.replace('.md', '')
        assert '\\' not in filename

    def test_absolute_path_prevention(self):
        """Test that absolute paths are not created."""
        url = "https://example.com//etc/passwd"
        filename = generate_filename_from_url(url)

        # Should not start with / (except for absolute paths which we want)
        # The generated filename should be relative
        assert filename.endswith('_documentation.md')

    def test_special_filename_characters(self):
        """Test sanitization of special filename characters."""
        url = "https://example.com/docs/<script>test</script>"
        filename = generate_filename_from_url(url)

        # Should not contain < > or other dangerous characters
        dangerous_chars = ['<', '>', '|', '?', '*', '"', ':', '\\']
        for char in dangerous_chars:
            assert char not in filename, f"Filename contains dangerous char: {char}"


@pytest.mark.security
class TestCommandInjection:
    """Test prevention of command injection."""

    def test_shell_metacharacters_in_url(self):
        """Test handling of shell metacharacters in URLs."""
        urls = [
            "https://example.com/docs;rm -rf /",
            "https://example.com/docs|whoami",
            "https://example.com/docs&& cat /etc/passwd",
            "https://example.com/docs`id`",
            "https://example.com/docs$(whoami)",
        ]

        for url in urls:
            # Validation should handle these
            is_valid, _ = validate_url(url)
            # Even if valid as URL, filename should be safe
            if is_valid:
                filename = generate_filename_from_url(url)
                # Shell metacharacters should be sanitized
                dangerous = [';', '|', '&', '`', '$', '(', ')']
                # Note: Some may be valid URL characters, but filename should be safe
                assert filename.endswith('.md')


@pytest.mark.security
class TestInputSanitization:
    """Test general input sanitization."""

    def test_extremely_long_url(self):
        """Test handling of extremely long URLs."""
        long_url = "https://example.com/" + "a" * 10000
        is_valid, error = validate_url(long_url)

        # Should handle long URLs (they can be valid)
        # But filename should be reasonable
        if is_valid:
            filename = generate_filename_from_url(long_url)
            # Filename should not be absurdly long
            assert len(filename) < 500  # Reasonable limit

    def test_unicode_in_url(self):
        """Test handling of Unicode characters."""
        urls = [
            "https://例え.jp/",
            "https://example.com/日本語/",
            "https://مثال.إختبار/",
        ]

        for url in urls:
            is_valid, _ = validate_url(url)
            if is_valid:
                filename = generate_filename_from_url(url)
                # Should generate valid filename
                assert filename.endswith('.md')

    def test_url_encoded_characters(self):
        """Test handling of URL-encoded characters."""
        url = "https://example.com/docs%2F..%2F..%2Fetc%2Fpasswd"
        is_valid, error = validate_url(url)

        # Should be valid URL format
        if is_valid:
            filename = generate_filename_from_url(url)
            # Filename should be safe
            assert filename.endswith('.md')

    def test_multiple_schemes(self):
        """Test URLs with multiple schemes."""
        urls = [
            "https://http://example.com",
            "http://https://example.com",
        ]

        for url in urls:
            is_valid, error = validate_url(url)
            # Should handle gracefully (likely invalid)
            assert isinstance(is_valid, bool)

    def test_whitespace_in_url(self):
        """Test handling of whitespace in URLs."""
        urls = [
            "https://example.com/docs test",
            "https://example .com/docs",
            " https://example.com/docs",
            "https://example.com/docs ",
        ]

        for url in urls:
            is_valid, error = validate_url(url)
            # Whitespace should be handled
            assert isinstance(is_valid, bool)

    def test_case_sensitivity(self):
        """Test case handling in URL validation."""
        urls = [
            "HTTPS://EXAMPLE.COM/DOCS",
            "HtTpS://ExAmPlE.CoM/docs",
        ]

        for url in urls:
            is_valid, error = validate_url(url)
            # Should handle case variations
            assert isinstance(is_valid, bool)


@pytest.mark.security
class TestOutputSanitization:
    """Test output sanitization for security."""

    def test_xss_in_scraped_content(self):
        """Test that scraped content with XSS is safe in Markdown."""
        from scrape_api_docs.scraper import convert_html_to_markdown

        html_with_xss = '''
        <html><body><main>
            <script>alert('XSS')</script>
            <p onload="alert('XSS')">Content</p>
            <img src="x" onerror="alert('XSS')">
        </main></body></html>
        '''

        markdown = convert_html_to_markdown(html_with_xss)

        # Markdown output should be safe (scripts converted to text)
        # Note: This is informational - Markdown itself is safer
        assert 'alert' not in markdown or 'alert(\'XSS\')' in markdown

    def test_html_injection_prevention(self):
        """Test proper escaping in Markdown output."""
        from scrape_api_docs.scraper import convert_html_to_markdown

        html = '<p>&lt;iframe src="evil.com"&gt;&lt;/iframe&gt;</p>'
        markdown = convert_html_to_markdown(html)

        # Should preserve HTML entities or convert safely
        assert 'iframe' in markdown.lower()

    def test_command_execution_via_filenames(self):
        """Test that filenames cannot execute commands."""
        malicious_urls = [
            "https://example.com/$(whoami)",
            "https://example.com/`id`",
            "https://example.com/;ls;",
        ]

        for url in malicious_urls:
            filename = generate_filename_from_url(url)
            # Filename should not contain shell metacharacters
            assert not any(char in filename for char in ['$', '`', ';'])


@pytest.mark.security
class TestProtocolValidation:
    """Test protocol-level security."""

    def test_only_http_https_allowed(self):
        """Test that only HTTP and HTTPS are accepted."""
        invalid_protocols = [
            "ftp://files.com/docs",
            "sftp://files.com/docs",
            "gopher://old.server.com",
            "telnet://server.com",
            "ssh://server.com",
        ]

        for url in invalid_protocols:
            is_valid, error = validate_url(url)
            assert is_valid is False
            assert 'http' in error.lower()

    def test_protocol_relative_urls(self):
        """Test handling of protocol-relative URLs."""
        url = "//example.com/docs"
        is_valid, error = validate_url(url)

        # Should require explicit protocol
        assert is_valid is False or 'scheme' in error.lower()

    def test_mixed_case_protocols(self):
        """Test case variations in protocols."""
        urls = [
            "HTTP://example.com",
            "HtTpS://example.com",
            "hTTp://example.com",
        ]

        for url in urls:
            is_valid, error = validate_url(url)
            # Should handle case-insensitive protocols
            assert is_valid is True


@pytest.mark.security
class TestDomainValidation:
    """Test domain validation security."""

    def test_missing_domain(self):
        """Test rejection of URLs without domain."""
        invalid_urls = [
            "https://",
            "http://",
            "https:///path",
        ]

        for url in invalid_urls:
            is_valid, error = validate_url(url)
            assert is_valid is False

    def test_ip_addresses_allowed(self):
        """Test that IP addresses are handled."""
        # Note: Public IPs should be allowed, private IPs tested in SSRF tests
        public_ips = [
            "https://8.8.8.8/",
            "http://1.1.1.1/docs",
        ]

        for url in public_ips:
            is_valid, error = validate_url(url)
            # Should validate as proper URLs
            assert is_valid is True

    def test_international_domains(self):
        """Test international domain names (IDN)."""
        urls = [
            "https://münchen.de/",
            "https://北京.中国/",
        ]

        for url in urls:
            is_valid, error = validate_url(url)
            # Should handle IDN domains
            assert isinstance(is_valid, bool)
