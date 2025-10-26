"""
API Integration Tests
=====================

Tests for FastAPI endpoints.
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from src.scrape_api_docs.api.main import app


# Synchronous tests using TestClient
client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns service info."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert data["service"] == "Documentation Scraper API"
    assert data["version"] == "2.0.0"
    assert "docs" in data
    assert "health" in data


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"


def test_system_health():
    """Test detailed system health endpoint."""
    response = client.get("/api/v1/system/health")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "version" in data
    assert "uptime" in data
    assert "dependencies" in data


def test_system_version():
    """Test version endpoint."""
    response = client.get("/api/v1/system/version")

    assert response.status_code == 200
    data = response.json()

    assert data["version"] == "2.0.0"
    assert data["api_version"] == "v1"


def test_system_ping():
    """Test ping endpoint."""
    response = client.get("/api/v1/system/ping")

    assert response.status_code == 200
    data = response.json()

    assert data["ping"] == "pong"
    assert "timestamp" in data


def test_create_scrape_job_invalid_url():
    """Test creating job with invalid URL."""
    response = client.post(
        "/api/v1/scrape",
        json={
            "url": "not-a-valid-url",
            "export_formats": ["markdown"]
        }
    )

    # Should fail validation
    assert response.status_code == 422


def test_create_scrape_job_invalid_format():
    """Test creating job with invalid export format."""
    response = client.post(
        "/api/v1/scrape",
        json={
            "url": "https://example.com",
            "export_formats": ["invalid_format"]
        }
    )

    # Should fail validation
    assert response.status_code == 422


def test_get_nonexistent_job():
    """Test getting status of non-existent job."""
    response = client.get("/api/v1/jobs/nonexistent_job_id")

    assert response.status_code == 404


def test_list_jobs():
    """Test listing jobs."""
    response = client.get("/api/v1/jobs")

    assert response.status_code == 200
    data = response.json()

    assert "jobs" in data
    assert "pagination" in data
    assert isinstance(data["jobs"], list)


def test_list_jobs_with_filters():
    """Test listing jobs with filters."""
    response = client.get(
        "/api/v1/jobs",
        params={
            "status": "completed",
            "limit": 5,
            "offset": 0
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["jobs"]) <= 5


def test_validate_url():
    """Test URL validation endpoint."""
    response = client.post(
        "/api/v1/scrape/validate",
        json={
            "url": "https://example.com"
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert "valid" in data
    assert "warnings" in data
    assert "recommendations" in data


def test_estimate_job():
    """Test job estimation endpoint."""
    response = client.post(
        "/api/v1/scrape/estimate",
        json={
            "url": "https://example.com",
            "options": {
                "max_depth": 5
            }
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert "estimated_pages" in data
    assert "estimated_duration_seconds" in data


def test_rate_limiting():
    """Test rate limiting middleware."""
    # Make many rapid requests
    responses = []
    for _ in range(150):  # Exceed the rate limit
        response = client.get("/api/v1/system/ping")
        responses.append(response.status_code)

    # Should eventually get rate limited
    assert 429 in responses


def test_cors_headers():
    """Test CORS headers are present."""
    response = client.options("/api/v1/system/health")

    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers


def test_request_id_header():
    """Test request ID is added to responses."""
    response = client.get("/api/v1/system/ping")

    assert "x-request-id" in response.headers


def test_process_time_header():
    """Test process time is added to responses."""
    response = client.get("/api/v1/system/ping")

    assert "x-process-time" in response.headers


# Async tests using AsyncClient
@pytest.mark.asyncio
async def test_create_scrape_job_valid():
    """Test creating a valid scrape job."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/scrape",
            json={
                "url": "https://example.com",
                "options": {
                    "max_depth": 3,
                    "rate_limit": 1.0
                },
                "export_formats": ["markdown"]
            }
        )

        assert response.status_code == 202
        data = response.json()

        assert "job_id" in data
        assert data["status"] == "queued"
        assert "status_url" in data


@pytest.mark.asyncio
async def test_system_stats():
    """Test system statistics endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/system/stats")

        assert response.status_code == 200
        data = response.json()

        assert "jobs" in data
        assert "performance" in data
        assert "resources" in data


@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Test Prometheus metrics endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/system/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

        # Check for Prometheus metric format
        content = response.text
        assert "scraper_jobs_total" in content
        assert "HELP" in content
        assert "TYPE" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
