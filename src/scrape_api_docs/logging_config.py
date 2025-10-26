"""
Structured Logging Configuration
=================================

This module provides structured logging configuration with proper log levels,
formatting, and request tracing for the documentation scraper.

Features:
- Structured JSON logging for production
- Human-readable console logging for development
- Request ID tracking for correlation
- Performance metrics logging
- Configurable log levels
- File and console outputs

Usage:
    from scrape_api_docs.logging_config import setup_logging, get_logger

    setup_logging(level='INFO', log_file='scraper.log')
    logger = get_logger(__name__)
    logger.info("Starting scrape", extra={'url': 'https://example.com'})
"""

import logging
import logging.handlers
import sys
import json
from datetime import datetime
from typing import Optional
import uuid
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs as JSON objects with consistent structure including
    timestamp, level, logger name, message, and any extra fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add any extra fields from the log call
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        # Add request_id if present
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for console output.

    Provides colorized, easy-to-read log output for development.
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors and structure."""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')

        # Build message
        message = f"{color}[{timestamp}] {record.levelname:8s}{reset} "
        message += f"{record.name}: {record.getMessage()}"

        # Add request_id if present
        if hasattr(record, 'request_id'):
            message += f" (req_id={record.request_id})"

        # Add exception if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return message


class RequestIdFilter(logging.Filter):
    """
    Filter to add request_id to log records.

    Generates a unique request ID per context and attaches it to
    all log records for request tracing and correlation.
    """

    def __init__(self):
        super().__init__()
        self.request_id = None

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request_id to record if not present."""
        if not hasattr(record, 'request_id'):
            if self.request_id is None:
                self.request_id = str(uuid.uuid4())[:8]
            record.request_id = self.request_id
        return True


def setup_logging(
    level: str = 'INFO',
    log_file: Optional[str] = None,
    json_format: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Configure application-wide logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None for console only)
        json_format: Use JSON formatting for logs
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup log files to keep

    Returns:
        Root logger instance
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    if json_format:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(HumanReadableFormatter())

    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)

    # Add request ID filter
    request_filter = RequestIdFilter()
    for handler in root_logger.handlers:
        handler.addFilter(request_filter)

    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

    root_logger.info(
        f"Logging configured: level={level}, "
        f"file={log_file or 'console'}, "
        f"format={'JSON' if json_format else 'human'}"
    )

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class PerformanceLogger:
    """
    Context manager for logging performance metrics.

    Usage:
        with PerformanceLogger(logger, "scrape_operation", url=url):
            # Perform operation
            pass
    """

    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        """
        Initialize performance logger.

        Args:
            logger: Logger instance
            operation: Name of operation being measured
            **kwargs: Additional context fields
        """
        self.logger = logger
        self.operation = operation
        self.context = kwargs
        self.start_time = None

    def __enter__(self):
        """Start performance measurement."""
        self.start_time = datetime.utcnow()
        self.logger.debug(
            f"Starting {self.operation}",
            extra={'extra_fields': self.context}
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log performance metrics."""
        duration = (datetime.utcnow() - self.start_time).total_seconds()

        metrics = {
            'operation': self.operation,
            'duration_seconds': duration,
            'success': exc_type is None,
            **self.context
        }

        if exc_type is None:
            self.logger.info(
                f"Completed {self.operation} in {duration:.2f}s",
                extra={'extra_fields': metrics}
            )
        else:
            metrics['error'] = str(exc_val)
            self.logger.error(
                f"Failed {self.operation} after {duration:.2f}s",
                extra={'extra_fields': metrics}
            )
