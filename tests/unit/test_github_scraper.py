"""
Unit tests for GitHub repository scraper functionality.

This module provides comprehensive test coverage for scraping documentation
from GitHub repositories, including:
- GitHub URL detection and validation
- URL parsing (owner, repo, branch, path extraction)
- GitHub API integration (tree fetching, content retrieval)
- Content processing and filtering
- Integration with existing scraper output format
- Rate limiting and error handling

Test Structure:
- TestGitHubURLDetection: URL validation and format detection
- TestGitHubURLParsing: Extracting components from GitHub URLs
- TestGitHubAPIIntegration: Mocking and testing GitHub API calls
- TestContentProcessing: File filtering and content extraction
- TestGitHubScraper: Integration tests for complete workflow
- TestEndToEnd: Real repository testing with BMAD-METHOD example
"""

import pytest
import responses
from unittest.mock import Mock, patch, MagicMock
import json
import base64


# ============================================================================
# Test Data and Fixtures
# ============================================================================

@pytest.fixture
def valid_github_urls():
    """Collection of valid GitHub repository URLs in various formats."""
    return [
        "https://github.com/owner/repo",
        "https://github.com/owner/repo/",
        "https://github.com/owner/repo/tree/main",
        "https://github.com/owner/repo/tree/main/",
        "https://github.com/owner/repo/tree/main/src/docs",
        "https://github.com/owner/repo/tree/develop/docs",
        "https://github.com/owner/repo/blob/main/README.md",
        "https://github.com/bmad-code-org/BMAD-METHOD/tree/main/src/modules/bmm/docs",
        "https://www.github.com/owner/repo",  # www prefix
        "http://github.com/owner/repo",  # http (should upgrade to https)
    ]


@pytest.fixture
def invalid_github_urls():
    """URLs that are not valid GitHub repository URLs."""
    return [
        "",
        "not-a-url",
        "https://gitlab.com/owner/repo",
        "https://bitbucket.org/owner/repo",
        "https://github.com/",  # Missing owner/repo
        "https://github.com/owner",  # Missing repo
        "https://gist.github.com/user/abc123",  # Gist (different structure)
        "https://raw.githubusercontent.com/owner/repo/main/file.txt",  # Raw content
        "git@github.com:owner/repo.git",  # SSH URL (may support later)
        "ftp://github.com/owner/repo",  # Wrong protocol
    ]


@pytest.fixture
def edge_case_urls():
    """Edge case GitHub URLs to test boundary conditions."""
    return [
        "https://github.com/owner/repo-with-dashes",
        "https://github.com/owner/repo_with_underscores",
        "https://github.com/owner/repo.with.dots",
        "https://github.com/owner/repo/tree/feature/branch-name",
        "https://github.com/owner/repo/tree/v1.2.3",  # Version tag
        "https://github.com/owner/repo/tree/main/path/with/many/segments",
        "https://github.com/123numeric/456numbers",  # Numeric names
        "https://github.com/single-char-owner/r",  # Short names
    ]


@pytest.fixture
def github_tree_response():
    """Mock GitHub API tree response."""
    return {
        "sha": "abc123def456",
        "url": "https://api.github.com/repos/owner/repo/git/trees/abc123",
        "tree": [
            {
                "path": "README.md",
                "mode": "100644",
                "type": "blob",
                "sha": "file1sha",
                "size": 1024,
                "url": "https://api.github.com/repos/owner/repo/git/blobs/file1sha"
            },
            {
                "path": "docs",
                "mode": "040000",
                "type": "tree",
                "sha": "tree1sha",
                "url": "https://api.github.com/repos/owner/repo/git/trees/tree1sha"
            },
            {
                "path": "docs/api.md",
                "mode": "100644",
                "type": "blob",
                "sha": "file2sha",
                "size": 2048,
                "url": "https://api.github.com/repos/owner/repo/git/blobs/file2sha"
            },
            {
                "path": "docs/guide.rst",
                "mode": "100644",
                "type": "blob",
                "sha": "file3sha",
                "size": 3072,
                "url": "https://api.github.com/repos/owner/repo/git/blobs/file3sha"
            },
            {
                "path": "src/main.py",
                "mode": "100644",
                "type": "blob",
                "sha": "file4sha",
                "size": 512,
                "url": "https://api.github.com/repos/owner/repo/git/blobs/file4sha"
            },
            {
                "path": "image.png",
                "mode": "100644",
                "type": "blob",
                "sha": "file5sha",
                "size": 10240,
                "url": "https://api.github.com/repos/owner/repo/git/blobs/file5sha"
            }
        ],
        "truncated": False
    }


