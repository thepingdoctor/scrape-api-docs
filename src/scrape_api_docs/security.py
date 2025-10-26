"""
Security Validation Module
==========================

This module provides security validation to prevent common web scraping
vulnerabilities including SSRF, path traversal, and injection attacks.

Features:
- SSRF protection (blocks private IPs, localhost, cloud metadata endpoints)
- URL validation and sanitization
- Path traversal prevention
- File name sanitization
- Scheme validation (http/https only)

Usage:
    from scrape_api_docs.security import SecurityValidator

    valid, reason = SecurityValidator.validate_url("https://example.com")
    if not valid:
        print(f"Security check failed: {reason}")

    safe_filename = SecurityValidator.sanitize_filename("../../etc/passwd")
"""

from urllib.parse import urlparse
import ipaddress
import socket
import re
import os
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class SecurityValidator:
    """
    Security validation for web scraping operations.

    Provides static methods for URL validation, SSRF prevention,
    and file name sanitization.
    """

    # RFC 1918 private networks and other blocked ranges
    BLOCKED_IP_RANGES = [
        ipaddress.IPv4Network('127.0.0.0/8'),      # Loopback
        ipaddress.IPv4Network('10.0.0.0/8'),       # Private Class A
        ipaddress.IPv4Network('172.16.0.0/12'),    # Private Class B
        ipaddress.IPv4Network('192.168.0.0/16'),   # Private Class C
        ipaddress.IPv4Network('169.254.0.0/16'),   # Link-local
        ipaddress.IPv4Network('0.0.0.0/8'),        # Current network
        ipaddress.IPv4Network('224.0.0.0/4'),      # Multicast
        ipaddress.IPv4Network('240.0.0.0/4'),      # Reserved
        ipaddress.IPv4Network('100.64.0.0/10'),    # Shared address space
    ]

    # IPv6 blocked ranges
    BLOCKED_IP6_RANGES = [
        ipaddress.IPv6Network('::1/128'),           # Loopback
        ipaddress.IPv6Network('fe80::/10'),         # Link-local
        ipaddress.IPv6Network('fc00::/7'),          # Unique local
        ipaddress.IPv6Network('ff00::/8'),          # Multicast
    ]

    # Cloud metadata endpoints (AWS, GCP, Azure, etc.)
    BLOCKED_HOSTNAMES = [
        '169.254.169.254',      # AWS, Azure, GCP metadata
        'metadata.google.internal',
        'metadata',
    ]

    ALLOWED_SCHEMES = ['http', 'https']

    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, str]:
        """
        Validate URL for security issues.

        Checks for:
        - Valid scheme (http/https only)
        - Private/localhost IP addresses (SSRF prevention)
        - Cloud metadata endpoints
        - Suspicious URL patterns

        Args:
            url: URL to validate

        Returns:
            Tuple of (valid: bool, reason: str)
            - valid: True if URL passes security checks
            - reason: "OK" if valid, error message otherwise
        """
        try:
            # Parse URL
            parsed = urlparse(url)

            # Validate scheme
            if parsed.scheme not in cls.ALLOWED_SCHEMES:
                return False, f"Invalid scheme '{parsed.scheme}'. Only http/https allowed."

            # Check for hostname
            hostname = parsed.hostname
            if not hostname:
                return False, "Missing hostname in URL"

            # Check for suspicious patterns
            if '@' in hostname:
                return False, "URL contains '@' (possible authentication bypass attack)"

            # Check against blocked hostnames
            if hostname.lower() in cls.BLOCKED_HOSTNAMES:
                return False, f"Blocked hostname: {hostname} (cloud metadata endpoint)"

            # Try to resolve IP address
            try:
                # Get all IP addresses for hostname
                ip_addresses = socket.getaddrinfo(
                    hostname,
                    None,
                    family=socket.AF_UNSPEC
                )

                # Check each resolved IP
                for ip_info in ip_addresses:
                    ip_str = ip_info[4][0]

                    # Try IPv4
                    try:
                        ip_obj = ipaddress.IPv4Address(ip_str)

                        # Check against blocked IPv4 ranges
                        for blocked_range in cls.BLOCKED_IP_RANGES:
                            if ip_obj in blocked_range:
                                return False, (
                                    f"SSRF attempt detected: {hostname} resolves to "
                                    f"{ip_str} in blocked range {blocked_range}"
                                )
                    except ipaddress.AddressValueError:
                        # Try IPv6
                        try:
                            ip6_obj = ipaddress.IPv6Address(ip_str)

                            # Check against blocked IPv6 ranges
                            for blocked_range in cls.BLOCKED_IP6_RANGES:
                                if ip6_obj in blocked_range:
                                    return False, (
                                        f"SSRF attempt detected: {hostname} resolves to "
                                        f"{ip_str} in blocked range {blocked_range}"
                                    )
                        except ipaddress.AddressValueError:
                            # Not a valid IP address
                            pass

                logger.debug(f"URL passed security validation: {url}")
                return True, "OK"

            except socket.gaierror as e:
                # DNS resolution failed
                # Could be temporary issue or invalid domain
                logger.warning(f"DNS resolution failed for {hostname}: {e}")
                return False, f"Cannot resolve hostname: {hostname}"

        except Exception as e:
            logger.error(f"Error validating URL {url}: {e}")
            return False, f"Validation error: {str(e)}"

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and other attacks.

        Removes:
        - Path separators (/, \)
        - Parent directory references (..)
        - Special/dangerous characters
        - Limits length to 200 characters

        Args:
            filename: Original filename

        Returns:
            Sanitized filename safe for file system use
        """
        if not filename:
            return "output"

        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')

        # Remove parent directory references
        filename = filename.replace('..', '')

        # Remove null bytes
        filename = filename.replace('\x00', '')

        # Remove or replace special characters
        # Allow only alphanumeric, underscore, hyphen, and dot
        filename = re.sub(r'[^\w\-_.]', '_', filename)

        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')

        # Ensure it's just a filename, not a path
        filename = os.path.basename(filename)

        # Limit length (filesystem limits vary, 200 is safe)
        if len(filename) > 200:
            # Preserve extension if present
            name, ext = os.path.splitext(filename)
            max_name_len = 200 - len(ext)
            filename = name[:max_name_len] + ext

        # Ensure we have a valid filename
        if not filename or filename in ('.', '..'):
            filename = "output"

        logger.debug(f"Sanitized filename: {filename}")
        return filename

    @classmethod
    def validate_content_length(cls, content_length: int, max_size: int = 100 * 1024 * 1024) -> Tuple[bool, str]:
        """
        Validate content length to prevent DoS attacks.

        Args:
            content_length: Content length in bytes
            max_size: Maximum allowed size in bytes (default: 100MB)

        Returns:
            Tuple of (valid: bool, reason: str)
        """
        if content_length > max_size:
            return False, (
                f"Content too large: {content_length} bytes "
                f"(max: {max_size} bytes)"
            )
        return True, "OK"

    @classmethod
    def is_safe_redirect(cls, original_url: str, redirect_url: str) -> Tuple[bool, str]:
        """
        Check if a redirect is safe to follow.

        Prevents redirects to private IPs or suspicious locations.

        Args:
            original_url: Original URL requested
            redirect_url: URL being redirected to

        Returns:
            Tuple of (safe: bool, reason: str)
        """
        # Validate the redirect URL
        valid, reason = cls.validate_url(redirect_url)
        if not valid:
            return False, f"Unsafe redirect: {reason}"

        # Additional checks could be added here
        # e.g., ensure redirect stays on same domain

        return True, "OK"
