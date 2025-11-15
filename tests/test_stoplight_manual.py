"""
Manual/Live testing script for Stoplight scraper
Use this to test against real Stoplight.io sites when needed

IMPORTANT: These tests require:
1. Network connectivity
2. Playwright browsers installed (playwright install chromium)
3. Actual Stoplight.io sites to be available

Run with: pytest tests/test_stoplight_manual.py -v -s --no-cov
Or mark as manual: pytest -m manual
"""

import pytest
import asyncio
from pathlib import Path
from scrape_api_docs.stoplight_scraper import (
    is_stoplight_url,
    scrape_stoplight_site,
    scrape_stoplight_site_sync,
)


# Mark all tests in this module as manual (skip by default)
pytestmark = pytest.mark.manual


class TestLiveStoplightScraping:
    """Live tests against real Stoplight.io sites"""

    @pytest.fixture
    def test_url(self):
        """Test URL for Stoplight site"""
        # Replace with actual Stoplight URL when testing
        return 'https://mycaseapi.stoplight.io/docs/mycase-api-documentation'

    @pytest.fixture
    def output_dir(self, tmp_path):
        """Temporary output directory"""
        return tmp_path / 'stoplight_test_output'

    def test_url_detection(self, test_url):
        """Verify URL is detected as Stoplight"""
        assert is_stoplight_url(test_url), f"URL should be detected as Stoplight: {test_url}"

    @pytest.mark.asyncio
    async def test_async_scraping(self, test_url, output_dir):
        """Test async scraping of Stoplight site"""
        print(f"\n🔍 Testing async scraping of: {test_url}")
        print(f"📁 Output directory: {output_dir}")

        try:
            output_path = await scrape_stoplight_site(
                url=test_url,
                output_dir=str(output_dir),
                max_pages=5,  # Limit for testing
                output_format='markdown'
            )

            print(f"✅ Scraping completed successfully!")
            print(f"📄 Output file: {output_path}")

            # Verify output file exists
            assert Path(output_path).exists(), "Output file should exist"

            # Verify file has content
            file_size = Path(output_path).stat().st_size
            print(f"📊 File size: {file_size} bytes")
            assert file_size > 0, "Output file should not be empty"

            # Read and display sample
            content = Path(output_path).read_text()
            print(f"\n📝 Content preview (first 500 chars):")
            print(content[:500])

        except Exception as e:
            pytest.fail(f"Async scraping failed: {e}")

    def test_sync_scraping(self, test_url, output_dir):
        """Test synchronous wrapper for scraping"""
        print(f"\n🔍 Testing sync scraping of: {test_url}")

        try:
            output_path = scrape_stoplight_site_sync(
                url=test_url,
                output_dir=str(output_dir),
                max_pages=3,  # Even smaller limit for sync test
                output_format='markdown'
            )

            print(f"✅ Sync scraping completed!")
            print(f"📄 Output file: {output_path}")

            assert Path(output_path).exists()

        except Exception as e:
            pytest.fail(f"Sync scraping failed: {e}")

    @pytest.mark.asyncio
    async def test_json_output(self, test_url, output_dir):
        """Test JSON output format"""
        print(f"\n🔍 Testing JSON output format")

        try:
            output_path = await scrape_stoplight_site(
                url=test_url,
                output_dir=str(output_dir),
                max_pages=3,
                output_format='json'
            )

            print(f"✅ JSON export completed!")
            print(f"📄 Output file: {output_path}")

            # Verify JSON file
            assert Path(output_path).exists()
            assert output_path.endswith('.json')

            # Parse JSON
            import json
            content = json.loads(Path(output_path).read_text())

            print(f"📊 JSON structure:")
            print(f"  - Metadata: {bool(content.get('metadata'))}")
            print(f"  - Pages: {len(content.get('pages', []))}")
            print(f"  - Global Index: {bool(content.get('global_index'))}")

        except Exception as e:
            pytest.fail(f"JSON export failed: {e}")


class TestStoplightErrorHandling:
    """Test error handling with live sites"""

    @pytest.mark.asyncio
    async def test_invalid_stoplight_url(self, tmp_path):
        """Should handle invalid Stoplight URLs"""
        print("\n🔍 Testing invalid URL handling")

        try:
            output_path = await scrape_stoplight_site(
                url='https://invalid.stoplight.io/nonexistent',
                output_dir=str(tmp_path),
                max_pages=1,
                output_format='markdown'
            )

            # Should either fail or return minimal output
            if Path(output_path).exists():
                size = Path(output_path).stat().st_size
                print(f"⚠️  Handled gracefully with {size} bytes output")
            else:
                print(f"✅ Correctly failed for invalid URL")

        except Exception as e:
            print(f"✅ Exception caught as expected: {type(e).__name__}")
            # This is expected behavior


# Utility function for manual testing outside pytest
async def manual_test_scrape():
    """
    Manual testing function
    Run with: python tests/test_stoplight_manual.py
    """
    url = 'https://mycaseapi.stoplight.io/docs/mycase-api-documentation'
    output_dir = Path('./tmp/stoplight_test')
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🚀 Starting manual Stoplight scraping test...")
    print(f"📌 URL: {url}")
    print(f"📁 Output: {output_dir}")
    print()

    try:
        output_path = await scrape_stoplight_site(
            url=url,
            output_dir=str(output_dir),
            max_pages=10,
            output_format='markdown'
        )

        print(f"\n✅ Success!")
        print(f"📄 Output: {output_path}")
        print(f"📊 Size: {Path(output_path).stat().st_size} bytes")

        # Also try JSON
        print(f"\n🔄 Creating JSON version...")
        json_output = await scrape_stoplight_site(
            url=url,
            output_dir=str(output_dir),
            max_pages=10,
            output_format='json'
        )
        print(f"📄 JSON Output: {json_output}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # Run manual test
    print("=" * 70)
    print("STOPLIGHT SCRAPER - MANUAL TEST")
    print("=" * 70)
    asyncio.run(manual_test_scrape())