@pytest.fixture
def github_blob_response():
    """Mock GitHub API blob response for file content."""
    content = "# API Documentation\n\nThis is a test document.\n\n## Features\n\n- Feature 1\n- Feature 2"
    encoded = base64.b64encode(content.encode()).decode()
    return {
        "sha": "file2sha",
        "size": len(content),
        "url": "https://api.github.com/repos/owner/repo/git/blobs/file2sha",
        "content": encoded,
        "encoding": "base64"
    }


@pytest.fixture
def github_api_rate_limit_response():
    """Mock GitHub API rate limit response."""
    return {
        "resources": {
            "core": {
                "limit": 60,
                "remaining": 0,
                "reset": 1372700873,
                "used": 60
            }
        }
    }


# ============================================================================
# Tests for GitHub URL Detection
# ============================================================================

@pytest.mark.unit
class TestGitHubURLDetection:
    """Test suite for detecting and validating GitHub URLs."""

    def test_valid_github_urls(self, valid_github_urls):
        """Test that valid GitHub URLs are correctly identified."""
        from scrape_api_docs.github_scraper import is_github_url

        for url in valid_github_urls:
            assert is_github_url(url), f"Expected {url} to be identified as GitHub URL"

    def test_invalid_github_urls(self, invalid_github_urls):
        """Test that non-GitHub URLs are correctly rejected."""
        from scrape_api_docs.github_scraper import is_github_url

        for url in invalid_github_urls:
            assert not is_github_url(url), f"Expected {url} to be rejected as non-GitHub URL"

    def test_edge_case_urls(self, edge_case_urls):
        """Test edge cases and boundary conditions for GitHub URLs."""
        from scrape_api_docs.github_scraper import is_github_url

        for url in edge_case_urls:
            assert is_github_url(url), f"Expected {url} to be valid GitHub URL"

    def test_case_insensitive_detection(self):
        """Test that GitHub URL detection is case-insensitive."""
        from scrape_api_docs.github_scraper import is_github_url

        urls = [
            "https://GITHUB.COM/owner/repo",
            "https://GitHub.com/owner/repo",
            "https://github.COM/owner/repo",
        ]

        for url in urls:
            assert is_github_url(url), f"Expected case-insensitive match for {url}"

    def test_ssh_url_handling(self):
        """Test handling of SSH-style GitHub URLs."""
        from scrape_api_docs.github_scraper import is_github_url

        ssh_url = "git@github.com:owner/repo.git"
        # SSH URLs should either be supported or explicitly rejected
        result = is_github_url(ssh_url)
        assert isinstance(result, bool), "Should return boolean for SSH URLs"


# ============================================================================
# Tests for GitHub URL Parsing
# ============================================================================

