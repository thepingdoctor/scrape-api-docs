"""
Pytest configuration and shared fixtures for test suite.

This module provides common test fixtures, mock data, and utilities
used across all test modules.
"""

import pytest
import responses
from typing import Dict, List
from unittest.mock import Mock, MagicMock
import tempfile
import os
import shutil


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def simple_html():
    """Simple valid HTML page with main content."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <nav>Navigation</nav>
        <main>
            <h1>Documentation</h1>
            <p>Main content here</p>
            <a href="/docs/page1">Page 1</a>
        </main>
        <footer>Footer</footer>
    </body>
    </html>
    """


@pytest.fixture
def multi_link_html():
    """HTML page with multiple internal and external links."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Multi Link Page</title></head>
    <body>
        <main>
            <h1>Links</h1>
            <a href="/docs/page1">Internal 1</a>
            <a href="/docs/page2">Internal 2</a>
            <a href="https://external.com">External</a>
            <a href="/other/page">Different path</a>
            <a href="#fragment">Fragment</a>
        </main>
    </body>
    </html>
    """


@pytest.fixture
def complex_html():
    """Complex HTML with nested structures, tables, code blocks."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Complex Documentation</title></head>
    <body>
        <main>
            <h1>API Reference</h1>
            <h2>Introduction</h2>
            <p>This is a <strong>complex</strong> page with <em>various</em> elements.</p>

            <h3>Code Example</h3>
            <pre><code>def hello():
    print("Hello, World!")</code></pre>

            <h3>Data Table</h3>
            <table>
                <thead>
                    <tr><th>Method</th><th>Description</th></tr>
                </thead>
                <tbody>
                    <tr><td>GET</td><td>Retrieve data</td></tr>
                    <tr><td>POST</td><td>Create data</td></tr>
                </tbody>
            </table>

            <ul>
                <li>Item 1</li>
                <li>Item 2
                    <ul>
                        <li>Nested item</li>
                    </ul>
                </li>
            </ul>
        </main>
    </body>
    </html>
    """


@pytest.fixture
def malformed_html():
    """Malformed HTML to test parser robustness."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Broken Page
    <body>
        <main>
            <h1>Unclosed heading
            <p>Missing closing tags
            <a href="/link">Link</a>
        </main>
    <!-- Missing closing body and html tags -->
    """


@pytest.fixture
def no_main_content_html():
    """HTML without main, article, or content divs."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>No Main</title></head>
    <body>
        <header>Header</header>
        <nav>Navigation</nav>
        <div class="sidebar">Sidebar</div>
        <footer>Footer</footer>
    </body>
    </html>
    """


@pytest.fixture
def article_fallback_html():
    """HTML using article tag instead of main."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Article Page</title></head>
    <body>
        <article>
            <h1>Article Content</h1>
            <p>Content in article tag</p>
        </article>
    </body>
    </html>
    """


@pytest.fixture
def class_selector_html():
    """HTML using .main-content class."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Class Selector</title></head>
    <body>
        <div class="main-content">
            <h1>Main Content Class</h1>
            <p>Content with class selector</p>
        </div>
    </body>
    </html>
    """


# ============================================================================
# URL Test Data
# ============================================================================

@pytest.fixture
def valid_urls():
    """Collection of valid URLs for testing."""
    return [
        "https://example.com/docs/",
        "https://api.example.com/",
        "http://localhost:8000/docs/",
        "https://docs.python.org/3/",
        "https://example.com/docs/api/v1/",
    ]


@pytest.fixture
def invalid_urls():
    """Collection of invalid URLs for testing."""
    return [
        "",
        "not-a-url",
        "ftp://files.com/docs/",
        "file:///etc/passwd",
        "javascript:alert('xss')",
        "data:text/html,<script>alert('xss')</script>",
        "example.com",  # Missing scheme
        "https://",  # Missing domain
        "//example.com",  # Protocol relative (should be handled)
    ]


@pytest.fixture
def ssrf_urls():
    """URLs that could be used for SSRF attacks."""
    return [
        "http://127.0.0.1/",
        "http://localhost/",
        "http://0.0.0.0/",
        "http://169.254.169.254/",  # AWS metadata
        "http://192.168.1.1/",
        "http://10.0.0.1/",
        "http://172.16.0.1/",
    ]


