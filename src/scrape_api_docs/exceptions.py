"""
Custom Exception Classes
========================

This module defines custom exceptions for better error handling and
more informative error messages throughout the scraper application.

Exception Hierarchy:
    ScraperException (base)
    ├── RobotsException
    ├── SecurityException
    │   ├── SSRFException
    │   └── ValidationException
    ├── RateLimitException
    ├── ContentException
    │   ├── ContentTooLargeException
    │   └── ContentParsingException
    └── ConfigurationException
"""


class ScraperException(Exception):
    """
    Base exception for all scraper-related errors.

    All custom exceptions inherit from this class to allow
    catching all scraper errors with a single except clause.
    """

    def __init__(self, message: str, details: dict = None):
        """
        Initialize exception with message and optional details.

        Args:
            message: Human-readable error message
            details: Additional context about the error
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        """String representation with details."""
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message


class RobotsException(ScraperException):
    """
    Raised when robots.txt prevents scraping.

    Indicates that scraping is blocked by the website's robots.txt file.
    """
    pass


class SecurityException(ScraperException):
    """
    Base exception for security-related errors.

    Parent class for all security validation failures.
    """
    pass


class SSRFException(SecurityException):
    """
    Raised when SSRF attack is detected.

    Indicates an attempt to access private IP ranges, localhost,
    or cloud metadata endpoints.
    """
    pass


class ValidationException(SecurityException):
    """
    Raised when input validation fails.

    Indicates invalid URL, filename, or other input that fails
    security validation.
    """
    pass


class RateLimitException(ScraperException):
    """
    Raised when rate limiting is exceeded.

    Indicates that the request was throttled due to rate limiting,
    either by the scraper's own limits or by the target server (429).
    """

    def __init__(self, message: str, retry_after: float = None, details: dict = None):
        """
        Initialize rate limit exception.

        Args:
            message: Error message
            retry_after: Suggested retry delay in seconds
            details: Additional context
        """
        super().__init__(message, details)
        self.retry_after = retry_after


class ContentException(ScraperException):
    """
    Base exception for content-related errors.

    Parent class for all content processing errors.
    """
    pass


class ContentTooLargeException(ContentException):
    """
    Raised when content exceeds size limits.

    Indicates that the downloaded content is too large and may
    indicate a DoS attempt or misconfiguration.
    """

    def __init__(self, message: str, size: int, max_size: int, details: dict = None):
        """
        Initialize content size exception.

        Args:
            message: Error message
            size: Actual content size in bytes
            max_size: Maximum allowed size in bytes
            details: Additional context
        """
        details = details or {}
        details.update({'size': size, 'max_size': max_size})
        super().__init__(message, details)
        self.size = size
        self.max_size = max_size


class ContentParsingException(ContentException):
    """
    Raised when content parsing fails.

    Indicates that HTML/Markdown conversion or content extraction
    encountered an error.
    """
    pass


class ConfigurationException(ScraperException):
    """
    Raised when configuration is invalid.

    Indicates problems with configuration files, environment variables,
    or application settings.
    """
    pass


class NetworkException(ScraperException):
    """
    Raised when network operations fail.

    Wraps network-related errors (connection, timeout, DNS, etc.)
    with additional context.
    """

    def __init__(self, message: str, url: str = None, details: dict = None):
        """
        Initialize network exception.

        Args:
            message: Error message
            url: URL that failed
            details: Additional context
        """
        details = details or {}
        if url:
            details['url'] = url
        super().__init__(message, details)
        self.url = url


class RetryableException(ScraperException):
    """
    Base exception for transient errors that can be retried.

    Indicates that the operation failed but may succeed if retried.
    """

    def __init__(self, message: str, retry_count: int = 0, max_retries: int = 3, details: dict = None):
        """
        Initialize retryable exception.

        Args:
            message: Error message
            retry_count: Current retry attempt
            max_retries: Maximum retry attempts
            details: Additional context
        """
        details = details or {}
        details.update({'retry_count': retry_count, 'max_retries': max_retries})
        super().__init__(message, details)
        self.retry_count = retry_count
        self.max_retries = max_retries

    def should_retry(self) -> bool:
        """Check if operation should be retried."""
        return self.retry_count < self.max_retries
