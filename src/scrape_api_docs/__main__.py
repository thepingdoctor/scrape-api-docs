"""CLI entry point for the scrape-api-docs package."""

import argparse
from .scraper import scrape_site


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Scrape a documentation website and save all content to a single Markdown file."
    )
    
    parser.add_argument(
        'url', 
        type=str, 
        help="The starting URL of the documentation to scrape (e.g., 'https://netboxlabs.com/docs/netbox/')."
    )

    args = parser.parse_args()
    scrape_site(args.url)
    print("\nScraping task complete.")


if __name__ == "__main__":
    main()
