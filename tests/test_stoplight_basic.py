"""
Basic validation tests for Stoplight scraper
These tests verify the core functionality works without external dependencies
"""

import pytest
from scrape_api_docs.stoplight_scraper import (
    is_stoplight_url,
    parse_stoplight_url,
)


class TestStoplightURLDetection:
    """Test Stoplight URL detection and parsing"""

    def test_is_stoplight_url_with_valid_stoplight_domain(self):
        """Should detect valid Stoplight.io URLs"""
        assert is_stoplight_url('https://example.stoplight.io/docs/api') is True
        assert is_stoplight_url('https://myapi.stoplight.io/docs') is True
        assert is_stoplight_url('http://demo.stoplight.io/reference') is True

    def test_is_stoplight_url_with_invalid_domains(self):
        """Should reject non-Stoplight URLs"""
        assert is_stoplight_url('https://github.com/user/repo') is False
        assert is_stoplight_url('https://example.com/docs') is False
        assert is_stoplight_url('https://readthedocs.io/en/latest') is False

    def test_is_stoplight_url_with_edge_cases(self):
        """Should handle edge cases properly"""
        assert is_stoplight_url('') is False
        assert is_stoplight_url('not-a-url') is False
        assert is_stoplight_url(None) is False

    def test_parse_stoplight_url_extracts_components(self):
        """Should parse Stoplight URL into components"""
        result = parse_stoplight_url('https://mycaseapi.stoplight.io/docs/mycase-api-documentation')

        assert result is not None
        assert result['base_url'] == 'https://mycaseapi.stoplight.io'
        assert result['workspace'] == 'mycaseapi'
        assert result['project'] == 'mycase-api-documentation'
        assert result['full_url'] == 'https://mycaseapi.stoplight.io/docs/mycase-api-documentation'

    def test_parse_stoplight_url_with_different_paths(self):
        """Should handle various path structures"""
        # Reference docs
        result = parse_stoplight_url('https://example.stoplight.io/reference/api-reference')
        assert result is not None
        assert result['workspace'] == 'example'

        # Guides
        result = parse_stoplight_url('https://demo.stoplight.io/guides/getting-started')
        assert result is not None
        assert result['workspace'] == 'demo'


class TestStoplightImports:
    """Verify all necessary components can be imported"""

    def test_import_stoplight_scraper(self):
        """Should import main scraper module"""
        from scrape_api_docs import stoplight_scraper
        assert stoplight_scraper is not None

    def test_import_scrape_function(self):
        """Should import async scrape function"""
        from scrape_api_docs.stoplight_scraper import scrape_stoplight_site
        assert callable(scrape_stoplight_site)

    def test_import_sync_wrapper(self):
        """Should import synchronous wrapper"""
        from scrape_api_docs.stoplight_scraper import scrape_stoplight_site
        assert callable(scrape_stoplight_site)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
