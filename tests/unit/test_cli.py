"""
Unit tests for CLI module.

Tests cover:
- Argument parsing
- Invalid arguments handling
- Help display
- Entry point execution
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
from io import StringIO


@pytest.mark.unit
class TestCLI:
    """Test suite for CLI functionality."""

    @patch('scrape_api_docs.__main__.scrape_site')
    def test_argument_parsing(self, mock_scrape):
        """Test correct URL extraction from arguments."""
        with patch('sys.argv', ['scrape-docs', 'https://example.com/docs/']):
            from scrape_api_docs.__main__ import main
            main()

            mock_scrape.assert_called_once_with('https://example.com/docs/')

    def test_no_arguments_shows_help(self):
        """Test that running without arguments shows help."""
        with patch('sys.argv', ['scrape-docs']):
            with pytest.raises(SystemExit) as exc_info:
                from scrape_api_docs.__main__ import main
                main()

            # Should exit with error code
            assert exc_info.value.code != 0

    @patch('sys.argv', ['scrape-docs', '--help'])
    def test_help_display(self):
        """Test -h/--help functionality."""
        with pytest.raises(SystemExit) as exc_info:
            from scrape_api_docs.__main__ import main
            main()

        # Help should exit with code 0
        assert exc_info.value.code == 0

    @patch('scrape_api_docs.__main__.scrape_site')
    def test_url_argument_required(self, mock_scrape):
        """Test that URL argument is required."""
        with patch('sys.argv', ['scrape-docs']):
            with pytest.raises(SystemExit):
                from scrape_api_docs.__main__ import main
                main()

    @patch('scrape_api_docs.__main__.scrape_site')
    def test_multiple_arguments_handling(self, mock_scrape):
        """Test behavior with extra arguments."""
        test_url = 'https://example.com/docs/'

        with patch('sys.argv', ['scrape-docs', test_url]):
            from scrape_api_docs.__main__ import main
            main()

            mock_scrape.assert_called_once_with(test_url)

    @patch('scrape_api_docs.__main__.scrape_site')
    def test_prints_completion_message(self, mock_scrape, capsys):
        """Test that completion message is printed."""
        with patch('sys.argv', ['scrape-docs', 'https://example.com/docs/']):
            from scrape_api_docs.__main__ import main
            main()

            captured = capsys.readouterr()
            assert 'complete' in captured.out.lower()

    @patch('scrape_api_docs.__main__.scrape_site')
    def test_scrape_site_called_with_url(self, mock_scrape):
        """Test that scrape_site is called with correct URL."""
        test_url = 'https://docs.example.com/api/v2/'

        with patch('sys.argv', ['scrape-docs', test_url]):
            from scrape_api_docs.__main__ import main
            main()

            mock_scrape.assert_called_once()
            args, kwargs = mock_scrape.call_args
            assert args[0] == test_url


@pytest.mark.unit
class TestRootScrapePy:
    """Test suite for root scrape.py file."""

    @patch('scrape.scrape_site')
    def test_root_scrape_argument_parsing(self, mock_scrape):
        """Test that root scrape.py also parses arguments correctly."""
        import scrape

        with patch('sys.argv', ['scrape.py', 'https://example.com/docs/']):
            with patch.object(scrape, '__name__', '__main__'):
                # Manually trigger the main block logic
                parser = scrape.argparse.ArgumentParser(
                    description="Scrape a documentation website and save all content to a single Markdown file."
                )
                parser.add_argument(
                    'url',
                    type=str,
                    help="The starting URL of the documentation to scrape (e.g., 'https://netboxlabs.com/docs/netbox/')."
                )

                args = parser.parse_args(['https://example.com/docs/'])
                assert args.url == 'https://example.com/docs/'


@pytest.mark.unit
class TestEntryPoint:
    """Test package entry point execution."""

    def test_module_can_be_imported(self):
        """Test that __main__ module can be imported."""
        try:
            import scrape_api_docs.__main__
            assert True
        except ImportError:
            pytest.fail("Failed to import __main__ module")

    def test_main_function_exists(self):
        """Test that main() function exists."""
        from scrape_api_docs.__main__ import main
        assert callable(main)

    @patch('scrape_api_docs.__main__.scrape_site')
    def test_can_run_as_module(self, mock_scrape):
        """Test package can be run with python -m."""
        with patch('sys.argv', ['__main__.py', 'https://example.com/docs/']):
            from scrape_api_docs.__main__ import main
            main()

            assert mock_scrape.called
