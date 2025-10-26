"""
System Endpoints
================

Health checks, metrics, and system information endpoints.
"""

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
import time
import logging
from datetime import datetime

from ..models.responses import HealthResponse, SystemStats

router = APIRouter()
logger = logging.getLogger(__name__)

# Track startup time
_startup_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check(req: Request):
    """
    Health check endpoint.

    Returns overall system health and dependency status.

    Status values:
    - **healthy**: All systems operational
    - **degraded**: Some non-critical issues
    - **unhealthy**: Critical system failure
    """
    try:
        job_service = req.app.state.job_service

        # Check dependencies
        dependencies = {
            "database": "healthy",  # TODO: Actual database check
            "storage": "healthy",   # TODO: Actual storage check
            "cache": "healthy",     # TODO: Actual cache check
        }

        # Overall status
        status = "healthy"
        if any(s != "healthy" for s in dependencies.values()):
            status = "degraded" if all(s != "unhealthy" for s in dependencies.values()) else "unhealthy"

        uptime = time.time() - _startup_time

        return HealthResponse(
            status=status,
            version="2.0.0",
            uptime=uptime,
            dependencies=dependencies
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return HealthResponse(
            status="unhealthy",
            version="2.0.0",
            uptime=time.time() - _startup_time,
            dependencies={"error": str(e)}
        )


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(req: Request):
    """
    Get system statistics and metrics.

    Returns:
    - Job statistics by status
    - Performance metrics (avg duration, cache hit rate)
    - Resource usage (storage, memory)
    - Success/failure rates
    """
    try:
        job_service = req.app.state.job_service

        stats = await job_service.get_statistics()

        return SystemStats(
            jobs=stats.get("jobs", {}),
            performance=stats.get("performance", {}),
            resources=stats.get("resources", {})
        )

    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.get("/metrics", response_class=PlainTextResponse)
async def get_metrics(req: Request):
    """
    Get system metrics in Prometheus format.

    Exposes metrics for:
    - Job counts by status
    - Request rates
    - Cache performance
    - Processing durations
    - Error rates
    """
    try:
        job_service = req.app.state.job_service
        stats = await job_service.get_statistics()

        jobs = stats.get("jobs", {})
        perf = stats.get("performance", {})

        # Generate Prometheus metrics
        metrics = []

        # Job counts
        metrics.append("# HELP scraper_jobs_total Total number of scraping jobs")
        metrics.append("# TYPE scraper_jobs_total counter")
        for status, count in jobs.items():
            metrics.append(f'scraper_jobs_total{{status="{status}"}} {count}')

        # Pages scraped
        total_pages = perf.get("total_pages_scraped", 0)
        metrics.append("\n# HELP scraper_pages_scraped_total Total pages scraped")
        metrics.append("# TYPE scraper_pages_scraped_total counter")
        metrics.append(f"scraper_pages_scraped_total {total_pages}")

        # Cache hit rate
        cache_rate = perf.get("cache_hit_rate", 0.0)
        metrics.append("\n# HELP scraper_cache_hit_rate Cache hit rate")
        metrics.append("# TYPE scraper_cache_hit_rate gauge")
        metrics.append(f"scraper_cache_hit_rate {cache_rate:.3f}")

        # Average job duration
        avg_duration = perf.get("avg_job_duration", 0.0)
        metrics.append("\n# HELP scraper_avg_job_duration_seconds Average job duration")
        metrics.append("# TYPE scraper_avg_job_duration_seconds gauge")
        metrics.append(f"scraper_avg_job_duration_seconds {avg_duration:.2f}")

        return "\n".join(metrics)

    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}", exc_info=True)
        return "# Error generating metrics"


@router.get("/version")
async def get_version():
    """
    Get API version information.

    Returns version number and build metadata.
    """
    return {
        "version": "2.0.0",
        "api_version": "v1",
        "build_date": "2025-10-26",
        "commit": "unknown",  # TODO: Add from build process
        "python_version": "3.11+"
    }


@router.get("/ping")
async def ping():
    """
    Simple ping endpoint for connectivity testing.
    """
    return {"ping": "pong", "timestamp": datetime.utcnow().isoformat()}


# Import HTTPException
from fastapi import HTTPException
