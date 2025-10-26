"""
Job Service
===========

Manages scraping job lifecycle, execution, and state management.
"""

import asyncio
import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, AsyncIterator
from collections import defaultdict
import logging
import uuid

from ..models.responses import (
    JobStatus,
    JobStatusEnum,
    JobProgress,
    JobStatistics,
    ExportInfo,
    JobLogEntry
)

logger = logging.getLogger(__name__)


class JobService:
    """
    Service for managing scraping jobs.

    Handles job creation, execution, status tracking, and result storage.
    """

    def __init__(self, db_path: str = ".scraper_jobs.db", storage_dir: str = ".scraper_storage"):
        """
        Initialize job service.

        Args:
            db_path: SQLite database path for job metadata
            storage_dir: Directory for storing job results
        """
        self.db_path = db_path
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # In-memory job progress tracking
        self.job_progress: Dict[str, Dict] = {}
        self.job_subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)

    async def initialize(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                status TEXT NOT NULL,
                options TEXT,
                export_formats TEXT,
                authentication TEXT,
                webhook_url TEXT,
                priority TEXT,
                metadata TEXT,
                created_at REAL NOT NULL,
                started_at REAL,
                completed_at REAL,
                estimated_duration INTEGER,
                error_message TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_stats (
                job_id TEXT PRIMARY KEY,
                pages_discovered INTEGER DEFAULT 0,
                pages_processed INTEGER DEFAULT 0,
                cache_hits INTEGER DEFAULT 0,
                cache_misses INTEGER DEFAULT 0,
                errors INTEGER DEFAULT 0,
                avg_page_time REAL DEFAULT 0.0,
                total_bytes INTEGER DEFAULT 0,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_exports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                format TEXT NOT NULL,
                file_path TEXT NOT NULL,
                size_bytes INTEGER,
                checksum TEXT,
                created_at REAL NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_job ON job_logs(job_id)')

        conn.commit()
        conn.close()

        logger.info("Job service initialized")

    async def cleanup(self):
        """Cleanup resources."""
        # Close any open connections, cleanup subscribers
        self.job_subscribers.clear()
        logger.info("Job service cleanup complete")

    async def create_job(
        self,
        url: str,
        options: Dict[str, Any],
        export_formats: List[str],
        authentication: Optional[Dict] = None,
        webhook_url: Optional[str] = None,
        priority: str = "normal",
        metadata: Optional[Dict] = None
    ) -> JobStatus:
        """
        Create a new scraping job.

        Args:
            url: Base URL to scrape
            options: Scraping options
            export_formats: Desired export formats
            authentication: Authentication credentials
            webhook_url: Webhook for completion notification
            priority: Job priority
            metadata: Custom metadata

        Returns:
            Created job status
        """
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        created_at = time.time()

        # Estimate duration based on options
        estimated_duration = self._estimate_duration(options)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO jobs (
                job_id, url, status, options, export_formats,
                authentication, webhook_url, priority, metadata,
                created_at, estimated_duration
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job_id,
            url,
            JobStatusEnum.QUEUED.value,
            json.dumps(options),
            json.dumps(export_formats),
            json.dumps(authentication) if authentication else None,
            webhook_url,
            priority,
            json.dumps(metadata) if metadata else None,
            created_at,
            estimated_duration
        ))

        # Initialize statistics
        cursor.execute('''
            INSERT INTO job_stats (job_id) VALUES (?)
        ''', (job_id,))

        conn.commit()
        conn.close()

        logger.info(f"Created job {job_id} for URL {url}")

        return JobStatus(
            job_id=job_id,
            url=url,
            status=JobStatusEnum.QUEUED,
            created_at=datetime.fromtimestamp(created_at),
            estimated_duration=estimated_duration,
            statistics=JobStatistics(),
            exports=[]
        )

    async def get_job(self, job_id: str) -> Optional[JobStatus]:
        """
        Get job status and details.

        Args:
            job_id: Job identifier

        Returns:
            Job status or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT j.*, s.*
            FROM jobs j
            LEFT JOIN job_stats s ON j.job_id = s.job_id
            WHERE j.job_id = ?
        ''', (job_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # Parse row data
        (
            job_id, url, status, options_json, export_formats_json,
            auth_json, webhook_url, priority, metadata_json,
            created_at, started_at, completed_at, estimated_duration, error_message,
            _, pages_discovered, pages_processed, cache_hits, cache_misses,
            errors, avg_page_time, total_bytes
        ) = row

        # Get progress if running
        progress = None
        if status == JobStatusEnum.RUNNING.value and job_id in self.job_progress:
            prog_data = self.job_progress[job_id]
            progress = JobProgress(
                current_page=prog_data.get("current_page", 0),
                total_pages=prog_data.get("total_pages", 0),
                percent_complete=prog_data.get("percent_complete", 0.0),
                current_operation=prog_data.get("current_operation", "Processing")
            )

        # Get exports
        exports = await self._get_job_exports(job_id)

        # Calculate duration
        duration = None
        if started_at and completed_at:
            duration = completed_at - started_at

        return JobStatus(
            job_id=job_id,
            url=url,
            status=JobStatusEnum(status),
            progress=progress,
            created_at=datetime.fromtimestamp(created_at),
            started_at=datetime.fromtimestamp(started_at) if started_at else None,
            completed_at=datetime.fromtimestamp(completed_at) if completed_at else None,
            estimated_completion=None,  # TODO: Calculate based on progress
            duration=duration,
            statistics=JobStatistics(
                pages_discovered=pages_discovered or 0,
                pages_processed=pages_processed or 0,
                cache_hits=cache_hits or 0,
                cache_misses=cache_misses or 0,
                errors=errors or 0,
                avg_page_time=avg_page_time or 0.0,
                total_bytes=total_bytes or 0
            ),
            exports=exports,
            error_message=error_message
        )

    async def list_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        sort: str = "created_at",
        order: str = "desc"
    ) -> Tuple[List[JobStatus], int]:
        """
        List jobs with filtering and pagination.

        Args:
            status: Filter by status
            limit: Results per page
            offset: Pagination offset
            sort: Sort field
            order: Sort order

        Returns:
            Tuple of (jobs list, total count)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build query
        where_clause = f"WHERE j.status = '{status}'" if status else ""
        order_clause = f"ORDER BY j.{sort} {order.upper()}"

        # Get total count
        cursor.execute(f'''
            SELECT COUNT(*) FROM jobs j {where_clause}
        ''')
        total = cursor.fetchone()[0]

        # Get jobs
        cursor.execute(f'''
            SELECT j.*, s.*
            FROM jobs j
            LEFT JOIN job_stats s ON j.job_id = s.job_id
            {where_clause}
            {order_clause}
            LIMIT ? OFFSET ?
        ''', (limit, offset))

        jobs = []
        for row in cursor.fetchall():
            job_id = row[0]
            job = await self.get_job(job_id)
            if job:
                jobs.append(job)

        conn.close()

        return jobs, total

    async def execute_job(self, job_id: str) -> Dict[str, Any]:
        """
        Execute scraping job (to be called in background).

        Args:
            job_id: Job identifier

        Returns:
            Job execution result
        """
        try:
            # Update status to running
            await self._update_job_status(job_id, JobStatusEnum.RUNNING)
            await self._log_job(job_id, "info", "Job started")

            # Get job details
            job = await self.get_job(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # TODO: Implement actual scraping logic using ScraperService
            # For now, simulate execution
            await asyncio.sleep(2)  # Simulate work

            # Update progress
            await self._update_progress(job_id, 50, 100, 50.0, "Processing pages")
            await asyncio.sleep(2)

            await self._update_progress(job_id, 100, 100, 100.0, "Generating exports")
            await asyncio.sleep(1)

            # Mark as completed
            await self._update_job_status(job_id, JobStatusEnum.COMPLETED)
            await self._log_job(job_id, "info", "Job completed successfully")

            return {"status": "completed", "job_id": job_id}

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            await self._update_job_status(job_id, JobStatusEnum.FAILED, str(e))
            await self._log_job(job_id, "error", f"Job failed: {e}")
            raise

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        job = await self.get_job(job_id)
        if not job:
            return False

        await self._update_job_status(job_id, JobStatusEnum.CANCELLED)
        await self._log_job(job_id, "info", "Job cancelled by user")

        return True

    async def retry_job(self, job_id: str) -> Optional[JobStatus]:
        """Create a new job with same configuration as failed job."""
        job = await self.get_job(job_id)
        if not job or job.status != JobStatusEnum.FAILED:
            return None

        # Get original job configuration
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT options, export_formats, authentication FROM jobs WHERE job_id = ?', (job_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        options = json.loads(row[0])
        export_formats = json.loads(row[1])
        authentication = json.loads(row[2]) if row[2] else None

        return await self.create_job(
            url=job.url,
            options=options,
            export_formats=export_formats,
            authentication=authentication,
            priority="normal"
        )

    async def stream_job_updates(self, job_id: str) -> AsyncIterator[Dict]:
        """Stream real-time job updates via async iterator."""
        queue = asyncio.Queue()
        self.job_subscribers[job_id].append(queue)

        try:
            while True:
                update = await queue.get()
                yield update

                # Stop if job completed
                if update.get("type") in ["complete", "error", "cancelled"]:
                    break

        finally:
            self.job_subscribers[job_id].remove(queue)

    async def get_job_logs(
        self,
        job_id: str,
        limit: int = 100,
        level: Optional[str] = None
    ) -> List[JobLogEntry]:
        """Get job execution logs."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        where_clause = f"AND level = '{level}'" if level else ""

        cursor.execute(f'''
            SELECT timestamp, level, message, details
            FROM job_logs
            WHERE job_id = ? {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (job_id, limit))

        logs = []
        for row in cursor.fetchall():
            logs.append(JobLogEntry(
                timestamp=datetime.fromtimestamp(row[0]),
                level=row[1],
                message=row[2],
                details=json.loads(row[3]) if row[3] else None
            ))

        conn.close()
        return logs

    async def get_statistics(self) -> Dict[str, Any]:
        """Get overall system statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Job counts by status
        cursor.execute('''
            SELECT status, COUNT(*)
            FROM jobs
            GROUP BY status
        ''')
        jobs_by_status = {row[0]: row[1] for row in cursor.fetchall()}

        # Performance metrics
        cursor.execute('''
            SELECT
                COUNT(*) as total_jobs,
                AVG(completed_at - started_at) as avg_duration,
                SUM(pages_processed) as total_pages
            FROM jobs j
            JOIN job_stats s ON j.job_id = s.job_id
            WHERE j.status = 'completed'
        ''')
        row = cursor.fetchone()
        total_jobs = row[0] or 0
        avg_duration = row[1] or 0.0
        total_pages = row[2] or 0

        conn.close()

        return {
            "jobs": jobs_by_status,
            "performance": {
                "total_jobs": total_jobs,
                "avg_job_duration": avg_duration,
                "total_pages_scraped": total_pages,
                "cache_hit_rate": 0.0  # TODO: Calculate from cache stats
            },
            "resources": {
                "storage_used_mb": self._get_storage_size(),
                "active_jobs": jobs_by_status.get("running", 0)
            }
        }

    # Private helper methods

    async def _update_job_status(
        self,
        job_id: str,
        status: JobStatusEnum,
        error_message: Optional[str] = None
    ):
        """Update job status in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        timestamp = time.time()

        if status == JobStatusEnum.RUNNING:
            cursor.execute('''
                UPDATE jobs
                SET status = ?, started_at = ?
                WHERE job_id = ?
            ''', (status.value, timestamp, job_id))
        elif status in [JobStatusEnum.COMPLETED, JobStatusEnum.FAILED, JobStatusEnum.CANCELLED]:
            cursor.execute('''
                UPDATE jobs
                SET status = ?, completed_at = ?, error_message = ?
                WHERE job_id = ?
            ''', (status.value, timestamp, error_message, job_id))
        else:
            cursor.execute('''
                UPDATE jobs
                SET status = ?
                WHERE job_id = ?
            ''', (status.value, job_id))

        conn.commit()
        conn.close()

        # Notify subscribers
        await self._notify_subscribers(job_id, {
            "type": "status",
            "data": {"job_id": job_id, "status": status.value}
        })

    async def _update_progress(
        self,
        job_id: str,
        current_page: int,
        total_pages: int,
        percent: float,
        operation: str
    ):
        """Update job progress."""
        self.job_progress[job_id] = {
            "current_page": current_page,
            "total_pages": total_pages,
            "percent_complete": percent,
            "current_operation": operation
        }

        # Notify subscribers
        await self._notify_subscribers(job_id, {
            "type": "progress",
            "data": {
                "job_id": job_id,
                "current_page": current_page,
                "total_pages": total_pages,
                "percent_complete": percent,
                "current_operation": operation
            }
        })

    async def _log_job(
        self,
        job_id: str,
        level: str,
        message: str,
        details: Optional[Dict] = None
    ):
        """Add log entry for job."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO job_logs (job_id, timestamp, level, message, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            job_id,
            time.time(),
            level,
            message,
            json.dumps(details) if details else None
        ))

        conn.commit()
        conn.close()

        # Notify subscribers
        await self._notify_subscribers(job_id, {
            "type": "log",
            "data": {"level": level, "message": message}
        })

    async def _get_job_exports(self, job_id: str) -> List[ExportInfo]:
        """Get list of exports for job."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT format, file_path, size_bytes, checksum, created_at
            FROM job_exports
            WHERE job_id = ?
        ''', (job_id,))

        exports = []
        for row in cursor.fetchall():
            exports.append(ExportInfo(
                format=row[0],
                url=f"/api/v1/exports/{job_id}/{Path(row[1]).name}",
                size_bytes=row[2] or 0,
                created_at=datetime.fromtimestamp(row[4]),
                checksum=row[3]
            ))

        conn.close()
        return exports

    async def _notify_subscribers(self, job_id: str, update: Dict):
        """Notify all subscribers of job update."""
        for queue in self.job_subscribers.get(job_id, []):
            await queue.put(update)

    def _estimate_duration(self, options: Dict) -> int:
        """Estimate job duration based on options."""
        # Simple estimation: 2 seconds per page * max_depth
        max_depth = options.get("max_depth", 10)
        return max_depth * 2

    def _get_storage_size(self) -> float:
        """Get total storage size in MB."""
        total_size = 0
        for file in self.storage_dir.rglob("*"):
            if file.is_file():
                total_size += file.stat().st_size
        return total_size / (1024 * 1024)  # Convert to MB
