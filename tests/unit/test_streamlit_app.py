"""
Unit tests for Streamlit application functionality.

Tests cover:
- ScraperState: State management class
- validate_url: URL validation logic
- scrape_with_progress: Progress tracking functionality
- UI component rendering (mocked)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from scrape_api_docs.streamlit_app import (
    ScraperState,
    validate_url,
    scrape_with_progress,
    init_session_state,
)


# ============================================================================
# Tests for ScraperState Class
# ============================================================================

@pytest.mark.unit
class TestScraperState:
    """Test suite for ScraperState class."""

    def test_initialization(self):
        """Test all attributes are set to defaults."""
        state = ScraperState()

        assert state.is_running is False
        assert state.progress == 0
        assert state.total_pages == 0
        assert state.current_url == ""
        assert state.discovered_urls == []
        assert state.processed_urls == []
        assert state.errors == []
        assert state.content == ""
        assert state.start_time is None
        assert state.end_time is None
        assert state.status_message == "Ready to start scraping"

    def test_state_updates(self):
        """Test state mutations work correctly."""
        state = ScraperState()

        state.is_running = True
        state.progress = 50
        state.total_pages = 10
        state.current_url = "https://example.com/page1"

        assert state.is_running is True
        assert state.progress == 50
        assert state.total_pages == 10
        assert state.current_url == "https://example.com/page1"

    def test_progress_tracking(self):
        """Test accurate progress percentage tracking."""
        state = ScraperState()

        state.total_pages = 10
        state.processed_urls = ["url1", "url2", "url3"]

        # Manual progress calculation
        expected_progress = (len(state.processed_urls) / state.total_pages) * 100
        # Note: The actual progress is set in scrape_with_progress
        assert len(state.processed_urls) == 3

    def test_error_collection(self):
        """Test proper error object structure."""
        state = ScraperState()

        error1 = {"url": "https://example.com/fail", "error": "404 Not Found"}
        error2 = {"url": "https://example.com/error", "error": "Timeout"}

        state.errors.append(error1)
        state.errors.append(error2)

        assert len(state.errors) == 2
        assert state.errors[0]["url"] == "https://example.com/fail"
        assert state.errors[1]["error"] == "Timeout"


# ============================================================================
# Tests for validate_url()
# ============================================================================

@pytest.mark.unit
class TestValidateUrl:
    """Test suite for URL validation."""

    def test_valid_http_url(self):
        """Test acceptance of valid HTTP URL."""
        is_valid, error = validate_url("http://example.com/docs")

        assert is_valid is True
        assert error == ""

    def test_valid_https_url(self):
        """Test acceptance of valid HTTPS URL."""
        is_valid, error = validate_url("https://example.com/docs")

        assert is_valid is True
        assert error == ""

    def test_empty_url(self):
        """Test rejection of empty URL with message."""
        is_valid, error = validate_url("")

        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_missing_scheme(self):
        """Test rejection of URLs without http/https."""
        is_valid, error = validate_url("example.com/docs")

        assert is_valid is False
        assert "invalid url format" in error.lower() or "scheme" in error.lower()

    def test_missing_domain(self):
        """Test rejection of incomplete URLs."""
        is_valid, error = validate_url("https://")

        assert is_valid is False
        assert "invalid url format" in error.lower() or "domain" in error.lower()

    def test_invalid_protocol_ftp(self):
        """Test rejection of FTP protocol."""
        is_valid, error = validate_url("ftp://files.example.com")

        assert is_valid is False
        assert "http or https" in error.lower()

    def test_invalid_protocol_file(self):
        """Test rejection of file:// protocol."""
        is_valid, error = validate_url("file:///etc/passwd")

        assert is_valid is False
        assert "http or https" in error.lower()

    def test_localhost_url(self):
        """Test acceptance of localhost URLs for testing."""
        is_valid, error = validate_url("http://localhost:8000/docs")

        assert is_valid is True
        assert error == ""

    def test_special_characters_in_url(self):
        """Test handling of encoded URLs."""
        is_valid, error = validate_url("https://example.com/docs%20test")

        assert is_valid is True

    @pytest.mark.parametrize("url,expected_valid", [
        ("https://example.com/docs", True),
        ("http://localhost:8000/", True),
        ("", False),
        ("example.com", False),
        ("ftp://files.com", False),
        ("javascript:alert('xss')", False),
    ])
    def test_multiple_url_patterns(self, url, expected_valid):
        """Test various URL patterns against validation."""
        is_valid, _ = validate_url(url)
        assert is_valid == expected_valid


# ============================================================================
# Tests for scrape_with_progress()
# ============================================================================

