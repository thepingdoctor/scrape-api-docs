"""
Example: Scraping Stoplight.io Documentation Sites
==================================================

This example demonstrates how to scrape documentation from Stoplight.io
hosted sites using the scrape-api-docs package.

Stoplight.io is a popular platform for API documentation that uses
dynamic rendering, requiring JavaScript execution to access content.

Features demonstrated:
1. Basic Stoplight scraping with auto-detection
2. Async scraping for better performance
3. Custom output formats (Markdown and JSON)
4. Progress tracking during scraping
5. Error handling and recovery
"""

import asyncio
from scrape_api_docs import scrape_site_async
from scrape_api_docs.stoplight_scraper import (
    scrape_stoplight_site,
    is_stoplight_url,
    parse_stoplight_url
)
from scrape_api_docs.config import Config


# =============================================================================
# Example 1: Basic Stoplight Scraping (Auto-Detection)
# =============================================================================

async def example_basic_scraping():
    """
    Simplest way to scrape a Stoplight site.
    The scraper auto-detects Stoplight URLs and uses the appropriate handler.
    """
    print("=" * 60)
    print("Example 1: Basic Stoplight Scraping")
    print("=" * 60)

    # Example Stoplight URL (replace with actual site)
    url = "https://example.stoplight.io/docs/api"

    # Check if it's a Stoplight URL
    if is_stoplight_url(url):
        print(f"✅ Detected Stoplight URL: {url}")

        # Parse URL to understand structure
        parsed = parse_stoplight_url(url)
        print(f"   Workspace: {parsed['workspace']}")
        print(f"   Project: {parsed['project']}")
        print(f"   Path: {parsed['path'] or '(root)'}")
    else:
        print(f"⚠️  Not a Stoplight URL: {url}")
        return

    # Scrape using auto-detection
    result = await scrape_site_async(
        base_url=url,
        max_pages=50,
        output_dir='./docs',
        output_format='markdown'
    )

    print(f"\n✨ Scraping Complete!")
    print(f"   Pages scraped: {result.pages_successful}")
    print(f"   Output: {result.exports.get('markdown', 'N/A')}")


# =============================================================================
# Example 2: Stoplight-Specific Scraper with Progress
# =============================================================================

async def example_with_progress():
    """
    Use the Stoplight-specific scraper directly with more control.
    Demonstrates progress tracking and custom configuration.
    """
    print("\n" + "=" * 60)
    print("Example 2: Stoplight Scraper with Progress Tracking")
    print("=" * 60)

    url = "https://example.stoplight.io/docs/api"

    # Create custom configuration
    config = Config.load()
    config.set('scraper.politeness_delay', 0.5)  # Faster scraping
    config.set('javascript.timeout', 30000)       # 30 second timeout

    print(f"🔦 Scraping Stoplight site: {url}")
    print(f"   Max pages: 100")
    print(f"   Output format: JSON")

    # Use Stoplight-specific scraper
    output_path = await scrape_stoplight_site(
        url=url,
        output_dir='./docs',
        max_pages=100,
        output_format='json',  # JSON output for structured data
        config=config
    )

    print(f"\n✅ JSON documentation saved to: {output_path}")
    print(f"   This file contains:")
    print(f"   - API endpoints with methods and paths")
    print(f"   - Models and schemas")
    print(f"   - Code examples by language")
    print(f"   - Page content in markdown format")


# =============================================================================
# Example 3: Markdown Output with API Endpoint Extraction
# =============================================================================

async def example_markdown_output():
    """
    Scrape Stoplight site and save as Markdown.
    API endpoints are automatically extracted and included.
    """
    print("\n" + "=" * 60)
    print("Example 3: Markdown Output with API Extraction")
    print("=" * 60)

    url = "https://example.stoplight.io/docs/api"

    print(f"📝 Scraping to Markdown format...")

    output_path = await scrape_stoplight_site(
        url=url,
        output_dir='./docs',
        max_pages=50,
        output_format='markdown',  # Markdown output
        config=None  # Use default config
    )

    print(f"\n✅ Markdown saved to: {output_path}")
    print(f"\n📄 The Markdown file includes:")
    print(f"   - Table of contents")
    print(f"   - API endpoints section")
    print(f"   - Full page content")
    print(f"   - Preserved internal links")


# =============================================================================
# Example 4: Error Handling and Recovery
# =============================================================================

