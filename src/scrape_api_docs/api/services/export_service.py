"""
Export Service
==============

Manages export generation, conversion, and file serving.
"""

import logging
import hashlib
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
import json

logger = logging.getLogger(__name__)


class ExportService:
    """
    Service for managing export files and conversions.
    """

    def __init__(self, storage_dir: str = ".scraper_storage"):
        """
        Initialize export service.

        Args:
            storage_dir: Directory for storing export files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def get_export_file(self, job_id: str, filename: str) -> Optional[str]:
        """
        Get path to export file.

        Args:
            job_id: Job identifier
            filename: Export filename

        Returns:
            Absolute file path or None if not found
        """
        file_path = self.storage_dir / job_id / filename

        if file_path.exists() and file_path.is_file():
            return str(file_path)

        return None

    async def get_export_metadata(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about available exports.

        Args:
            job_id: Job identifier

        Returns:
            Export metadata or None if no exports found
        """
        job_dir = self.storage_dir / job_id

        if not job_dir.exists():
            return None

        exports = {}

        for file_path in job_dir.glob("*"):
            if file_path.is_file():
                format_name = file_path.suffix.lstrip('.')

                # Calculate checksum
                checksum = self._calculate_checksum(file_path)

                exports[format_name] = {
                    "available": True,
                    "url": f"/api/v1/exports/{job_id}/{file_path.name}",
                    "size_bytes": file_path.stat().st_size,
                    "created_at": file_path.stat().st_mtime,
                    "checksum": checksum
                }

        return exports if exports else None

    async def create_conversion(self, job_id: str, target_format: str) -> str:
        """
        Create export conversion job.

        Args:
            job_id: Source job identifier
            target_format: Target format

        Returns:
            Conversion job ID
        """
        conversion_id = f"conv_{uuid.uuid4().hex[:12]}"

        # TODO: Implement actual conversion queue
        # For now, just return conversion ID

        logger.info(f"Created conversion {conversion_id} for job {job_id} to {target_format}")

        return conversion_id

    async def get_conversion_status(self, conversion_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conversion job status.

        Args:
            conversion_id: Conversion job identifier

        Returns:
            Conversion status or None if not found
        """
        # TODO: Implement conversion status tracking
        # For now, return mock status

        return {
            "conversion_id": conversion_id,
            "status": "completed",
            "progress": 100,
            "download_url": None
        }

    async def delete_exports(self, job_id: str) -> int:
        """
        Delete all export files for a job.

        Args:
            job_id: Job identifier

        Returns:
            Number of files deleted
        """
        job_dir = self.storage_dir / job_id

        if not job_dir.exists():
            return 0

        count = 0
        for file_path in job_dir.glob("*"):
            if file_path.is_file():
                file_path.unlink()
                count += 1

        # Remove directory if empty
        if not any(job_dir.iterdir()):
            job_dir.rmdir()

        logger.info(f"Deleted {count} export files for job {job_id}")

        return count

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()