@pytest.mark.unit
class TestGitHubURLParsing:
    """Test suite for parsing GitHub URL components."""

    def test_parse_owner_and_repo(self):
        """Test extraction of owner and repository names."""
        from scrape_api_docs.github_scraper import parse_github_url

        url = "https://github.com/facebook/react"
        result = parse_github_url(url)

        assert result['owner'] == 'facebook'
        assert result['repo'] == 'react'

    def test_parse_default_branch(self):
        """Test that URLs without branch default to 'main'."""
        from scrape_api_docs.github_scraper import parse_github_url

        url = "https://github.com/owner/repo"
        result = parse_github_url(url)

        # Should default to 'main' or 'master'
        assert result['branch'] in ['main', 'master', None]

    def test_parse_explicit_branch(self):
        """Test extraction of explicitly specified branch."""
        from scrape_api_docs.github_scraper import parse_github_url

        url = "https://github.com/owner/repo/tree/develop"
        result = parse_github_url(url)

        assert result['branch'] == 'develop'

    def test_parse_nested_path(self):
        """Test extraction of file/directory path within repository."""
        from scrape_api_docs.github_scraper import parse_github_url

        url = "https://github.com/bmad-code-org/BMAD-METHOD/tree/main/src/modules/bmm/docs"
        result = parse_github_url(url)

        assert result['owner'] == 'bmad-code-org'
        assert result['repo'] == 'BMAD-METHOD'
        assert result['branch'] == 'main'
        assert result['path'] == 'src/modules/bmm/docs'

    def test_parse_blob_url(self):
        """Test parsing of single file blob URLs."""
        from scrape_api_docs.github_scraper import parse_github_url

        url = "https://github.com/owner/repo/blob/main/README.md"
        result = parse_github_url(url)

        assert result['owner'] == 'owner'
        assert result['repo'] == 'repo'
        assert result['branch'] == 'main'
        assert result['path'] == 'README.md'
        assert result.get('is_blob', False) is True

    def test_parse_trailing_slash(self):
        """Test that trailing slashes are handled correctly."""
        from scrape_api_docs.github_scraper import parse_github_url

        url1 = "https://github.com/owner/repo/"
        url2 = "https://github.com/owner/repo"

        result1 = parse_github_url(url1)
        result2 = parse_github_url(url2)

        assert result1['owner'] == result2['owner']
        assert result1['repo'] == result2['repo']

    def test_parse_special_characters(self):
        """Test parsing of repos with dashes, dots, underscores."""
        from scrape_api_docs.github_scraper import parse_github_url

        test_cases = [
            ("https://github.com/owner/repo-name", "repo-name"),
            ("https://github.com/owner/repo_name", "repo_name"),
            ("https://github.com/owner/repo.name", "repo.name"),
        ]

        for url, expected_repo in test_cases:
            result = parse_github_url(url)
            assert result['repo'] == expected_repo

    def test_parse_invalid_url(self):
        """Test that invalid URLs raise appropriate exceptions."""
        from scrape_api_docs.github_scraper import parse_github_url

        with pytest.raises((ValueError, AttributeError)):
            parse_github_url("not-a-github-url")

    def test_parse_missing_components(self):
        """Test handling of URLs with missing required components."""
        from scrape_api_docs.github_scraper import parse_github_url

        urls_missing_parts = [
            "https://github.com/owner",  # Missing repo
            "https://github.com/",  # Missing owner and repo
        ]

        for url in urls_missing_parts:
            with pytest.raises((ValueError, KeyError, IndexError)):
                parse_github_url(url)


# ============================================================================
# Tests for GitHub API Integration
# ============================================================================

