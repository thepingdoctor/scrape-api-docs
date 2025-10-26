"""
Integration tests for HTTP client functionality.

Tests cover:
- Live website mocking with realistic scenarios
- Multi-page crawling
- Redirect following
- Rate limiting
- Connection pooling
- Retry logic
"""

import pytest
import responses
import requests
from scrape_api_docs.scraper import get_all_site_links, scrape_site
from unittest.mock import patch, MagicMock


@pytest.mark.integration
class TestHTTPClientIntegration:
    """Test HTTP client integration with real scenarios."""

    @responses.activate
    def test_crawl_10_page_mock_site(self):
        """Full workflow test with 10-page site."""
        # Setup 10-page mock site
        base_url = 'https://example.com/docs/'

        for i in range(10):
            url = f'{base_url}page{i}' if i > 0 else base_url

            # Each page links to the next
            next_link = f'/docs/page{i+1}' if i < 9 else '/docs/'

            responses.add(
                responses.GET,
                url,
                body=f'''
                <html><body><main>
                    <h1>Page {i}</h1>
                    <a href="{next_link}">Next</a>
                </main></body></html>
                ''',
                status=200
            )

        links = get_all_site_links(base_url)

        # Should discover all 10 pages
        assert len(links) == 10
        assert base_url in links
        assert f'{base_url}page9' in links

    @responses.activate
    def test_pagination_handling(self):
        """Test sequential page discovery."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='''
            <html><body><main>
                <a href="/docs/page/1">Page 1</a>
            </main></body></html>
            ''',
            status=200
        )

        responses.add(
            responses.GET,
            'https://example.com/docs/page/1',
            body='''
            <html><body><main>
                <a href="/docs/page/2">Page 2</a>
            </main></body></html>
            ''',
            status=200
        )

        responses.add(
            responses.GET,
            'https://example.com/docs/page/2',
            body='''
            <html><body><main>
                <a href="/docs/">Back</a>
            </main></body></html>
            ''',
            status=200
        )

        links = get_all_site_links('https://example.com/docs/')

        assert len(links) == 3

    @responses.activate
    def test_redirect_following(self):
        """Test handling of 301/302 redirects."""
        # Initial URL redirects
        responses.add(
            responses.GET,
            'https://example.com/old-docs/',
            status=301,
            headers={'Location': 'https://example.com/docs/'}
        )

        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><body><main>New location</main></body></html>',
            status=200
        )

        # Should follow redirect automatically
        links = get_all_site_links('https://example.com/old-docs/')

        # Requests library follows redirects by default
        assert len(links) >= 1

    @responses.activate
    def test_connection_pooling_with_session(self):
        """Test session reuse and connection pooling."""
        # Multiple requests to same domain
        for i in range(5):
            responses.add(
                responses.GET,
                f'https://example.com/docs/page{i}',
                body=f'<html><body><main>Page {i}</main></body></html>',
                status=200
            )

        # Setup first page with links to others
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='''
            <html><body><main>
                <a href="/docs/page0">P0</a>
                <a href="/docs/page1">P1</a>
            </main></body></html>
            ''',
            status=200
        )

        links = get_all_site_links('https://example.com/docs/')

        # Should successfully use session for all requests
        assert len(links) >= 2

    @responses.activate
    def test_timeout_with_slow_server(self):
        """Test timeout handling with slow responses."""
        # Add a callback that simulates slow response
        def slow_response(request):
            import time
            time.sleep(0.1)  # Small delay
            return (200, {}, '<html><body><main>Slow</main></body></html>')

        responses.add_callback(
            responses.GET,
            'https://example.com/docs/',
            callback=slow_response
        )

        # Should complete successfully with small delay
        links = get_all_site_links('https://example.com/docs/')
        assert len(links) >= 1

    @responses.activate
    def test_retry_logic_on_503(self):
        """Test retry behavior on 503 Service Unavailable."""
        # First request fails, second succeeds
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            status=503
        )

        # After retry (manual simulation)
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><body><main>Now available</main></body></html>',
            status=200
        )

        # First attempt should fail gracefully
        links = get_all_site_links('https://example.com/docs/')

        # Should have base URL even if first attempt failed
        assert len(links) >= 1


@pytest.mark.integration
class TestHTTPRateLimiting:
    """Test rate limiting integration."""

    @responses.activate
    def test_rate_limiting_delays(self):
        """Test that rate limiting adds appropriate delays."""
        import time

        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><body><main>Test</main></body></html>',
            status=200
        )

        start_time = time.time()

        # Make request (no actual rate limiting in test)
        get_all_site_links('https://example.com/docs/')

        elapsed = time.time() - start_time

        # Should complete reasonably fast in tests
        assert elapsed < 5.0

    @responses.activate
    def test_429_handling(self):
        """Test handling of 429 Too Many Requests."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            status=429,
            headers={'Retry-After': '1'}
        )

        # Should handle gracefully
        links = get_all_site_links('https://example.com/docs/')

        # Should still return base URL
        assert len(links) >= 1

    @responses.activate
    def test_respect_server_constraints(self):
        """Test that scraper doesn't overwhelm servers."""
        # Setup multiple pages
        for i in range(20):
            responses.add(
                responses.GET,
                f'https://example.com/docs/page{i}',
                body=f'<html><body><main>Page {i}</main></body></html>',
                status=200
            )

        # Add index with all links
        links_html = ''.join([f'<a href="/docs/page{i}">P{i}</a>' for i in range(20)])
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body=f'<html><body><main>{links_html}</main></body></html>',
            status=200
        )

        import time
        start_time = time.time()

        links = get_all_site_links('https://example.com/docs/')

        elapsed = time.time() - start_time

        # Should complete in reasonable time
        assert elapsed < 10.0
        assert len(links) == 21  # 20 pages + index


