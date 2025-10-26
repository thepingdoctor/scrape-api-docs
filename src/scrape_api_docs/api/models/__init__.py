"""
Pydantic Models for API Requests and Responses
==============================================

Type-safe models for validation and documentation.
"""

from .requests import (
    ScrapeRequest,
    ScrapeOptions,
    AuthCredentials,
    AuthType,
    Priority
)
from .responses import (
    JobResponse,
    JobStatus,
    JobStatusEnum,
    JobProgress,
    JobStatistics,
    ErrorResponse,
    HealthResponse
)

__all__ = [
    # Requests
    "ScrapeRequest",
    "ScrapeOptions",
    "AuthCredentials",
    "AuthType",
    "Priority",
    # Responses
    "JobResponse",
    "JobStatus",
    "JobStatusEnum",
    "JobProgress",
    "JobStatistics",
    "ErrorResponse",
    "HealthResponse",
]