# ============================================================================
# Mock HTTP Responses
# ============================================================================

@pytest.fixture
def mock_responses():
    """Activate responses mock for HTTP requests."""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def mock_site_structure(mock_responses, simple_html):
    """Mock a simple 3-page documentation site."""
    mock_responses.add(
        responses.GET,
        'https://example.com/docs/',
        body="""
        <html><body><main>
            <h1>Home</h1>
            <a href="/docs/page1">Page 1</a>
            <a href="/docs/page2">Page 2</a>
        </main></body></html>
        """,
        status=200
    )

    mock_responses.add(
        responses.GET,
        'https://example.com/docs/page1',
        body="""
        <html><body><main>
            <h1>Page 1</h1>
            <a href="/docs/">Home</a>
            <a href="/docs/page2">Page 2</a>
        </main></body></html>
        """,
        status=200
    )

    mock_responses.add(
        responses.GET,
        'https://example.com/docs/page2',
        body="""
        <html><body><main>
            <h1>Page 2</h1>
            <a href="/docs/">Home</a>
        </main></body></html>
        """,
        status=200
    )

    return mock_responses


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)


@pytest.fixture
def temp_output_file(temp_dir):
    """Create a temporary output file path."""
    return os.path.join(temp_dir, "test_output.md")


# ============================================================================
# Session and State Fixtures
# ============================================================================

@pytest.fixture
def mock_session():
    """Mock requests.Session object."""
    session = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.text = "<html><body><main>Test</main></body></html>"
    response.raise_for_status = MagicMock()
    session.get.return_value = response
    return session


@pytest.fixture
def mock_scraper_state():
    """Mock ScraperState for Streamlit tests."""
    from scrape_api_docs.streamlit_app import ScraperState
    return ScraperState()


# ============================================================================
# Rate Limiter Fixtures
# ============================================================================

@pytest.fixture
def rate_limiter():
    """Create a RateLimiter instance for testing."""
    import sys
    sys.path.insert(0, '/home/ruhroh/scrape-api-docs/examples/rate-limiting')
    from rate_limiter import RateLimiter
    return RateLimiter(requests_per_second=10.0)  # Fast for testing


@pytest.fixture
def token_bucket():
    """Create a TokenBucket instance for testing."""
    import sys
    sys.path.insert(0, '/home/ruhroh/scrape-api-docs/examples/rate-limiting')
    from rate_limiter import TokenBucket
    return TokenBucket(rate=5.0, capacity=10.0)


# ============================================================================
# Parametrize Helpers
# ============================================================================

# Common test cases for URL validation
url_validation_cases = [
    ("https://example.com/docs/", True, ""),
    ("http://localhost:8000/", True, ""),
    ("", False, "URL cannot be empty"),
    ("not-a-url", False, "Invalid URL format"),
    ("ftp://files.com", False, "URL must use http or https"),
]


# Common test cases for filename generation
filename_cases = [
    ("https://example.com/docs/api/", "example_com_docs_api_documentation.md"),
    ("https://api.example.com/", "api_example_com_documentation.md"),
    ("https://example.com/", "example_com_documentation.md"),
    ("https://docs.python.org/3/library/", "docs_python_org_3_library_documentation.md"),
]


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual functions"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for component interactions"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests for full workflows"
    )
    config.addinivalue_line(
        "markers", "security: Security-focused tests"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and benchmark tests"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer to run"
    )


# ============================================================================
# Helper Functions
# ============================================================================

def assert_markdown_contains(markdown: str, *expected_elements: str):
    """Helper to assert markdown contains expected elements."""
    for element in expected_elements:
        assert element in markdown, f"Expected '{element}' in markdown output"


def create_mock_response(status_code: int = 200, text: str = "", headers: Dict = None):
    """Create a mock HTTP response."""
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.headers = headers or {}
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        import requests
        response.raise_for_status.side_effect = requests.exceptions.HTTPError()
    return response
