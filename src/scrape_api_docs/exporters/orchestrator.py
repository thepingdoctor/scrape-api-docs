"""Export orchestrator for managing multiple format exports."""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional

from .base import ExportOptions, ExportResult, PageResult
from .pdf_exporter import PDFExportConverter
from .epub_exporter import EPUBExportConverter
from .json_exporter import JSONExportConverter
from .html_exporter import HTMLExportConverter

logger = logging.getLogger(__name__)


class ExportOrchestrator:
    """
    Orchestrates multiple export format generation.

    Features:
    - Parallel export generation
    - Error handling per format
    - Progress tracking
    - Result aggregation
    """

    def __init__(self):
        """Initialize orchestrator with all available converters."""
        self.converters = {}

        # Register converters with error handling
        try:
            self.converters['pdf'] = PDFExportConverter()
        except ImportError as e:
            logger.warning(f"PDF export unavailable: {e}")

        try:
            self.converters['epub'] = EPUBExportConverter()
        except ImportError as e:
            logger.warning(f"EPUB export unavailable: {e}")

        try:
            self.converters['json'] = JSONExportConverter()
        except ImportError as e:
            logger.warning(f"JSON export unavailable: {e}")

        try:
            self.converters['html'] = HTMLExportConverter()
        except ImportError as e:
            logger.warning(f"HTML export unavailable: {e}")

    def list_available_formats(self) -> List[str]:
        """List all available export formats."""
        return list(self.converters.keys())

    async def generate_exports(
        self,
        pages: List[PageResult],
        base_url: str,
        formats: List[str],
        output_dir: Path,
        options: Optional[Dict[str, ExportOptions]] = None
    ) -> Dict[str, ExportResult]:
        """
        Generate multiple export formats concurrently.

        Args:
            pages: Scraped pages
            base_url: Source URL
            formats: List of format names
            output_dir: Output directory
            options: Per-format options

        Returns:
            Dictionary mapping format to export result
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Validate formats
        invalid_formats = [f for f in formats if f not in self.converters]
        if invalid_formats:
            logger.warning(f"Unknown formats (skipping): {', '.join(invalid_formats)}")
            formats = [f for f in formats if f in self.converters]

        if not formats:
            logger.error("No valid formats specified")
            return {}

        # Create tasks for each format
        tasks = []
        for format_name in formats:
            converter = self.converters[format_name]

            # Determine output path
            if format_name == 'html':
                # HTML exports to directory
                output_path = output_dir / 'html-export'
            else:
                output_path = output_dir / f"output{converter.file_extension}"

            # Get format-specific options or use defaults
            format_options = (options or {}).get(format_name, ExportOptions())

            # Set source URL if not already set
            if not format_options.source_url:
                format_options.source_url = base_url

            # Create async task
            task = asyncio.create_task(
                self._export_with_error_handling(
                    converter,
                    format_name,
                    pages,
                    output_path,
                    format_options
                )
            )
            tasks.append((format_name, task))

        # Execute in parallel
        results = {}
        for format_name, task in tasks:
            result = await task
            results[format_name] = result

            if result.success:
                logger.info(
                    f"Export {format_name} completed: "
                    f"{result.size_bytes} bytes in {result.duration:.2f}s"
                )
            else:
                logger.error(f"Export {format_name} failed: {result.error}")

        return results

    async def _export_with_error_handling(
        self,
        converter,
        format_name: str,
        pages: List[PageResult],
        output_path: Path,
        options: ExportOptions
    ) -> ExportResult:
        """Execute export with error handling."""
        try:
            return await converter.convert(pages, output_path, options)
        except Exception as e:
            logger.error(f"Export {format_name} failed: {e}", exc_info=True)
            return ExportResult(
                format=format_name,
                success=False,
                error=str(e)
            )

    async def generate_single_export(
        self,
        pages: List[PageResult],
        format_name: str,
        output_path: Path,
        options: Optional[ExportOptions] = None
    ) -> ExportResult:
        """
        Generate a single export format.

        Args:
            pages: Scraped pages
            format_name: Format name (pdf, epub, json, html)
            output_path: Output file path
            options: Export options

        Returns:
            ExportResult
        """
        if format_name not in self.converters:
            return ExportResult(
                format=format_name,
                success=False,
                error=f"Unknown format: {format_name}"
            )

        converter = self.converters[format_name]
        format_options = options or ExportOptions()

        return await self._export_with_error_handling(
            converter,
            format_name,
            pages,
            output_path,
            format_options
        )

    def get_format_info(self, format_name: str) -> Optional[Dict]:
        """Get information about a specific format."""
        if format_name not in self.converters:
            return None

        converter = self.converters[format_name]
        return {
            'format': format_name,
            'file_extension': converter.file_extension,
            'mime_type': converter.mime_type,
            'capabilities': converter.get_capabilities()
        }
