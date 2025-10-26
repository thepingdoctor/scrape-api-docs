"""Tests for base export classes."""

import pytest
from pathlib import Path
from scrape_api_docs.exporters.base import (
    ExportConverter,
    ExportOptions,
    ExportResult,
    PageResult
)


class TestPageResult:
    """Test PageResult dataclass."""

    def test_create_page_result(self):
        """Test creating a PageResult."""
        page = PageResult(
            url="https://example.com/docs",
            title="Test Page",
            content="# Test Content",
            format="markdown"
        )

        assert page.url == "https://example.com/docs"
        assert page.title == "Test Page"
        assert page.content == "# Test Content"
        assert page.format == "markdown"
        assert page.render_time == 0.0
        assert page.from_cache is False
        assert page.metadata == {}


class TestExportOptions:
    """Test ExportOptions dataclass."""

    def test_default_options(self):
        """Test default export options."""
        options = ExportOptions()

        assert options.include_metadata is True
        assert options.include_toc is True
        assert options.template is None
        assert options.custom_css is None
        assert options.author is None
        assert options.title is None

    def test_custom_options(self):
        """Test custom export options."""
        options = ExportOptions(
            title="My Documentation",
            author="Test Author",
            include_toc=False
        )

        assert options.title == "My Documentation"
        assert options.author == "Test Author"
        assert options.include_toc is False


class TestExportResult:
    """Test ExportResult dataclass."""

    def test_create_successful_result(self):
        """Test creating a successful export result."""
        result = ExportResult(
            format="pdf",
            output_path=Path("/tmp/output.pdf"),
            size_bytes=1024,
            duration=1.5,
            page_count=10,
            success=True
        )

        assert result.format == "pdf"
        assert result.success is True
        assert result.size_bytes == 1024
        assert result.duration == 1.5
        assert result.page_count == 10
        assert result.error is None

    def test_create_failed_result(self):
        """Test creating a failed export result."""
        result = ExportResult(
            format="pdf",
            success=False,
            error="Export failed"
        )

        assert result.format == "pdf"
        assert result.success is False
        assert result.error == "Export failed"


class TestExportConverter:
    """Test ExportConverter base class."""

    def test_sanitize_filename(self):
        """Test filename sanitization."""

        class TestConverter(ExportConverter):
            format_name = "test"
            file_extension = ".test"
            mime_type = "test/test"

            async def convert(self, pages, output_path, options):
                pass

        converter = TestConverter()

        # Test special characters removal
        assert converter._sanitize_filename("test<>file") == "test_file"
        assert converter._sanitize_filename("path/to/file") == "path_to_file"
        assert converter._sanitize_filename("file:name") == "file_name"

        # Test multiple underscores
        assert converter._sanitize_filename("test___file") == "test_file"

        # Test edge trimming
        assert converter._sanitize_filename("_test_") == "test"

    def test_get_capabilities(self):
        """Test getting converter capabilities."""

        class TestConverter(ExportConverter):
            format_name = "test"
            file_extension = ".test"
            mime_type = "test/test"

            async def convert(self, pages, output_path, options):
                pass

        converter = TestConverter()
        capabilities = converter.get_capabilities()

        assert capabilities['format'] == 'test'
        assert capabilities['supports_toc'] is True
        assert capabilities['supports_images'] is True
        assert capabilities['supports_styling'] is True
