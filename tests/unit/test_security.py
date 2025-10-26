"""Unit tests for security validation module."""

import pytest
from unittest.mock import patch
import socket

from scrape_api_docs.security import SecurityValidator


class TestSecurityValidator:
    """Test suite for SecurityValidator class."""

    def test_validate_url_valid_https(self):
        """Test validation passes for valid HTTPS URL."""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            # Mock DNS resolution to a public IP
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 80))
            ]

            valid, reason = SecurityValidator.validate_url("https://example.com/docs")
            assert valid is True
            assert reason == "OK"

    def test_validate_url_invalid_scheme(self):
        """Test validation fails for invalid scheme."""
        valid, reason = SecurityValidator.validate_url("ftp://example.com")
        assert valid is False
        assert "Invalid scheme" in reason

    def test_validate_url_missing_hostname(self):
        """Test validation fails for missing hostname."""
        valid, reason = SecurityValidator.validate_url("https://")
        assert valid is False
        assert "Missing hostname" in reason

    def test_validate_url_localhost(self):
        """Test validation blocks localhost."""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 80))
            ]

            valid, reason = SecurityValidator.validate_url("https://localhost/api")
            assert valid is False
            assert "SSRF" in reason
            assert "127.0.0.0/8" in reason

    def test_validate_url_private_ip_10(self):
        """Test validation blocks private IP (10.x.x.x)."""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.1', 80))
            ]

            valid, reason = SecurityValidator.validate_url("https://internal.example.com")
            assert valid is False
            assert "SSRF" in reason
            assert "10.0.0.0/8" in reason

    def test_validate_url_private_ip_192(self):
        """Test validation blocks private IP (192.168.x.x)."""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.1', 80))
            ]

            valid, reason = SecurityValidator.validate_url("https://router.local")
            assert valid is False
            assert "SSRF" in reason
            assert "192.168.0.0/16" in reason

    def test_validate_url_metadata_endpoint(self):
        """Test validation blocks cloud metadata endpoint."""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('169.254.169.254', 80))
            ]

            valid, reason = SecurityValidator.validate_url("http://169.254.169.254/metadata")
            assert valid is False
            assert "SSRF" in reason

    def test_validate_url_auth_bypass(self):
        """Test validation blocks URLs with @ (auth bypass)."""
        valid, reason = SecurityValidator.validate_url("https://user@example.com/docs")
        assert valid is False
        assert "@" in reason

    def test_validate_url_dns_failure(self):
        """Test validation handles DNS resolution failure."""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.side_effect = socket.gaierror("DNS lookup failed")

            valid, reason = SecurityValidator.validate_url("https://invalid-domain.example")
            assert valid is False
            assert "Cannot resolve hostname" in reason

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        result = SecurityValidator.sanitize_filename("my-file.txt")
        assert result == "my-file.txt"

    def test_sanitize_filename_path_traversal(self):
        """Test sanitization removes path traversal."""
        result = SecurityValidator.sanitize_filename("../../etc/passwd")
        assert result == "etc_passwd"
        assert ".." not in result
        assert "/" not in result

    def test_sanitize_filename_special_chars(self):
        """Test sanitization removes special characters."""
        result = SecurityValidator.sanitize_filename("file<>:\"\\|?*.txt")
        assert result == "file_________.txt"

    def test_sanitize_filename_null_bytes(self):
        """Test sanitization removes null bytes."""
        result = SecurityValidator.sanitize_filename("file\x00name.txt")
        assert "\x00" not in result

    def test_sanitize_filename_length_limit(self):
        """Test sanitization limits filename length."""
        long_name = "a" * 300 + ".txt"
        result = SecurityValidator.sanitize_filename(long_name)
        assert len(result) <= 200

    def test_sanitize_filename_preserve_extension(self):
        """Test sanitization preserves extension when truncating."""
        long_name = "a" * 300 + ".md"
        result = SecurityValidator.sanitize_filename(long_name)
        assert result.endswith(".md")
        assert len(result) <= 200

    def test_sanitize_filename_empty_input(self):
        """Test sanitization handles empty input."""
        result = SecurityValidator.sanitize_filename("")
        assert result == "output"

    def test_sanitize_filename_only_dots(self):
        """Test sanitization handles only dots."""
        result = SecurityValidator.sanitize_filename("...")
        assert result == "output"

    def test_validate_content_length_ok(self):
        """Test content length validation passes for normal size."""
        valid, reason = SecurityValidator.validate_content_length(1000, max_size=10000)
        assert valid is True
        assert reason == "OK"

    def test_validate_content_length_too_large(self):
        """Test content length validation fails for large content."""
        valid, reason = SecurityValidator.validate_content_length(
            150 * 1024 * 1024,  # 150MB
            max_size=100 * 1024 * 1024  # 100MB max
        )
        assert valid is False
        assert "too large" in reason.lower()

    def test_is_safe_redirect_valid(self):
        """Test safe redirect validation."""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 80))
            ]

            original = "https://example.com/old"
            redirect = "https://example.com/new"

            safe, reason = SecurityValidator.is_safe_redirect(original, redirect)
            assert safe is True
            assert reason == "OK"

    def test_is_safe_redirect_to_localhost(self):
        """Test unsafe redirect to localhost."""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 80))
            ]

            original = "https://example.com/page"
            redirect = "http://localhost/admin"

            safe, reason = SecurityValidator.is_safe_redirect(original, redirect)
            assert safe is False
            assert "Unsafe redirect" in reason