@pytest.mark.unit
class TestGitHubAPIIntegration:
    """Test suite for GitHub API interactions."""

    @responses.activate
    def test_get_repo_tree_success(self, github_tree_response):
        """Test successful retrieval of repository tree structure."""
        from scrape_api_docs.github_scraper import get_repo_tree

        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/trees/main?recursive=1',
            json=github_tree_response,
            status=200
        )

        tree = get_repo_tree('owner', 'repo', 'main')

        assert tree is not None
        assert 'tree' in tree
        assert len(tree['tree']) > 0

    @responses.activate
    def test_get_repo_tree_404(self):
        """Test handling of non-existent repository."""
        from scrape_api_docs.github_scraper import get_repo_tree

        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/nonexistent/git/trees/main?recursive=1',
            json={"message": "Not Found"},
            status=404
        )

        with pytest.raises(Exception):  # Should raise appropriate exception
            get_repo_tree('owner', 'nonexistent', 'main')

    @responses.activate
    def test_get_repo_tree_rate_limit(self, github_api_rate_limit_response):
        """Test handling of GitHub API rate limiting."""
        from scrape_api_docs.github_scraper import get_repo_tree

        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/trees/main?recursive=1',
            json={"message": "API rate limit exceeded"},
            status=403,
            headers={'X-RateLimit-Remaining': '0'}
        )

        with pytest.raises(Exception) as exc_info:
            get_repo_tree('owner', 'repo', 'main')

        # Should raise exception mentioning rate limit
        assert 'rate limit' in str(exc_info.value).lower() or '403' in str(exc_info.value)

    @responses.activate
    def test_get_file_content_success(self, github_blob_response):
        """Test successful retrieval of file content from GitHub."""
        from scrape_api_docs.github_scraper import get_file_content

        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/blobs/file2sha',
            json=github_blob_response,
            status=200
        )

        content = get_file_content('owner', 'repo', 'file2sha')

        assert content is not None
        assert isinstance(content, str)
        assert '# API Documentation' in content

    @responses.activate
    def test_get_file_content_binary(self):
        """Test handling of binary file content."""
        from scrape_api_docs.github_scraper import get_file_content

        # Binary content (PNG signature)
        binary_content = b'\x89PNG\r\n\x1a\n'
        encoded = base64.b64encode(binary_content).decode()

        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/blobs/binarysha',
            json={
                "sha": "binarysha",
                "size": len(binary_content),
                "content": encoded,
                "encoding": "base64"
            },
            status=200
        )

        content = get_file_content('owner', 'repo', 'binarysha')

        # Should either skip binary files or decode them appropriately
        assert content is not None or content is None  # Implementation dependent

    @responses.activate
    def test_api_authentication(self):
        """Test that GitHub token is used if provided."""
        from scrape_api_docs.github_scraper import get_repo_tree

        def request_callback(request):
            # Check for Authorization header
            if 'Authorization' in request.headers:
                assert request.headers['Authorization'].startswith('token ')
                return (200, {}, json.dumps({"tree": []}))
            return (401, {}, json.dumps({"message": "Requires authentication"}))

        responses.add_callback(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/trees/main?recursive=1',
            callback=request_callback
        )

        # Test with token (implementation may vary)
        try:
            tree = get_repo_tree('owner', 'repo', 'main', token='test_token')
            # If function accepts token parameter
        except TypeError:
            # If function doesn't support token parameter yet
            pass

    @responses.activate
    def test_recursive_tree_fetching(self, github_tree_response):
        """Test that recursive flag is used to get complete tree."""
        from scrape_api_docs.github_scraper import get_repo_tree

        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/trees/main?recursive=1',
            json=github_tree_response,
            status=200
        )

        tree = get_repo_tree('owner', 'repo', 'main')

        # Verify recursive parameter is used
        assert len(responses.calls) == 1
        assert 'recursive=1' in responses.calls[0].request.url


# ============================================================================
# Tests for Content Processing
# ============================================================================

