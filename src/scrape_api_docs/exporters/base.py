"""Base classes and interfaces for export converters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class PageResult:
    """Represents a scraped documentation page."""
    url: str
    title: str
    content: str
    format: str = 'markdown'  # 'markdown' or 'html'
    render_time: float = 0.0
    from_cache: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportOptions:
    """Common export options across all formats."""
    include_metadata: bool = True
    include_toc: bool = True
    template: Optional[str] = None
    custom_css: Optional[str] = None
    author: Optional[str] = None
    title: Optional[str] = None
    cover_image: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class ExportResult:
    """Result of an export operation."""
    format: str
    output_path: Optional[Path] = None
    size_bytes: int = 0
    duration: float = 0.0
    page_count: int = 0
    success: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExportConverter(ABC):
    """Base class for export format converters."""

    format_name: str = ""
    file_extension: str = ""
    mime_type: str = ""

    @abstractmethod
    async def convert(
        self,
        pages: List[PageResult],
        output_path: Path,
        options: ExportOptions
    ) -> ExportResult:
        """
        Convert pages to target format.

        Args:
            pages: List of scraped page results
            output_path: Output file path
            options: Export configuration

        Returns:
            ExportResult with metadata
        """
        pass

    def validate_options(self, options: ExportOptions) -> bool:
        """Validate export options for this format."""
        return True

    def get_capabilities(self) -> Dict[str, Any]:
        """Return converter capabilities."""
        return {
            'format': self.format_name,
            'supports_toc': True,
            'supports_images': True,
            'supports_styling': True,
            'supports_metadata': True
        }

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file system usage."""
        import re
        # Replace special characters with underscores
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove multiple consecutive underscores
        safe_name = re.sub(r'_+', '_', safe_name)
        # Trim underscores from edges
        safe_name = safe_name.strip('_')
        # Limit length
        return safe_name[:200] if len(safe_name) > 200 else safe_name
