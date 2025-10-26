"""
Scraping Endpoints
==================

Endpoints for creating and managing scraping operations.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
import logging
from datetime import datetime

from ..models.requests import ScrapeRequest, ValidationRequest
from ..models.responses import JobResponse, ValidationResponse, JobStatusEnum
from ..services.scraper_service import ScraperService
from ..services.job_service import JobService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=JobResponse, status_code=202)
async def create_scrape_job(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    req: Request
):
    """
    Create a new scraping job (async).

    The job is queued for background processing. Use the returned job_id
    to check status and retrieve results.

    - **url**: Base URL of documentation site
    - **options**: Scraping configuration (optional)
    - **export_formats**: Desired export formats (default: markdown)
    - **authentication**: Auth credentials for protected sites (optional)
    - **webhook_url**: Callback URL for completion notification (optional)
    - **priority**: Job priority (low, normal, high, urgent)
    """
    try:
        # Get job service from app state
        job_service: JobService = req.app.state.job_service

        # Create job
        job = await job_service.create_job(
            url=str(request.url),
            options=request.options.dict(),
            export_formats=request.export_formats,
            authentication=request.authentication.dict() if request.authentication else None,
            webhook_url=str(request.webhook_url) if request.webhook_url else None,
            priority=request.priority.value,
            metadata=request.metadata
        )

        # Queue background task
        background_tasks.add_task(
            job_service.execute_job,
            job.job_id
        )

        logger.info(f"Created scraping job {job.job_id} for {request.url}")

        # Build WebSocket URL
        websocket_url = None
        if req.base_url:
            ws_scheme = "wss" if req.url.scheme == "https" else "ws"
            websocket_url = f"{ws_scheme}://{req.base_url.netloc}/api/v1/jobs/{job.job_id}/stream"

        return JobResponse(
            job_id=job.job_id,
            status=job.status,
            created_at=job.created_at,
            estimated_duration=job.estimated_duration,
            status_url=f"/api/v1/jobs/{job.job_id}",
            websocket_url=websocket_url
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create scraping job")


@router.post("/sync", status_code=200)
async def create_sync_scrape_job(request: ScrapeRequest, req: Request):
    """
    Create a synchronous scraping job (blocks until complete).

    WARNING: Only use for small documentation sites. Larger sites should
    use the async endpoint to avoid timeouts.

    Returns the complete job results including all exports.
    """
    try:
        job_service: JobService = req.app.state.job_service

        # Create and execute job synchronously
        job = await job_service.create_job(
            url=str(request.url),
            options=request.options.dict(),
            export_formats=request.export_formats,
            authentication=request.authentication.dict() if request.authentication else None,
            priority=request.priority.value,
            metadata=request.metadata
        )

        # Execute synchronously
        result = await job_service.execute_job(job.job_id)

        logger.info(f"Completed sync job {job.job_id} for {request.url}")

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Scraping operation timed out. Use async endpoint for large sites."
        )
    except Exception as e:
        logger.error(f"Failed to execute sync job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to execute scraping job")


@router.post("/validate", response_model=ValidationResponse)
async def validate_scrape_request(request: ValidationRequest):
    """
    Validate URL and scraping options without executing.

    Performs the following checks:
    - URL accessibility
    - SSL certificate validity
    - Estimated page count
    - Authentication requirements
    - JavaScript rendering needs

    Returns recommendations for optimal scraping configuration.
    """
    try:
        scraper_service = ScraperService()

        # Validate URL
        validation_result = await scraper_service.validate_url(
            url=str(request.url),
            options=request.options.dict() if request.options else {}
        )

        return ValidationResponse(**validation_result)

    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Validation failed")


@router.post("/estimate", status_code=200)
async def estimate_scrape_job(request: ScrapeRequest):
    """
    Estimate scraping job parameters without execution.

    Returns:
    - Estimated page count
    - Estimated duration
    - Resource requirements
    - Cost estimation (if applicable)
    """
    try:
        scraper_service = ScraperService()

        estimate = await scraper_service.estimate_job(
            url=str(request.url),
            options=request.options.dict()
        )

        return {
            "url": str(request.url),
            "estimated_pages": estimate.get("page_count", 0),
            "estimated_duration_seconds": estimate.get("duration", 0),
            "estimated_size_mb": estimate.get("size_mb", 0),
            "recommendations": estimate.get("recommendations", {})
        }

    except Exception as e:
        logger.error(f"Estimation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to estimate job")