async def example_error_handling():
    """
    Demonstrates proper error handling when scraping Stoplight sites.
    """
    print("\n" + "=" * 60)
    print("Example 4: Error Handling")
    print("=" * 60)

    url = "https://example.stoplight.io/docs/api"

    try:
        print(f"🔍 Attempting to scrape: {url}")

        output_path = await scrape_stoplight_site(
            url=url,
            output_dir='./docs',
            max_pages=100,
            output_format='markdown'
        )

        print(f"✅ Success! Output: {output_path}")

    except Exception as e:
        print(f"❌ Error occurred: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        print(f"\n💡 Common issues:")
        print(f"   - Playwright not installed: pip install playwright")
        print(f"   - Browser not installed: playwright install chromium")
        print(f"   - Network timeout: Check internet connection")
        print(f"   - Invalid URL: Verify Stoplight URL format")


# =============================================================================
# Example 5: Batch Scraping Multiple Stoplight Sites
# =============================================================================

async def example_batch_scraping():
    """
    Scrape multiple Stoplight documentation sites in sequence.
    Useful for organizations with multiple API documentation sites.
    """
    print("\n" + "=" * 60)
    print("Example 5: Batch Scraping Multiple Sites")
    print("=" * 60)

    # List of Stoplight sites to scrape
    sites = [
        "https://api1.stoplight.io/docs/api",
        "https://api2.stoplight.io/docs/api",
        "https://api3.stoplight.io/docs/api",
    ]

    results = []

    for idx, url in enumerate(sites, 1):
        print(f"\n[{idx}/{len(sites)}] Scraping: {url}")

        try:
            output_path = await scrape_stoplight_site(
                url=url,
                output_dir='./docs',
                max_pages=50,
                output_format='markdown'
            )

            results.append({
                'url': url,
                'status': 'success',
                'output': output_path
            })

            print(f"   ✅ Saved to: {output_path}")

        except Exception as e:
            results.append({
                'url': url,
                'status': 'failed',
                'error': str(e)
            })

            print(f"   ❌ Failed: {e}")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Batch Scraping Summary")
    print(f"{'=' * 60}")
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = sum(1 for r in results if r['status'] == 'failed')

    print(f"Total sites: {len(sites)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")


# =============================================================================
# Example 6: Using with Custom Config
# =============================================================================

async def example_custom_config():
    """
    Demonstrates advanced configuration options for Stoplight scraping.
    """
    print("\n" + "=" * 60)
    print("Example 6: Custom Configuration")
    print("=" * 60)

    # Create custom configuration
    config = Config.load()

    # Adjust scraping behavior
    config.set('scraper.timeout', 60)                    # Longer timeout
    config.set('scraper.politeness_delay', 2.0)          # More polite
    config.set('javascript.timeout', 45000)              # 45s JS timeout
    config.set('rate_limiting.requests_per_second', 1.0) # Slower rate

    print("⚙️  Custom configuration:")
    print(f"   Timeout: {config.get('scraper.timeout')}s")
    print(f"   Politeness delay: {config.get('scraper.politeness_delay')}s")
    print(f"   JS timeout: {config.get('javascript.timeout')}ms")

    url = "https://example.stoplight.io/docs/api"

    output_path = await scrape_stoplight_site(
        url=url,
        output_dir='./docs',
        max_pages=50,
        output_format='json',
        config=config  # Use custom config
    )

    print(f"\n✅ Scraped with custom config: {output_path}")


# =============================================================================
# Main Function
# =============================================================================

async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Stoplight.io Documentation Scraping Examples")
    print("=" * 60)
    print("\nThese examples demonstrate various ways to scrape")
    print("Stoplight.io documentation sites.\n")

    # Run examples
    # Note: Comment out examples that use non-existent URLs

    # Example 1: Basic scraping with auto-detection
    # await example_basic_scraping()

    # Example 2: With progress tracking
    # await example_with_progress()

    # Example 3: Markdown output
    # await example_markdown_output()

    # Example 4: Error handling
    # await example_error_handling()

    # Example 5: Batch scraping
    # await example_batch_scraping()

    # Example 6: Custom configuration
    # await example_custom_config()

    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60)
    print("\n💡 Tips:")
    print("   - Uncomment examples above to run them")
    print("   - Replace example URLs with real Stoplight sites")
    print("   - Install Playwright: pip install playwright")
    print("   - Install browsers: playwright install chromium")


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
