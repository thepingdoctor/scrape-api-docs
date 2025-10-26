"""
Export Endpoints
================

Endpoints for downloading and managing exported documentation.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
import logging
from pathlib import Path

from ..services.export_service import ExportService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{job_id}/{filename}")
async def download_export(job_id: str, filename: str, req: Request):
    """
    Download exported documentation file.

    Supported formats:
    - **Markdown** (.md): Plain text Markdown format
    - **PDF** (.pdf): PDF document
    - **JSON** (.json): Structured JSON data
    - **EPUB** (.epub): EPUB ebook format
    - **HTML** (.html): Single-page HTML

    Returns the file with appropriate Content-Type and Content-Disposition headers.
    """
    try:
        export_service = ExportService()

        # Get export file path
        file_path = await export_service.get_export_file(job_id, filename)

        if not file_path or not Path(file_path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"Export file {filename} not found for job {job_id}"
            )

        # Determine media type
        media_types = {
            ".md": "text/markdown",
            ".pdf": "application/pdf",
            ".json": "application/json",
            ".epub": "application/epub+zip",
            ".html": "text/html"
        }

        suffix = Path(filename).suffix.lower()
        media_type = media_types.get(suffix, "application/octet-stream")

        logger.info(f"Serving export {filename} for job {job_id}")

        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to serve export {filename} for job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve export file")


@router.get("/{job_id}/metadata")
async def get_export_metadata(job_id: str):
    """
    Get metadata about available exports for a job.

    Returns information about:
    - Available export formats
    - File sizes
    - Creation timestamps
    - Download URLs
    - SHA256 checksums
    """
    try:
        export_service = ExportService()

        metadata = await export_service.get_export_metadata(job_id)

        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"No exports found for job {job_id}"
            )

        return {
            "job_id": job_id,
            "formats": metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get export metadata for job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve export metadata")


@router.post("/{job_id}/convert")
async def convert_export(job_id: str, target_format: str):
    """
    Convert existing export to a different format.

    Creates a background job to convert the documentation to the requested format.

    - **target_format**: Desired format (pdf, epub, markdown, json, html)

    Returns conversion job ID and status URL.
    """
    try:
        export_service = ExportService()

        # Validate format
        supported_formats = {"pdf", "epub", "markdown", "json", "html"}
        if target_format.lower() not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {target_format}. Supported: {supported_formats}"
            )

        # Create conversion job
        conversion_id = await export_service.create_conversion(job_id, target_format)

        logger.info(f"Created conversion {conversion_id} for job {job_id} to {target_format}")

        return {
            "conversion_id": conversion_id,
            "job_id": job_id,
            "target_format": target_format,
            "status": "processing",
            "status_url": f"/api/v1/exports/conversions/{conversion_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create conversion for job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create conversion")


@router.get("/conversions/{conversion_id}")
async def get_conversion_status(conversion_id: str):
    """
    Get status of an export conversion job.

    Returns:
    - Conversion progress
    - Status (processing, completed, failed)
    - Download URL (if completed)
    - Error details (if failed)
    """
    try:
        export_service = ExportService()

        status = await export_service.get_conversion_status(conversion_id)

        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Conversion {conversion_id} not found"
            )

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversion status {conversion_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve conversion status")


@router.delete("/{job_id}")
async def delete_exports(job_id: str):
    """
    Delete all export files for a job.

    Removes all generated export files and metadata.
    The job record itself is not deleted.
    """
    try:
        export_service = ExportService()

        deleted = await export_service.delete_exports(job_id)

        logger.info(f"Deleted {deleted} export files for job {job_id}")

        return {
            "job_id": job_id,
            "deleted_files": deleted,
            "message": "Export files deleted successfully"
        }

    except Exception as e:
        logger.error(f"Failed to delete exports for job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete exports")
