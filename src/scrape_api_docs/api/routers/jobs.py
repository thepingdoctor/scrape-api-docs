"""
Job Management Endpoints
========================

Endpoints for managing scraping jobs and retrieving results.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request, Query
from typing import Optional
import logging
import json

from ..models.responses import JobStatus, JobListResponse, JobStatusEnum
from ..services.job_service import JobService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    req: Request,
    status: Optional[JobStatusEnum] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    sort: str = Query("created_at", description="Sort field"),
    order: str = Query("desc", description="Sort order (asc/desc)")
):
    """
    List all scraping jobs with filtering and pagination.

    Supports filtering by:
    - **status**: queued, running, completed, failed, cancelled
    - **limit**: Results per page (max 100)
    - **offset**: Pagination offset
    - **sort**: Sort field (created_at, updated_at, duration)
    - **order**: Sort order (asc, desc)
    """
    try:
        job_service: JobService = req.app.state.job_service

        jobs, total = await job_service.list_jobs(
            status=status.value if status else None,
            limit=limit,
            offset=offset,
            sort=sort,
            order=order
        )

        return JobListResponse(
            jobs=jobs,
            pagination={
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            }
        )

    except Exception as e:
        logger.error(f"Failed to list jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve jobs")


@router.get("/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str, req: Request):
    """
    Get detailed job status and results.

    Returns comprehensive information including:
    - Current execution status
    - Progress information (if running)
    - Statistics (pages processed, cache hits, etc.)
    - Available exports
    - Execution logs
    - Error details (if failed)
    """
    try:
        job_service: JobService = req.app.state.job_service

        job = await job_service.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )

        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve job status")


@router.delete("/{job_id}")
async def cancel_or_delete_job(job_id: str, req: Request):
    """
    Cancel a running job or delete completed job data.

    - Running jobs will be cancelled immediately
    - Completed/failed jobs will have their data deleted
    - Queued jobs will be removed from the queue
    """
    try:
        job_service: JobService = req.app.state.job_service

        result = await job_service.cancel_job(job_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )

        logger.info(f"Cancelled/deleted job {job_id}")

        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": "Job cancelled or deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to cancel job")


@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    req: Request,
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None, description="Filter by log level")
):
    """
    Get execution logs for a job.

    - **limit**: Maximum number of log entries (max 1000)
    - **level**: Filter by log level (info, warning, error)
    """
    try:
        job_service: JobService = req.app.state.job_service

        logs = await job_service.get_job_logs(job_id, limit=limit, level=level)

        return {
            "job_id": job_id,
            "logs": logs,
            "count": len(logs)
        }

    except Exception as e:
        logger.error(f"Failed to get logs for job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")


@router.websocket("/{job_id}/stream")
async def job_progress_stream(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress updates.

    Sends JSON messages with:
    - Progress updates (pages processed, percentage)
    - Log messages
    - Status changes
    - Completion notification

    Message types:
    - `progress`: Progress update
    - `log`: Log message
    - `status`: Status change
    - `complete`: Job completion
    - `error`: Error occurred
    """
    await websocket.accept()

    try:
        # Get job service from app
        job_service: JobService = websocket.app.state.job_service

        # Verify job exists
        job = await job_service.get_job(job_id)
        if not job:
            await websocket.send_json({
                "type": "error",
                "data": {
                    "code": "JOB_NOT_FOUND",
                    "message": f"Job {job_id} not found"
                }
            })
            await websocket.close()
            return

        logger.info(f"WebSocket connected for job {job_id}")

        # Send initial status
        await websocket.send_json({
            "type": "status",
            "data": {
                "job_id": job_id,
                "status": job.status.value,
                "progress": job.progress.dict() if job.progress else None
            }
        })

        # Stream updates until job completes
        async for update in job_service.stream_job_updates(job_id):
            try:
                await websocket.send_json(update)

                # Close connection on completion or failure
                if update.get("type") in ["complete", "error", "cancelled"]:
                    break

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for job {job_id}")
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "data": {
                    "code": "STREAM_ERROR",
                    "message": str(e)
                }
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


@router.post("/{job_id}/retry")
async def retry_failed_job(job_id: str, req: Request):
    """
    Retry a failed job.

    Creates a new job with the same configuration as the failed job.
    """
    try:
        job_service: JobService = req.app.state.job_service

        new_job = await job_service.retry_job(job_id)

        if not new_job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found or cannot be retried"
            )

        logger.info(f"Created retry job {new_job.job_id} for failed job {job_id}")

        return {
            "original_job_id": job_id,
            "new_job_id": new_job.job_id,
            "status_url": f"/api/v1/jobs/{new_job.job_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retry job")
