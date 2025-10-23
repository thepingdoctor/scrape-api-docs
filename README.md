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

*   Python 3.8 or higher
*   Poetry (for dependency management and installation)

## Installation

### Using Poetry (Recommended)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/thepingdoctor/scrape-api-docs
    cd scrape-api-docs
    ```

2.  **Install with Poetry:**
    ```bash
    poetry install
    ```

3.  **Activate the virtual environment:**
    ```bash
    poetry shell
    ```

### Using pip (Alternative)

You can also install directly from the repository:
```bash
pip install git+https://github.com/thepingdoctor/scrape-api-docs.git
```

Or install in development mode:
```bash
git clone https://github.com/thepingdoctor/scrape-api-docs
cd scrape-api-docs
pip install -e .
```

### Legacy Method (Direct Script)

If you prefer to use the standalone script without packaging:
```bash
python scrape.py <URL>
```

## Usage

After installation with Poetry or pip, use the `scrape-docs` command:

```bash
scrape-docs <URL>
```

**Example:**
```bash
scrape-docs https://netboxlabs.com/docs/netbox/
```

## Development

### Setting up for development

1.  Clone the repository and install dependencies:
    ```bash
    git clone https://github.com/thepingdoctor/scrape-api-docs
    cd scrape-api-docs
    poetry install
    ```

2.  Run tests (when available):
    ```bash
    poetry run pytest
    ```

3.  Format code with Black:
    ```bash
    poetry run black src/
    ```

4.  Run linting:
    ```bash
    poetry run flake8 src/
    ```

### Building and Publishing

Build the package:
```bash
poetry build
```

Publish to PyPI (requires credentials):
```bash
poetry publish
```

## Disclaimer

This script is designed for legitimate purposes, such as the archival of API documentation for personal or internal team use. Users are responsible for ensuring they have the right to scrape any website and must comply with the website's terms of service and `robots.txt` file. The author is not responsible for any misuse of this script.

This script is provided "as is" without warranty of any kind, express or implied, and no support is provided.
