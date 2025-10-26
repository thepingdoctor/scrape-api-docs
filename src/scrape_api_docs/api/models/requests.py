"""
Request Models for API Endpoints
================================

Pydantic models for validating incoming requests.
"""

from pydantic import BaseModel, HttpUrl, Field, validator
from typing import List, Optional, Dict
from enum import Enum


class AuthType(str, Enum):
    """Supported authentication types."""
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"
    COOKIE = "cookie"


class Priority(str, Enum):
    """Job priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ScrapeOptions(BaseModel):
    """Configuration options for scraping operations."""

    render_javascript: bool = Field(
        default=False,
        description="Enable JavaScript rendering using Playwright"
    )
    max_depth: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum crawl depth from base URL"
    )
    include_patterns: Optional[List[str]] = Field(
        default=None,
        description="URL patterns to include (glob format)"
    )
    exclude_patterns: Optional[List[str]] = Field(
        default=None,
        description="URL patterns to exclude (glob format)"
    )
    rate_limit: float = Field(
        default=2.0,
        ge=0.1,
        le=10.0,
        description="Maximum requests per second"
    )
    timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Request timeout in seconds"
    )
    cache_enabled: bool = Field(
        default=True,
        description="Enable response caching"
    )
    cache_ttl: int = Field(
        default=3600,
        ge=0,
        description="Cache TTL in seconds (0 = no expiration)"
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="Custom User-Agent header"
    )
    follow_redirects: bool = Field(
        default=True,
        description="Follow HTTP redirects"
    )
    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificates"
    )

    class Config:
        schema_extra = {
            "example": {
                "render_javascript": False,
                "max_depth": 10,
                "include_patterns": ["*/docs/*", "*/api/*"],
                "exclude_patterns": ["*/blog/*"],
                "rate_limit": 2.0,
                "timeout": 30,
                "cache_enabled": True,
                "cache_ttl": 3600
            }
        }


class AuthCredentials(BaseModel):
    """Authentication credentials for protected sites."""

    type: AuthType = Field(description="Authentication type")
    username: Optional[str] = Field(
        default=None,
        description="Username for Basic auth"
    )
    password: Optional[str] = Field(
        default=None,
        description="Password for Basic auth"
    )
    token: Optional[str] = Field(
        default=None,
        description="Bearer token or API key"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key value"
    )
    cookies: Optional[Dict[str, str]] = Field(
        default=None,
        description="Cookie key-value pairs"
    )

    @validator('username')
    def validate_basic_auth(cls, v, values):
        """Validate Basic auth requires username and password."""
        if values.get('type') == AuthType.BASIC and not v:
            raise ValueError("Username required for Basic authentication")
        return v

    @validator('token')
    def validate_bearer_auth(cls, v, values):
        """Validate Bearer auth requires token."""
        if values.get('type') == AuthType.BEARER and not v:
            raise ValueError("Token required for Bearer authentication")
        return v

    class Config:
        schema_extra = {
            "example": {
                "type": "bearer",
                "token": "your_bearer_token_here"
            }
        }


class ScrapeRequest(BaseModel):
    """Request to create a new scraping job."""

    url: HttpUrl = Field(
        description="Base URL of the documentation site to scrape"
    )
    options: ScrapeOptions = Field(
        default_factory=ScrapeOptions,
        description="Scraping configuration options"
    )
    export_formats: List[str] = Field(
        default=["markdown"],
        description="Export formats (markdown, pdf, json, epub)"
    )
    authentication: Optional[AuthCredentials] = Field(
        default=None,
        description="Authentication credentials"
    )
    webhook_url: Optional[HttpUrl] = Field(
        default=None,
        description="Webhook URL for completion notification"
    )
    priority: Priority = Field(
        default=Priority.NORMAL,
        description="Job priority level"
    )
    metadata: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom metadata for job tracking"
    )

    @validator('export_formats')
    def validate_export_formats(cls, v):
        """Validate export formats are supported."""
        supported = {'markdown', 'pdf', 'json', 'epub', 'html'}
        invalid = set(v) - supported
        if invalid:
            raise ValueError(
                f"Unsupported export formats: {invalid}. "
                f"Supported: {supported}"
            )
        return v

    class Config:
        schema_extra = {
            "example": {
                "url": "https://docs.example.com",
                "options": {
                    "render_javascript": False,
                    "max_depth": 10,
                    "rate_limit": 2.0,
                    "cache_enabled": True
                },
                "export_formats": ["markdown", "pdf"],
                "priority": "normal"
            }
        }


class ValidationRequest(BaseModel):
    """Request to validate URL and options without scraping."""

    url: HttpUrl = Field(description="URL to validate")
    options: Optional[ScrapeOptions] = Field(
        default=None,
        description="Options to validate"
    )
