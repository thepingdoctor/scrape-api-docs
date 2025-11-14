"""
Quick integration test for GitHub scraping functionality.
Tests basic URL detection and parsing without making actual API calls.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrape_api_docs.github_scraper import (
    is_github_url,
    parse_github_url
)

def test_github_url_detection():
    """Test that GitHub URLs are correctly detected."""
    # Valid GitHub URLs
    assert is_github_url('https://github.com/owner/repo')
    assert is_github_url('https://github.com/owner/repo/tree/main/docs')
    assert is_github_url('https://github.com/bmad-code-org/BMAD-METHOD/tree/main/src/modules/bmm/docs')
    assert is_github_url('git@github.com:owner/repo.git')

    # Invalid URLs
    assert not is_github_url('https://example.com')
    assert not is_github_url('https://gitlab.com/owner/repo')

    print("✅ URL detection tests passed")

def test_github_url_parsing():
    """Test that GitHub URLs are correctly parsed."""
    # Test BMAD-METHOD example
    url = 'https://github.com/bmad-code-org/BMAD-METHOD/tree/main/src/modules/bmm/docs'
    result = parse_github_url(url)

    assert result['owner'] == 'bmad-code-org'
    assert result['repo'] == 'BMAD-METHOD'
    assert result['branch'] == 'main'
    assert result['path'] == 'src/modules/bmm/docs'

    print(f"✅ URL parsing tests passed")
    print(f"   Parsed: {result}")

    # Test simple repo URL
    url2 = 'https://github.com/owner/repo'
    result2 = parse_github_url(url2)

    assert result2['owner'] == 'owner'
    assert result2['repo'] == 'repo'
    assert result2['branch'] == 'main'  # default
    assert result2['path'] == ''

    print(f"✅ Simple URL parsing tests passed")

def test_imports():
    """Test that all necessary functions can be imported."""
    from scrape_api_docs import (
        scrape_site,
        scrape_github_repo,
        is_github_url,
        parse_github_url,
    )

    print("✅ All imports successful")

if __name__ == '__main__':
    print("Running GitHub scraping integration tests...")
    print()

    try:
        test_imports()
        test_github_url_detection()
        test_github_url_parsing()

        print()
        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("GitHub scraping functionality is ready!")
        print("Example usage:")
        print("  from scrape_api_docs import scrape_github_repo")
        print("  scrape_github_repo('https://github.com/owner/repo/tree/main/docs')")

        sys.exit(0)

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)