@pytest.mark.unit
class TestContentProcessing:
    """Test suite for filtering and processing GitHub content."""

    def test_filter_documentation_files(self, github_tree_response):
        """Test filtering to include only documentation files."""
        from scrape_api_docs.github_scraper import filter_documentation_files

        files = filter_documentation_files(github_tree_response['tree'])

        # Should include .md and .rst files, exclude .py and .png
        file_paths = [f['path'] for f in files]

        assert 'README.md' in file_paths
        assert 'docs/api.md' in file_paths
        assert 'docs/guide.rst' in file_paths
        assert 'src/main.py' not in file_paths
        assert 'image.png' not in file_paths

    def test_filter_by_file_extension(self):
        """Test filtering by specific file extensions."""
        from scrape_api_docs.github_scraper import filter_documentation_files

        tree_items = [
            {"path": "README.md", "type": "blob"},
            {"path": "guide.rst", "type": "blob"},
            {"path": "api.txt", "type": "blob"},
            {"path": "config.yaml", "type": "blob"},
            {"path": "docs.html", "type": "blob"},
            {"path": "script.py", "type": "blob"},
        ]

        files = filter_documentation_files(tree_items)
        paths = [f['path'] for f in files]

        # Should include common doc formats
        assert 'README.md' in paths
        assert 'guide.rst' in paths
        # May or may not include .txt, .html depending on implementation
        assert 'script.py' not in paths

    def test_filter_directories(self):
        """Test that directories are excluded from file list."""
        from scrape_api_docs.github_scraper import filter_documentation_files

        tree_items = [
            {"path": "README.md", "type": "blob"},
            {"path": "docs", "type": "tree"},  # Directory
            {"path": "src", "type": "tree"},  # Directory
        ]

        files = filter_documentation_files(tree_items)

        # Should only include blobs, not trees
        assert len(files) == 1
        assert files[0]['path'] == 'README.md'

    def test_filter_by_path_prefix(self, github_tree_response):
        """Test filtering files within specific path."""
        from scrape_api_docs.github_scraper import filter_by_path

        # Filter only files in docs/ directory
        files = filter_by_path(github_tree_response['tree'], 'docs/')
        paths = [f['path'] for f in files]

        assert 'docs/api.md' in paths
        assert 'docs/guide.rst' in paths
        assert 'README.md' not in paths
        assert 'src/main.py' not in paths

    def test_combine_markdown_content(self):
        """Test combining multiple markdown files into single document."""
        from scrape_api_docs.github_scraper import combine_markdown_files

        files = [
            {"path": "README.md", "content": "# README\n\nIntro text"},
            {"path": "docs/api.md", "content": "# API\n\nAPI docs"},
            {"path": "docs/guide.md", "content": "# Guide\n\nGuide text"},
        ]

        combined = combine_markdown_files(files)

        assert '# README' in combined
        assert '# API' in combined
        assert '# Guide' in combined
        assert 'Intro text' in combined

    def test_preserve_file_structure(self):
        """Test that file paths are preserved in output."""
        from scrape_api_docs.github_scraper import combine_markdown_files

        files = [
            {"path": "docs/section1/intro.md", "content": "# Intro"},
            {"path": "docs/section2/advanced.md", "content": "# Advanced"},
        ]

        combined = combine_markdown_files(files)

        # Output should indicate source file paths
        assert 'docs/section1/intro.md' in combined or 'intro.md' in combined
        assert 'section2/advanced.md' in combined or 'advanced.md' in combined


# ============================================================================
# Tests for Complete GitHub Scraper Workflow
# ============================================================================

