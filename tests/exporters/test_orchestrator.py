"""Tests for export orchestrator."""

import pytest
import asyncio
from pathlib import Path
from scrape_api_docs.exporters.orchestrator import ExportOrchestrator
from scrape_api_docs.exporters.base import ExportOptions, PageResult


@pytest.fixture
def sample_pages():
    """Create sample pages for testing."""
    return [
        PageResult(
            url="https://example.com/page1",
            title="Page 1",
            content="# Page 1\n\nContent for page 1.",
            format="markdown"
        ),
        PageResult(
            url="https://example.com/page2",
            title="Page 2",
            content="# Page 2\n\nContent for page 2.",
            format="markdown"
        )
    ]


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "exports"
    output_dir.mkdir()
    return output_dir


class TestExportOrchestrator:
    """Test export orchestrator."""

    def test_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = ExportOrchestrator()
        assert isinstance(orchestrator.converters, dict)
        assert 'json' in orchestrator.converters

    def test_list_available_formats(self):
        """Test listing available formats."""
        orchestrator = ExportOrchestrator()
        formats = orchestrator.list_available_formats()

        assert isinstance(formats, list)
        assert 'json' in formats
        # PDF and EPUB may not be available without dependencies
        # assert len(formats) >= 1

    @pytest.mark.asyncio
    async def test_generate_single_export_json(self, sample_pages, tmp_output_dir):
        """Test generating single JSON export."""
        orchestrator = ExportOrchestrator()
        output_path = tmp_output_dir / "output.json"
        options = ExportOptions(title="Test Documentation")

        result = await orchestrator.generate_single_export(
            pages=sample_pages,
            format_name="json",
            output_path=output_path,
            options=options
        )

        assert result.success is True
        assert result.format == "json"
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_generate_exports_parallel(self, sample_pages, tmp_output_dir):
        """Test generating multiple exports in parallel."""
        orchestrator = ExportOrchestrator()

        # Only test JSON since other formats may not have dependencies
        results = await orchestrator.generate_exports(
            pages=sample_pages,
            base_url="https://example.com",
            formats=["json"],
            output_dir=tmp_output_dir
        )

        assert "json" in results
        assert results["json"].success is True

    @pytest.mark.asyncio
    async def test_invalid_format(self, sample_pages, tmp_output_dir):
        """Test handling of invalid format."""
        orchestrator = ExportOrchestrator()
        output_path = tmp_output_dir / "output.invalid"

        result = await orchestrator.generate_single_export(
            pages=sample_pages,
            format_name="invalid_format",
            output_path=output_path
        )

        assert result.success is False
        assert "Unknown format" in result.error

    def test_get_format_info(self):
        """Test getting format information."""
        orchestrator = ExportOrchestrator()

        # Test JSON format info
        info = orchestrator.get_format_info("json")
        assert info is not None
        assert info['format'] == "json"
        assert info['file_extension'] == ".json"
        assert info['mime_type'] == "application/json"

        # Test invalid format
        invalid_info = orchestrator.get_format_info("invalid")
        assert invalid_info is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