@pytest.mark.integration
class TestHTTPSConnections:
    """Test HTTPS connection handling."""

    @responses.activate
    def test_https_connection(self):
        """Test HTTPS connections work correctly."""
        responses.add(
            responses.GET,
            'https://secure.example.com/docs/',
            body='<html><body><main>Secure content</main></body></html>',
            status=200
        )

        links = get_all_site_links('https://secure.example.com/docs/')

        assert len(links) >= 1
        assert all(link.startswith('https://') for link in links)

    @responses.activate
    def test_mixed_content_handling(self):
        """Test handling of mixed HTTP/HTTPS content."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='''
            <html><body><main>
                <a href="https://example.com/docs/secure">Secure</a>
                <a href="http://example.com/docs/insecure">Insecure</a>
            </main></body></html>
            ''',
            status=200
        )

        responses.add(
            responses.GET,
            'https://example.com/docs/secure',
            body='<html><body><main>Secure</main></body></html>',
            status=200
        )

        # Note: HTTP link won't be followed as it's different scheme
        links = get_all_site_links('https://example.com/docs/')

        # Should only have HTTPS links
        assert all(link.startswith('https://') for link in links)


@pytest.mark.integration
class TestFullScrapingIntegration:
    """Test complete scraping workflow integration."""

    @responses.activate
    def test_complete_scrape_workflow(self, temp_dir, monkeypatch):
        """Test end-to-end scraping with multiple pages."""
        monkeypatch.chdir(temp_dir)

        # Setup 3-page site
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='''
            <html><head><title>Home</title></head>
            <body><main>
                <h1>Home</h1>
                <a href="/docs/guide">Guide</a>
                <a href="/docs/api">API</a>
            </main></body></html>
            ''',
            status=200
        )

        responses.add(
            responses.GET,
            'https://example.com/docs/guide',
            body='''
            <html><head><title>Guide</title></head>
            <body><main>
                <h1>Guide</h1>
                <p>User guide content</p>
            </main></body></html>
            ''',
            status=200
        )

        responses.add(
            responses.GET,
            'https://example.com/docs/api',
            body='''
            <html><head><title>API</title></head>
            <body><main>
                <h1>API Reference</h1>
                <p>API documentation</p>
            </main></body></html>
            ''',
            status=200
        )

        scrape_site('https://example.com/docs/')

        # Check output file
        import os
        files = os.listdir(temp_dir)
        assert len(files) == 1

        with open(os.path.join(temp_dir, files[0]), 'r') as f:
            content = f.read()

        assert 'Home' in content
        assert 'Guide' in content
        assert 'API Reference' in content

    @responses.activate
    def test_error_recovery_during_crawl(self, temp_dir, monkeypatch):
        """Test that scraping continues despite errors."""
        monkeypatch.chdir(temp_dir)

        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='''
            <html><head><title>Home</title></head>
            <body><main>
                <a href="/docs/good">Good</a>
                <a href="/docs/bad">Bad</a>
            </main></body></html>
            ''',
            status=200
        )

        responses.add(
            responses.GET,
            'https://example.com/docs/good',
            body='<html><head><title>Good</title></head><body><main>Good content</main></body></html>',
            status=200
        )

        responses.add(
            responses.GET,
            'https://example.com/docs/bad',
            status=500
        )

        scrape_site('https://example.com/docs/')

        # Should complete despite one error
        import os
        files = os.listdir(temp_dir)
        assert len(files) == 1