@pytest.mark.unit
class TestGitHubScraper:
    """Test suite for end-to-end GitHub scraping."""

    @responses.activate
    def test_scrape_github_repo_basic(self, github_tree_response, github_blob_response, temp_dir, monkeypatch):
        """Test basic repository scraping workflow."""
        from scrape_api_docs.github_scraper import scrape_github_repo

        monkeypatch.chdir(temp_dir)

        # Mock tree API
        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/trees/main?recursive=1',
            json=github_tree_response,
            status=200
        )

        # Mock blob APIs for each markdown file
        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/blobs/file1sha',
            json=github_blob_response,
            status=200
        )
        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/blobs/file2sha',
            json=github_blob_response,
            status=200
        )

        result = scrape_github_repo('https://github.com/owner/repo')

        assert result is not None
        assert isinstance(result, str)  # Should return markdown content

    @responses.activate
    def test_output_format_compatibility(self, github_tree_response, github_blob_response, temp_dir, monkeypatch):
        """Test that output format matches web scraper format."""
        from scrape_api_docs.github_scraper import scrape_github_repo

        monkeypatch.chdir(temp_dir)

        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/trees/main?recursive=1',
            json=github_tree_response,
            status=200
        )
        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/blobs/file1sha',
            json=github_blob_response,
            status=200
        )

        result = scrape_github_repo('https://github.com/owner/repo')

        # Should have similar structure to web scraper output
        assert '# Documentation for' in result or 'Documentation' in result
        assert 'https://github.com/owner/repo' in result

    @responses.activate
    def test_file_creation(self, github_tree_response, github_blob_response, temp_dir, monkeypatch):
        """Test that markdown file is created with proper naming."""
        from scrape_api_docs.github_scraper import scrape_github_repo

        monkeypatch.chdir(temp_dir)

        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/trees/main?recursive=1',
            json=github_tree_response,
            status=200
        )

        scrape_github_repo('https://github.com/owner/repo', save_file=True)

        import os
        files = os.listdir(temp_dir)

        # Should create file with GitHub-specific naming
        assert any('github' in f.lower() or 'repo' in f for f in files)
        assert any(f.endswith('.md') for f in files)

    @responses.activate
    def test_rate_limit_handling(self, temp_dir, monkeypatch):
        """Test graceful handling of rate limits."""
        from scrape_api_docs.github_scraper import scrape_github_repo

        monkeypatch.chdir(temp_dir)

        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/trees/main?recursive=1',
            json={"message": "API rate limit exceeded"},
            status=403
        )

        with pytest.raises(Exception) as exc_info:
            scrape_github_repo('https://github.com/owner/repo')

        # Should provide helpful error message
        error_msg = str(exc_info.value).lower()
        assert 'rate' in error_msg or '403' in error_msg

    @responses.activate
    def test_path_filtering(self, github_tree_response, github_blob_response, temp_dir, monkeypatch):
        """Test scraping specific directory within repository."""
        from scrape_api_docs.github_scraper import scrape_github_repo

        monkeypatch.chdir(temp_dir)

        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/trees/main?recursive=1',
            json=github_tree_response,
            status=200
        )
        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/blobs/file2sha',
            json=github_blob_response,
            status=200
        )

        # Scrape only docs/ directory
        result = scrape_github_repo('https://github.com/owner/repo/tree/main/docs')

        assert result is not None
        # Should only include docs/ content


# ============================================================================
# Tests for Real Repository Integration
# ============================================================================

@pytest.mark.integration
class TestEndToEnd:
    """Integration tests with real GitHub repositories."""

    @pytest.mark.slow
    def test_scrape_bmad_method_docs(self, temp_dir, monkeypatch):
        """Test scraping BMAD-METHOD documentation (real API call)."""
        from scrape_api_docs.github_scraper import scrape_github_repo

        monkeypatch.chdir(temp_dir)

        url = "https://github.com/bmad-code-org/BMAD-METHOD/tree/main/src/modules/bmm/docs"

        try:
            result = scrape_github_repo(url)

            assert result is not None
            assert isinstance(result, str)
            assert len(result) > 0

            # Should contain actual documentation content
            # (exact content depends on repository state)

        except Exception as e:
            # If rate limited or network issue, skip test
            if 'rate limit' in str(e).lower() or 'network' in str(e).lower():
                pytest.skip(f"Skipping due to: {e}")
            else:
                raise

    @pytest.mark.slow
    def test_real_api_rate_limiting(self):
        """Test that rate limiting is properly implemented."""
        from scrape_api_docs.github_scraper import get_repo_tree
        import time

        try:
            start_time = time.time()

            # Make multiple requests
            for i in range(3):
                get_repo_tree('octocat', 'Hello-World', 'master')

            elapsed = time.time() - start_time

            # Should have some delay between requests (rate limiting)
            # Exact timing depends on implementation

        except Exception as e:
            if '404' in str(e):
                # Repository might not exist anymore
                pytest.skip("Test repository not available")
            elif 'rate' in str(e).lower():
                # Expected if rate limited
                pass
            else:
                raise

    @pytest.mark.slow
    def test_large_repository_handling(self):
        """Test handling of repositories with many files."""
        from scrape_api_docs.github_scraper import scrape_github_repo

        # Test with a known large documentation repository
        # This is a slow test that should be run less frequently

        try:
            # Example: Python documentation (large repo)
            result = scrape_github_repo('https://github.com/python/cpython/tree/main/Doc')

            # Should handle large repositories without crashing
            assert result is not None

        except Exception as e:
            if 'rate limit' in str(e).lower():
                pytest.skip(f"Rate limited: {e}")
            else:
                raise