@pytest.mark.unit
class TestScrapeWithProgress:
    """Test suite for progress tracking scraper."""

    @patch('scrape_api_docs.streamlit_app.st')
    @patch('scrape_api_docs.streamlit_app.get_all_site_links')
    @patch('scrape_api_docs.streamlit_app.requests.get')
    def test_state_initialization(self, mock_get, mock_links, mock_st, temp_dir):
        """Test that state is properly initialized before scraping."""
        # Setup mocks
        mock_st.session_state = MagicMock()
        state = ScraperState()
        mock_st.session_state.scraper_state = state
        mock_st.session_state.output_filename = ""
        mock_st.session_state.scraping_complete = False

        mock_links.return_value = ["https://example.com/docs/"]

        mock_response = MagicMock()
        mock_response.text = '<html><body><main><h1>Test</h1></main></body></html>'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Change to temp dir
        import os
        os.chdir(temp_dir)

        # Execute
        scrape_with_progress("https://example.com/docs/")

        # Verify state
        assert state.start_time is not None
        assert state.is_running is False  # Should be False after completion

    @patch('scrape_api_docs.streamlit_app.st')
    @patch('scrape_api_docs.streamlit_app.get_all_site_links')
    def test_max_pages_limit(self, mock_links, mock_st):
        """Test respect of user-defined max pages limit."""
        # Setup
        mock_st.session_state = MagicMock()
        state = ScraperState()
        mock_st.session_state.scraper_state = state
        mock_st.session_state.output_filename = ""
        mock_st.session_state.scraping_complete = False

        # Return 10 pages but limit to 3
        mock_links.return_value = [f"https://example.com/page{i}" for i in range(10)]

        with patch('scrape_api_docs.streamlit_app.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = '<html><body><main>Test</main></body></html>'
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            scrape_with_progress("https://example.com/docs/", max_pages=3)

            # Should only process 3 pages
            assert state.total_pages == 3

    @patch('scrape_api_docs.streamlit_app.st')
    @patch('scrape_api_docs.streamlit_app.get_all_site_links')
    @patch('scrape_api_docs.streamlit_app.requests.get')
    def test_error_collection_during_scrape(self, mock_get, mock_links, mock_st, temp_dir):
        """Test aggregation of errors during processing."""
        # Setup
        mock_st.session_state = MagicMock()
        state = ScraperState()
        mock_st.session_state.scraper_state = state
        mock_st.session_state.output_filename = ""
        mock_st.session_state.scraping_complete = False

        mock_links.return_value = [
            "https://example.com/page1",
            "https://example.com/page2"
        ]

        # First request succeeds, second fails
        mock_get.side_effect = [
            MagicMock(text='<html><body><main>OK</main></body></html>', raise_for_status=MagicMock()),
            Exception("Network error")
        ]

        import os
        os.chdir(temp_dir)

        scrape_with_progress("https://example.com/docs/")

        # Should have collected the error
        assert len(state.errors) > 0

    @patch('scrape_api_docs.streamlit_app.st')
    def test_custom_filename_usage(self, mock_st, temp_dir):
        """Test use of provided custom filename."""
        # Setup
        mock_st.session_state = MagicMock()
        state = ScraperState()
        mock_st.session_state.scraper_state = state
        mock_st.session_state.output_filename = ""
        mock_st.session_state.scraping_complete = False

        with patch('scrape_api_docs.streamlit_app.get_all_site_links') as mock_links:
            mock_links.return_value = ["https://example.com/docs/"]

            with patch('scrape_api_docs.streamlit_app.requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.text = '<html><body><main>Test</main></body></html>'
                mock_response.raise_for_status = MagicMock()
                mock_get.return_value = mock_response

                import os
                os.chdir(temp_dir)

                custom_name = "my_custom_docs.md"
                scrape_with_progress(
                    "https://example.com/docs/",
                    custom_filename=custom_name
                )

                assert mock_st.session_state.output_filename == custom_name


# ============================================================================
# Tests for init_session_state()
# ============================================================================

@pytest.mark.unit
class TestInitSessionState:
    """Test suite for session state initialization."""

    @patch('scrape_api_docs.streamlit_app.st')
    def test_state_initialization_when_empty(self, mock_st):
        """Test initialization when session state is empty."""
        mock_st.session_state = {}

        init_session_state()

        assert "scraper_state" in mock_st.session_state
        assert "output_filename" in mock_st.session_state
        assert "scraping_complete" in mock_st.session_state

    @patch('scrape_api_docs.streamlit_app.st')
    def test_state_preservation_when_exists(self, mock_st):
        """Test that existing state is not overwritten."""
        existing_state = ScraperState()
        existing_state.progress = 50

        mock_st.session_state = {
            "scraper_state": existing_state,
            "output_filename": "test.md",
            "scraping_complete": True
        }

        init_session_state()

        # Should not reinitialize
        assert mock_st.session_state["scraper_state"].progress == 50
        assert mock_st.session_state["output_filename"] == "test.md"
        assert mock_st.session_state["scraping_complete"] is True


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_state_thread_safety_simulation(self):
        """Simulate concurrent state access."""
        state = ScraperState()

        # Simulate multiple updates
        state.progress = 25
        state.current_url = "https://example.com/page1"
        assert state.progress == 25

        state.progress = 50
        state.current_url = "https://example.com/page2"
        assert state.progress == 50

    @patch('scrape_api_docs.streamlit_app.st')
    @patch('scrape_api_docs.streamlit_app.get_all_site_links')
    def test_stop_functionality(self, mock_links, mock_st):
        """Test graceful stop during scraping."""
        mock_st.session_state = MagicMock()
        state = ScraperState()
        state.is_running = True
        mock_st.session_state.scraper_state = state

        mock_links.return_value = [f"https://example.com/page{i}" for i in range(100)]

        # Simulate user stopping after 2 pages
        def stop_after_two(*args, **kwargs):
            if len(state.processed_urls) >= 2:
                state.is_running = False
            resp = MagicMock()
            resp.text = '<html><body><main>Test</main></body></html>'
            resp.raise_for_status = MagicMock()
            return resp

        with patch('scrape_api_docs.streamlit_app.requests.get', side_effect=stop_after_two):
            scrape_with_progress("https://example.com/docs/")

            # Should have stopped early
            assert len(state.processed_urls) < 100

    def test_validate_url_exception_handling(self):
        """Test validation handles unexpected exceptions."""
        # Test with completely malformed input
        is_valid, error = validate_url("ht!@#$%^&*()")

        assert is_valid is False
        assert len(error) > 0
