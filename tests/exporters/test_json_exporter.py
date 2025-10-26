"""Tests for JSON exporter."""

import pytest
import json
import asyncio
from pathlib import Path
from scrape_api_docs.exporters.json_exporter import JSONExportConverter
from scrape_api_docs.exporters.base import ExportOptions, PageResult


@pytest.fixture
def sample_pages():
    """Create sample pages for testing."""
    return [
        PageResult(
            url="https://example.com/page1",
            title="Page 1",
            content="# Page 1\n\nThis is page 1 content.",
            format="markdown"
        ),
        PageResult(
            url="https://example.com/page2",
            title="Page 2",
            content="<h1>Page 2</h1><p>This is page 2 content.</p>",
            format="html"
        )
    ]


@pytest.fixture
def tmp_output(tmp_path):
    """Create temporary output path."""
    return tmp_path / "output.json"


class TestJSONExportConverter:
    """Test JSON export converter."""

    def test_initialization(self):
        """Test converter initialization."""
        converter = JSONExportConverter()
        assert converter.format_name == "json"
        assert converter.file_extension == ".json"
        assert converter.mime_type == "application/json"

    @pytest.mark.asyncio
    async def test_convert_success(self, sample_pages, tmp_output):
        """Test successful JSON export."""
        converter = JSONExportConverter()
        options = ExportOptions(
            title="Test Documentation",
            author="Test Author"
        )

        result = await converter.convert(sample_pages, tmp_output, options)

        assert result.success is True
        assert result.format == "json"
        assert result.output_path == tmp_output
        assert result.page_count == 2
        assert result.duration > 0

        # Verify JSON file was created
        assert tmp_output.exists()

        # Verify JSON content
        with open(tmp_output, 'r') as f:
            data = json.load(f)

        assert 'metadata' in data
        assert 'pages' in data
        assert 'statistics' in data
        assert 'structure' in data
        assert 'export_info' in data

        assert data['metadata']['title'] == "Test Documentation"
        assert data['metadata']['author'] == "Test Author"
        assert len(data['pages']) == 2

    @pytest.mark.asyncio
    async def test_page_to_dict(self, sample_pages):
        """Test converting page to dictionary."""
        converter = JSONExportConverter()
        page_dict = converter._page_to_dict(sample_pages[0])

        assert page_dict['url'] == "https://example.com/page1"
        assert page_dict['title'] == "Page 1"
        assert 'content' in page_dict
        assert 'structure' in page_dict
        assert 'metadata' in page_dict

        # Check content structure
        assert page_dict['content']['markdown'] == "# Page 1\n\nThis is page 1 content."
        assert page_dict['content']['html'] is None
        assert 'text' in page_dict['content']

        # Check metadata
        assert page_dict['metadata']['word_count'] > 0
        assert page_dict['metadata']['character_count'] > 0

    @pytest.mark.asyncio
    async def test_statistics_calculation(self, sample_pages):
        """Test statistics calculation."""
        converter = JSONExportConverter()
        stats = converter._calculate_statistics(sample_pages)

        assert 'totals' in stats
        assert 'averages' in stats
        assert 'performance' in stats

        assert stats['totals']['pages'] == 2
        assert stats['totals']['words'] > 0
        assert stats['averages']['words_per_page'] > 0

    @pytest.mark.asyncio
    async def test_extract_structure(self, sample_pages):
        """Test structure extraction."""
        converter = JSONExportConverter()
        structure = converter._extract_structure(sample_pages)

        assert structure['total_pages'] == 2
        assert 'hierarchy' in structure
        assert 'navigation' in structure
        assert 'depth' in structure


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
