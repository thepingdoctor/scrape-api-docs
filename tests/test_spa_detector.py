"""
Tests for SPA detection heuristics.
"""

import pytest
from scrape_api_docs.spa_detector import SPADetector, detect_spa


def test_detect_react_spa():
    """Test detection of React SPA."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>React App</title></head>
    <body>
        <div id="root"></div>
        <script src="/static/js/main.js"></script>
    </body>
    </html>
    """

    detector = SPADetector(content_threshold=500)
    assert detector.needs_javascript_rendering('https://example.com', html)


def test_detect_vue_spa():
    """Test detection of Vue SPA."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Vue App</title></head>
    <body>
        <div id="app" v-app></div>
    </body>
    </html>
    """

    detector = SPADetector()
    assert detector.needs_javascript_rendering('https://example.com', html)


def test_detect_angular_spa():
    """Test detection of Angular SPA."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Angular App</title></head>
    <body>
        <app-root ng-version="15.0.0"></app-root>
    </body>
    </html>
    """

    detector = SPADetector()
    assert detector.needs_javascript_rendering('https://example.com', html)


def test_detect_nextjs_spa():
    """Test detection of Next.js SPA."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Next.js App</title></head>
    <body>
        <div id="__next"></div>
        <script id="__NEXT_DATA__" type="application/json">{"props":{}}</script>
    </body>
    </html>
    """

    detector = SPADetector()
    assert detector.needs_javascript_rendering('https://example.com', html)


def test_detect_static_site():
    """Test that static sites are NOT detected as SPAs."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Static Site</title></head>
    <body>
        <main>
            <h1>Welcome to Documentation</h1>
            <p>This is a static documentation site with lots of content.
            It has multiple paragraphs and sections that are fully rendered
            in the initial HTML without requiring JavaScript execution.
            The content is immediately visible and accessible.</p>
            <section>
                <h2>Getting Started</h2>
                <p>Follow these steps to get started with our API.</p>
                <ul>
                    <li>Step 1: Install the package</li>
                    <li>Step 2: Configure your environment</li>
                    <li>Step 3: Make your first request</li>
                </ul>
            </section>
        </main>
    </body>
    </html>
    """

    detector = SPADetector(content_threshold=100)
    assert not detector.needs_javascript_rendering('https://example.com', html)


def test_detect_docusaurus():
    """Test detection of Docusaurus site."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="generator" content="Docusaurus">
        <title>Docs</title>
    </head>
    <body>
        <div id="__docusaurus"></div>
    </body>
    </html>
    """

    detector = SPADetector()
    assert detector.needs_javascript_rendering('https://example.com', html)


def test_confidence_score():
    """Test confidence score calculation."""
    # React SPA with minimal content
    react_html = """
    <html>
    <body>
        <div id="root" data-reactroot></div>
        <script></script>
    </body>
    </html>
    """

    detector = SPADetector()
    confidence = detector.calculate_spa_confidence(react_html)

    # Should have high confidence (>0.7) for clear SPA indicators
    assert confidence > 0.7


def test_analyze_page_structure():
    """Test page structure analysis."""
    html = """
    <html>
    <body>
        <div id="root"></div>
        <script src="app.js"></script>
        <a href="/page1">Link 1</a>
        <a href="/page2">Link 2</a>
    </body>
    </html>
    """

    detector = SPADetector()
    analysis = detector.analyze_page_structure(html)

    assert analysis['total_scripts'] == 1
    assert analysis['total_links'] == 2
    assert 'root' in str(analysis['root_div_patterns'])


def test_convenience_function():
    """Test convenience detect_spa function."""
    react_html = '<div id="root"></div>'
    assert detect_spa(react_html, 'https://example.com')

    static_html = '<main><h1>Lots of content here</h1><p>More content...</p></main>' * 10
    assert not detect_spa(static_html, 'https://example.com')


def test_threshold_tuning():
    """Test that thresholds can be tuned."""
    minimal_html = '<div id="root">Small content</div>'

    # With low threshold, should detect as SPA
    detector_low = SPADetector(content_threshold=1000)
    assert detector_low.needs_javascript_rendering('', minimal_html)

    # With very high threshold, might not detect (depends on other signals)
    detector_high = SPADetector(content_threshold=10)
    # Result depends on other heuristics, just test it runs
    detector_high.needs_javascript_rendering('', minimal_html)
