#!/usr/bin/env python3
"""
GitHub Repository Scraper Example
==================================

This example demonstrates how to use the GitHub repository scraper
to download documentation from public GitHub repositories.

Examples cover:
- Scraping entire repository documentation
- Scraping specific directories
- Scraping single files
- Various GitHub URL formats
- Error handling
"""

from scrape_api_docs import scrape_github_repo, is_github_url, parse_github_url
from scrape_api_docs.config import Config
from scrape_api_docs.logging_config import setup_logging
from scrape_api_docs.exceptions import ValidationException, RateLimitException


def example_basic_usage():
    """Basic usage: Scrape entire repository."""
    print("\n=== Example 1: Basic Repository Scrape ===")

    url = "https://github.com/python/cpython"
    output_path = scrape_github_repo(url, output_dir='./output', max_files=10)

    print(f"✓ Documentation saved to: {output_path}")


def example_specific_directory():
    """Scrape specific directory from repository."""
    print("\n=== Example 2: Scrape Specific Directory ===")

    # Scrape only the docs folder
    url = "https://github.com/python/cpython/tree/main/Doc"
    output_path = scrape_github_repo(url, output_dir='./output', max_files=50)

    print(f"✓ Documentation saved to: {output_path}")


def example_single_file():
    """Scrape single file from repository."""
    print("\n=== Example 3: Scrape Single File ===")

    # Scrape a specific markdown file
    url = "https://github.com/python/cpython/blob/main/README.md"
    output_path = scrape_github_repo(url, output_dir='./output')

    print(f"✓ File saved to: {output_path}")


def example_url_parsing():
    """Parse various GitHub URL formats."""
    print("\n=== Example 4: URL Parsing ===")

    test_urls = [
        "https://github.com/owner/repo",
        "https://github.com/owner/repo/tree/develop/docs",
        "https://github.com/owner/repo/blob/main/README.md",
        "git@github.com:owner/repo.git",
    ]

    for url in test_urls:
        if is_github_url(url):
            parsed = parse_github_url(url)
            print(f"\n✓ {url}")
            print(f"  Owner: {parsed['owner']}")
            print(f"  Repo: {parsed['repo']}")
            print(f"  Branch: {parsed['branch']}")
            print(f"  Path: {parsed['path'] or '(root)'}")
            print(f"  Type: {'file' if parsed['is_file'] else 'directory'}")


def example_with_config():
    """Use custom configuration."""
    print("\n=== Example 5: Custom Configuration ===")

    # Create custom config
    config = Config.load()
    config.set('scraper.timeout', 15)
    config.set('scraper.user_agent', 'MyCustomBot/1.0')

    url = "https://github.com/psf/requests/tree/main/docs"
    output_path = scrape_github_repo(
        url,
        output_dir='./output',
        max_files=20,
        config=config
    )

    print(f"✓ Documentation saved to: {output_path}")


def example_error_handling():
    """Demonstrate error handling."""
    print("\n=== Example 6: Error Handling ===")

    test_cases = [
        ("https://not-github.com/repo", "Invalid URL"),
        ("https://github.com/nonexistent/fake-repo-12345", "Repository not found"),
    ]

    for url, description in test_cases:
        try:
            scrape_github_repo(url, output_dir='./output', max_files=5)
            print(f"✗ {description}: Expected error but succeeded")
        except ValidationException as e:
            print(f"✓ {description}: Caught ValidationException")
            print(f"  Error: {e}")
        except Exception as e:
            print(f"✓ {description}: Caught {type(e).__name__}")
            print(f"  Error: {e}")


def example_rate_limit_handling():
    """Handle GitHub API rate limiting."""
    print("\n=== Example 7: Rate Limit Handling ===")

    urls = [
        "https://github.com/psf/requests",
        "https://github.com/pallets/flask",
        "https://github.com/django/django",
    ]

    for url in urls:
        try:
            output_path = scrape_github_repo(url, output_dir='./output', max_files=5)
            print(f"✓ Scraped: {url}")
        except RateLimitException as e:
            print(f"⚠ Rate limited: {e}")
            print(f"  Retry after: {e.retry_after:.0f} seconds")
            break


def main():
    """Run all examples."""
    # Setup logging
    setup_logging(level='INFO')

    print("GitHub Repository Scraper Examples")
    print("=" * 50)

    # Run examples (comment out any you don't want to run)
    try:
        example_url_parsing()
        # example_basic_usage()  # Uncomment to scrape entire repos
        # example_specific_directory()
        # example_single_file()
        # example_with_config()
        example_error_handling()
        # example_rate_limit_handling()

        print("\n" + "=" * 50)
        print("✓ All examples completed!")

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
