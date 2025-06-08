# Documentation Scraper

A Python script to crawl and scrape documentation websites, converting their content into a single, consolidated Markdown file. This is useful for offline reading, archiving, or feeding documentation into other systems.

## Features

*   **Site Crawler:** Discovers all unique, internal pages of a documentation site starting from a given base URL.
*   **Content Extraction:** Intelligently extracts the main content from each page, prioritizing common HTML structures like `<main>` tags, or falling back to `article`, `.main-content`, or `#content` selectors.
*   **HTML to Markdown:** Converts the extracted HTML content into clean Markdown.
*   **Consolidated Output:** Combines content from all scraped pages into a single Markdown file.
*   **Dynamic Filename Generation:** Creates a descriptive filename for the output Markdown file based on the source URL.
*   **Error Handling:** Gracefully handles network errors and issues during page processing.
*   **Command-Line Interface:** Easy to use with a simple CLI argument for the target URL.

## Requirements

*   Python 3.x
*   The following Python libraries:
    *   `requests`
    *   `beautifulsoup4`
    *   `markdownify`

## Installation

1.  **Clone the repository (or download the script):**
    ```bash
    git clone https://github.com/thepingdoctor/scrape-api-docs
    cd scrape-api-docs
    ```
    Or, simply download the `scrape.py` file.

2.  **Install dependencies:**
    It's recommended to use a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
    Then install the required packages:
    ```bash
    pip install requests beautifulsoup4 markdownify
    ```

## Usage

Run the script from your terminal, providing the base URL of the documentation site you want to scrape.

```bash
python scrape.py <URL>
```

## Disclaimer

This script is designed for legitimate purposes, such as the archival of API documentation for personal or internal team use. Users are responsible for ensuring they have the right to scrape any website and must comply with the website's terms of service and `robots.txt` file. The author is not responsible for any misuse of this script.

This script is provided "as is" without warranty of any kind, express or implied, and no support is provided.