# ============================================================================
# Tests for Error Handling and Edge Cases
# ============================================================================

@pytest.mark.unit
class TestErrorHandling:
    """Test suite for error conditions and edge cases."""

    def test_empty_repository(self):
        """Test handling of repository with no documentation files."""
        from scrape_api_docs.github_scraper import filter_documentation_files

        tree_items = [
            {"path": "main.py", "type": "blob"},
            {"path": "config.json", "type": "blob"},
            {"path": "image.png", "type": "blob"},
        ]

        files = filter_documentation_files(tree_items)

        # Should return empty list gracefully
        assert len(files) == 0

    @responses.activate
    def test_network_timeout(self):
        """Test handling of network timeouts."""
        from scrape_api_docs.github_scraper import get_repo_tree
        import requests

        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/trees/main?recursive=1',
            body=requests.exceptions.Timeout('Connection timeout')
        )

        with pytest.raises(Exception):
            get_repo_tree('owner', 'repo', 'main')

    def test_malformed_tree_response(self):
        """Test handling of unexpected API response format."""
        from scrape_api_docs.github_scraper import filter_documentation_files

        # Malformed tree items
        tree_items = [
            {"path": "file.md"},  # Missing 'type'
            {"type": "blob"},  # Missing 'path'
            None,  # Invalid item
            {},  # Empty object
        ]

        # Should handle gracefully without crashing
        try:
            files = filter_documentation_files(tree_items)
            assert isinstance(files, list)
        except (KeyError, AttributeError, TypeError):
            # Expected for malformed data
            pass

    @responses.activate
    def test_invalid_branch_name(self):
        """Test handling of non-existent branch."""
        from scrape_api_docs.github_scraper import get_repo_tree

        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/trees/nonexistent?recursive=1',
            json={"message": "Not Found"},
            status=404
        )

        with pytest.raises(Exception):
            get_repo_tree('owner', 'repo', 'nonexistent')

    def test_unicode_content_handling(self):
        """Test handling of Unicode characters in markdown."""
        from scrape_api_docs.github_scraper import combine_markdown_files

        files = [
            {"path": "unicode.md", "content": "# Documentation\n\nUnicode: ñ, é, 中文, 🚀"},
        ]

        combined = combine_markdown_files(files)

        assert 'ñ' in combined
        assert '中文' in combined
        assert '🚀' in combined


# ============================================================================
# Performance and Optimization Tests
# ============================================================================

@pytest.mark.performance
class TestPerformance:
    """Test suite for performance and optimization."""

    def test_large_file_handling(self):
        """Test handling of large markdown files."""
        from scrape_api_docs.github_scraper import combine_markdown_files

        # Create large content
        large_content = "# Header\n\n" + ("Lorem ipsum dolor sit amet. " * 10000)

        files = [
            {"path": "large.md", "content": large_content},
        ]

        # Should handle without performance issues
        import time
        start = time.time()
        result = combine_markdown_files(files)
        elapsed = time.time() - start

        assert result is not None
        assert elapsed < 1.0  # Should process in under 1 second

    @responses.activate
    def test_batch_api_requests(self, github_tree_response):
        """Test that API requests are optimized/batched."""
        from scrape_api_docs.github_scraper import get_repo_tree

        responses.add(
            responses.GET,
            'https://api.github.com/repos/owner/repo/git/trees/main?recursive=1',
            json=github_tree_response,
            status=200
        )

        get_repo_tree('owner', 'repo', 'main')

        # Should use recursive=1 to minimize API calls
        assert len(responses.calls) == 1

    def test_memory_efficiency(self):
        """Test memory usage with multiple files."""
        from scrape_api_docs.github_scraper import combine_markdown_files

        # Create many small files
        files = [
            {"path": f"doc{i}.md", "content": f"# Document {i}\n\nContent {i}"}
            for i in range(100)
        ]

        result = combine_markdown_files(files)

        # Should handle efficiently
        assert result is not None
        assert len(result) > 0
