"""Example usage of the multi-format export system."""

import asyncio
from pathlib import Path
from scrape_api_docs.exporters import (
    ExportOrchestrator,
    ExportOptions,
    PageResult
)


async def main():
    """Demonstrate export system usage."""

    # Sample pages (would normally come from scraper)
    sample_pages = [
        PageResult(
            url="https://example.com/docs/intro",
            title="Introduction",
            content="""# Introduction

Welcome to the documentation!

## Getting Started

Follow these steps to get started:

1. Install the package
2. Configure your settings
3. Run the application

```python
import example
example.run()
```
""",
            format="markdown"
        ),
        PageResult(
            url="https://example.com/docs/api",
            title="API Reference",
            content="""# API Reference

## Functions

### process_data()

Processes input data and returns results.

**Parameters:**
- `data` (str): Input data to process
- `options` (dict): Configuration options

**Returns:**
- Processed data object

**Example:**
```python
result = process_data("input", {"mode": "fast"})
```
""",
            format="markdown"
        ),
        PageResult(
            url="https://example.com/docs/examples",
            title="Examples",
            content="""# Examples

## Basic Usage

Here's a simple example:

```python
from example import Client

client = Client(api_key="your-key")
response = client.fetch_data()
print(response)
```

## Advanced Usage

For more complex scenarios:

```python
from example import Client, Options

options = Options(
    timeout=30,
    retries=3,
    cache=True
)

client = Client(api_key="your-key", options=options)
results = client.batch_process(items)
```
""",
            format="markdown"
        )
    ]

    # Create export orchestrator
    orchestrator = ExportOrchestrator()

    # List available formats
    available_formats = orchestrator.list_available_formats()
    print(f"Available export formats: {', '.join(available_formats)}")

    # Configure export options
    export_options = {
        'pdf': ExportOptions(
            title="Example Documentation",
            author="Documentation Team",
            include_toc=True,
            include_metadata=True
        ),
        'epub': ExportOptions(
            title="Example Documentation",
            author="Documentation Team",
            include_toc=True
        ),
        'json': ExportOptions(
            title="Example Documentation",
            include_metadata=True
        ),
        'html': ExportOptions(
            title="Example Documentation",
            include_toc=True
        )
    }

    # Output directory
    output_dir = Path("./exports")
    output_dir.mkdir(exist_ok=True)

    # Generate all formats in parallel
    print("\nGenerating exports in parallel...")
    results = await orchestrator.generate_exports(
        pages=sample_pages,
        base_url="https://example.com/docs",
        formats=available_formats,  # Export all available formats
        output_dir=output_dir,
        options=export_options
    )

    # Print results
    print("\n" + "=" * 60)
    print("EXPORT RESULTS")
    print("=" * 60)

    for format_name, result in results.items():
        if result.success:
            print(f"\n✓ {format_name.upper()}")
            print(f"  Output: {result.output_path}")
            print(f"  Size: {result.size_bytes:,} bytes")
            print(f"  Duration: {result.duration:.2f}s")
            print(f"  Pages: {result.page_count}")
        else:
            print(f"\n✗ {format_name.upper()}")
            print(f"  Error: {result.error}")

    # Example: Generate single format
    print("\n" + "=" * 60)
    print("SINGLE FORMAT EXPORT")
    print("=" * 60)

    json_output = output_dir / "custom_output.json"
    json_result = await orchestrator.generate_single_export(
        pages=sample_pages,
        format_name="json",
        output_path=json_output,
        options=ExportOptions(
            title="Custom JSON Export",
            include_metadata=True
        )
    )

    if json_result.success:
        print(f"\n✓ JSON export successful")
        print(f"  Output: {json_result.output_path}")
        print(f"  Size: {json_result.size_bytes:,} bytes")

    # Get format information
    print("\n" + "=" * 60)
    print("FORMAT INFORMATION")
    print("=" * 60)

    for format_name in available_formats:
        info = orchestrator.get_format_info(format_name)
        if info:
            print(f"\n{format_name.upper()}:")
            print(f"  Extension: {info['file_extension']}")
            print(f"  MIME type: {info['mime_type']}")
            print(f"  Capabilities: {info['capabilities']}")


if __name__ == '__main__':
    asyncio.run(main())
