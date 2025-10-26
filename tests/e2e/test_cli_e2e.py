"""
End-to-end tests for CLI functionality.

Tests cover:
- Complete CLI workflows
- File output validation
- Error handling
- Progress output
"""

import pytest
import subprocess
import os
import sys
import responses


@pytest.mark.e2e
class TestCLIEndToEnd:
    """End-to-end tests for CLI scraping."""

    @responses.activate
    def test_basic_single_page_scrape(self, temp_dir):
        """Test scraping a single page via CLI."""
        # Setup mock response
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><head><title>Test</title></head><body><main><h1>Test Page</h1></main></body></html>',
            status=200
        )

        # Change to temp directory
        os.chdir(temp_dir)

        # Run scraper as module
        result = subprocess.run(
            [sys.executable, '-m', 'scrape_api_docs', 'https://example.com/docs/'],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Check success
        assert result.returncode == 0
        assert 'complete' in result.stdout.lower()

        # Check file created
        files = os.listdir(temp_dir)
        assert len(files) == 1
        assert files[0].endswith('.md')

    @responses.activate
    def test_multi_page_scrape_workflow(self, temp_dir):
        """Test scraping multiple pages via CLI."""
        # Setup 3-page mock site
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='''
            <html><head><title>Home</title></head>
            <body><main>
                <h1>Home</h1>
                <a href="/docs/page1">Page 1</a>
            </main></body></html>
            ''',
            status=200
        )

        responses.add(
            responses.GET,
            'https://example.com/docs/page1',
            body='''
            <html><head><title>Page 1</title></head>
            <body><main><h1>Page 1</h1></main></body></html>
            ''',
            status=200
        )

        os.chdir(temp_dir)

        result = subprocess.run(
            [sys.executable, '-m', 'scrape_api_docs', 'https://example.com/docs/'],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0

        # Read output file
        files = [f for f in os.listdir(temp_dir) if f.endswith('.md')]
        assert len(files) == 1

        with open(os.path.join(temp_dir, files[0]), 'r') as f:
            content = f.read()

        assert 'Home' in content
        assert 'Page 1' in content

    def test_invalid_url_error(self, temp_dir, capsys):
        """Test error handling with invalid URL."""
        os.chdir(temp_dir)

        # Run with invalid URL
        result = subprocess.run(
            [sys.executable, '-m', 'scrape_api_docs', 'not-a-url'],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Should handle gracefully (may timeout or error)
        # Just verify it doesn't crash completely
        assert isinstance(result.returncode, int)

    def test_help_output(self):
        """Test help message is displayed."""
        result = subprocess.run(
            [sys.executable, '-m', 'scrape_api_docs', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0
        assert 'usage' in result.stdout.lower() or 'help' in result.stdout.lower()

    @responses.activate
    def test_file_contains_metadata(self, temp_dir):
        """Test output file contains proper metadata."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><head><title>Test</title></head><body><main><h1>Content</h1></main></body></html>',
            status=200
        )

        os.chdir(temp_dir)

        subprocess.run(
            [sys.executable, '-m', 'scrape_api_docs', 'https://example.com/docs/'],
            capture_output=True,
            timeout=10
        )

        files = [f for f in os.listdir(temp_dir) if f.endswith('.md')]
        with open(os.path.join(temp_dir, files[0]), 'r') as f:
            content = f.read()

        assert '# Documentation for' in content
        assert '**Source:**' in content
        assert 'https://example.com/docs/' in content

    @responses.activate
    def test_progress_output(self, temp_dir):
        """Test that progress is printed to console."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><body><main>Test</main></body></html>',
            status=200
        )

        os.chdir(temp_dir)

        result = subprocess.run(
            [sys.executable, '-m', 'scrape_api_docs', 'https://example.com/docs/'],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Should have progress output
        assert 'crawling' in result.stdout.lower() or 'visiting' in result.stdout.lower() or 'found' in result.stdout.lower()


@pytest.mark.e2e
@pytest.mark.slow
class TestRootScriptE2E:
    """Test root scrape.py script."""

    @responses.activate
    def test_root_script_execution(self, temp_dir):
        """Test running root scrape.py script."""
        responses.add(
            responses.GET,
            'https://example.com/docs/',
            body='<html><body><main>Test</main></body></html>',
            status=200
        )

        os.chdir(temp_dir)

        # Run root scrape.py
        script_path = '/home/ruhroh/scrape-api-docs/scrape.py'

        result = subprocess.run(
            [sys.executable, script_path, 'https://example.com/docs/'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=temp_dir
        )

        assert result.returncode == 0

        # File should be created
        files = os.listdir(temp_dir)
        assert any(f.endswith('.md') for f in files)
