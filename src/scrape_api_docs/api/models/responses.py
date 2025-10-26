"""
Response Models for API Endpoints
=================================

Pydantic models for API responses and data structures.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class JobStatusEnum(str, Enum):
    """Job execution status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobProgress(BaseModel):
    """Job progress information."""

    current_page: int = Field(description="Current page being processed")
    total_pages: int = Field(description="Total pages discovered")
    percent_complete: float = Field(
        ge=0.0,
        le=100.0,
        description="Completion percentage"
    )
    current_operation: str = Field(description="Current operation description")


class JobStatistics(BaseModel):
    """Job execution statistics."""

    pages_discovered: int = Field(default=0, description="Pages found during crawl")
    pages_processed: int = Field(default=0, description="Pages successfully processed")
    cache_hits: int = Field(default=0, description="Cache hit count")
    cache_misses: int = Field(default=0, description="Cache miss count")
    errors: int = Field(default=0, description="Error count")
    avg_page_time: float = Field(default=0.0, description="Average page processing time (seconds)")
    total_bytes: int = Field(default=0, description="Total bytes downloaded")


class ExportInfo(BaseModel):
    """Information about an exported file."""

    format: str = Field(description="Export format (markdown, pdf, etc.)")
    url: str = Field(description="Download URL")
    size_bytes: int = Field(description="File size in bytes")
    created_at: datetime = Field(description="Export creation timestamp")
    checksum: Optional[str] = Field(default=None, description="SHA256 checksum")


class JobLogEntry(BaseModel):
    """Log entry for job execution."""

    timestamp: datetime = Field(description="Log timestamp")
    level: str = Field(description="Log level (info, warning, error)")
    message: str = Field(description="Log message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional details")


class JobResponse(BaseModel):
    """Response for job creation."""

    job_id: str = Field(description="Unique job identifier")
    status: JobStatusEnum = Field(description="Current job status")
    created_at: datetime = Field(description="Job creation timestamp")
    estimated_duration: Optional[int] = Field(
        default=None,
        description="Estimated duration in seconds"
    )
    status_url: str = Field(description="URL to check job status")
    websocket_url: Optional[str] = Field(
        default=None,
        description="WebSocket URL for real-time updates"
    )


class JobStatus(BaseModel):
    """Detailed job status and results."""

    job_id: str = Field(description="Unique job identifier")
    url: str = Field(description="Source URL being scraped")
    status: JobStatusEnum = Field(description="Current job status")
    progress: Optional[JobProgress] = Field(
        default=None,
        description="Progress information (if running)"
    )
    created_at: datetime = Field(description="Job creation timestamp")
    started_at: Optional[datetime] = Field(
        default=None,
        description="Job start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Job completion timestamp"
    )
    estimated_completion: Optional[datetime] = Field(
        default=None,
        description="Estimated completion time"
    )
    duration: Optional[float] = Field(
        default=None,
        description="Job duration in seconds"
    )
    statistics: JobStatistics = Field(
        default_factory=JobStatistics,
        description="Execution statistics"
    )
    exports: List[ExportInfo] = Field(
        default_factory=list,
        description="Available exports"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
    logs: List[JobLogEntry] = Field(
        default_factory=list,
        description="Job execution logs"
    )


class JobListResponse(BaseModel):
    """Response for listing jobs."""

    jobs: List[JobStatus] = Field(description="List of jobs")
    pagination: Dict[str, Any] = Field(description="Pagination information")


class ValidationResponse(BaseModel):
    """Response for URL validation."""

    valid: bool = Field(description="Whether URL and options are valid")
    estimated_pages: Optional[int] = Field(
        default=None,
        description="Estimated page count"
    )
    estimated_duration: Optional[int] = Field(
        default=None,
        description="Estimated duration in seconds"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Validation warnings"
    )
    recommendations: Dict[str, Any] = Field(
        default_factory=dict,
        description="Recommended option changes"
    )


class ErrorResponse(BaseModel):
    """Error response format."""

    error: Dict[str, Any] = Field(
        description="Error details",
        example={
            "code": "INVALID_URL",
            "message": "The provided URL is not accessible",
            "details": {"url": "https://invalid.example.com"},
            "timestamp": "2025-10-26T19:00:00Z"
        }
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Overall health status")
    version: str = Field(description="API version")
    uptime: float = Field(description="Uptime in seconds")
    dependencies: Dict[str, str] = Field(
        description="Dependency health status"
    )


class SystemStats(BaseModel):
    """System statistics response."""

    jobs: Dict[str, int] = Field(description="Job statistics by status")
    performance: Dict[str, float] = Field(description="Performance metrics")
    resources: Dict[str, Any] = Field(description="Resource usage")
