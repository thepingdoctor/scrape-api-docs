"""Unit tests for robots.txt compliance module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from urllib.robotparser import RobotFileParser

from scrape_api_docs.robots import RobotsChecker


class TestRobotsChecker:
    """Test suite for RobotsChecker class."""

    def test_initialization(self):
        """Test checker initialization with custom user-agent."""
        checker = RobotsChecker(user_agent="custom-bot/1.0")
        assert checker.user_agent == "custom-bot/1.0"
        assert isinstance(checker._cache, dict)
        assert len(checker._cache) == 0

    def test_default_user_agent(self):
        """Test default user-agent is set correctly."""
        checker = RobotsChecker()
        assert checker.user_agent == "scrape-api-docs/0.1.0"

    def test_get_robots_url(self):
        """Test robots.txt URL generation."""
        checker = RobotsChecker()
        url = "https://example.com/docs/api"
        robots_url = checker._get_robots_url(url)
        assert robots_url == "https://example.com/robots.txt"

    @patch('scrape_api_docs.robots.RobotFileParser')
    def test_is_allowed_success(self, mock_parser_class):
        """Test URL is allowed when robots.txt permits."""
        # Setup mock
        mock_parser = Mock(spec=RobotFileParser)
        mock_parser.can_fetch.return_value = True
        mock_parser_class.return_value = mock_parser

        checker = RobotsChecker()
        allowed, reason = checker.is_allowed("https://example.com/docs")

        assert allowed is True
        assert reason is None
        mock_parser.can_fetch.assert_called_with("scrape-api-docs/0.1.0", "https://example.com/docs")

    @patch('scrape_api_docs.robots.RobotFileParser')
    def test_is_allowed_blocked(self, mock_parser_class):
        """Test URL is blocked when robots.txt disallows."""
        # Setup mock
        mock_parser = Mock(spec=RobotFileParser)
        mock_parser.can_fetch.return_value = False
        mock_parser_class.return_value = mock_parser

        checker = RobotsChecker()
        allowed, reason = checker.is_allowed("https://example.com/admin")

        assert allowed is False
        assert "Blocked by robots.txt" in reason

    @patch('scrape_api_docs.robots.RobotFileParser')
    def test_robots_txt_unavailable(self, mock_parser_class):
        """Test permissive default when robots.txt unavailable."""
        # Setup mock to raise exception
        mock_parser = Mock(spec=RobotFileParser)
        mock_parser.read.side_effect = Exception("Connection failed")
        mock_parser_class.return_value = mock_parser

        checker = RobotsChecker()
        allowed, reason = checker.is_allowed("https://example.com/docs")

        # Should allow by default
        assert allowed is True
        assert reason is None

    @patch('scrape_api_docs.robots.RobotFileParser')
    def test_crawl_delay_specified(self, mock_parser_class):
        """Test crawl delay retrieval when specified."""
        # Setup mock
        mock_parser = Mock(spec=RobotFileParser)
        mock_parser.crawl_delay.return_value = 5.0
        mock_parser_class.return_value = mock_parser

        checker = RobotsChecker()
        delay = checker.get_crawl_delay("https://example.com/docs")

        assert delay == 5.0

    @patch('scrape_api_docs.robots.RobotFileParser')
    def test_crawl_delay_default(self, mock_parser_class):
        """Test default crawl delay when not specified."""
        # Setup mock
        mock_parser = Mock(spec=RobotFileParser)
        mock_parser.crawl_delay.return_value = None
        mock_parser_class.return_value = mock_parser

        checker = RobotsChecker()
        delay = checker.get_crawl_delay("https://example.com/docs")

        assert delay == 1.0  # Default

    def test_cache_functionality(self):
        """Test robots.txt caching works correctly."""
        with patch('scrape_api_docs.robots.RobotFileParser') as mock_parser_class:
            mock_parser = Mock(spec=RobotFileParser)
            mock_parser.can_fetch.return_value = True
            mock_parser_class.return_value = mock_parser

            checker = RobotsChecker()

            # First call - should fetch
            checker.is_allowed("https://example.com/docs")
            assert mock_parser.read.call_count == 1

            # Second call - should use cache
            checker.is_allowed("https://example.com/page2")
            # read() should still only be called once
            assert mock_parser.read.call_count == 1

    def test_clear_cache(self):
        """Test cache clearing."""
        checker = RobotsChecker()
        checker._cache['https://example.com/robots.txt'] = Mock()

        assert len(checker._cache) == 1

        checker.clear_cache()
        assert len(checker._cache) == 0

    def test_get_cached_domains(self):
        """Test retrieving cached domains."""
        checker = RobotsChecker()
        checker._cache['https://example.com/robots.txt'] = Mock()
        checker._cache['https://test.com/robots.txt'] = Mock()

        domains = checker.get_cached_domains()
        assert len(domains) == 2
        assert 'https://example.com/robots.txt' in domains
        assert 'https://test.com/robots.txt' in domains
