# Streamlit UI Guide

This guide explains how to use the web interface for the Documentation Scraper.

## Installation

First, ensure you have installed the package with Streamlit support:

```bash
poetry install
```

Or if installing from source:
```bash
pip install -e .
```

## Launching the UI

### Option 1: Using the Command-Line Shortcut

After installation, simply run:

```bash
scrape-docs-ui
```

### Option 2: Using Streamlit Directly

```bash
streamlit run src/scrape_api_docs/streamlit_app.py
```

### Option 3: Within Poetry Environment

```bash
poetry run scrape-docs-ui
```

## Using the Web Interface

### 1. Configuration Section

**Documentation URL:**
- Enter the base URL of the documentation site you want to scrape
- Example: `https://netboxlabs.com/docs/netbox/`
- The URL must include the protocol (http:// or https://)

**Advanced Settings (Optional):**
- **Request Timeout:** How long to wait for each page to load (default: 10 seconds)
- **Max Pages:** Limit the number of pages to scrape (0 = unlimited)
- **Custom Filename:** Specify a custom name for the output file (auto-generated if left empty)

### 2. Starting a Scrape

1. Enter the documentation URL
2. Configure advanced settings if needed
3. Click "🚀 Start Scraping"
4. The scraper will begin discovering and processing pages

### 3. Monitoring Progress

While scraping, you'll see:
- **Progress Bar:** Visual indication of completion
- **Status Message:** Current activity
- **Metrics:**
  - Total Pages: Number of pages discovered
  - Processed: Number of pages successfully scraped
  - Errors: Number of pages that encountered errors
  - Time Elapsed: Duration of the scraping operation
- **Current URL:** The page currently being processed

### 4. Stopping a Scrape

If you need to cancel:
- Click the "⏹️ Stop Scraping" button
- The scraper will stop gracefully after completing the current page

### 5. Viewing Results

After completion, three tabs are available:

**📋 Overview Tab:**
- Summary statistics
- List of all discovered URLs with their status (✅ Processed or ❌ Failed)

**👁️ Preview Tab:**
- Preview of the generated Markdown content (first 5000 characters)
- Gives you a quick look at the output format

**⚠️ Errors Tab:**
- Detailed list of any errors encountered
- Includes the URL and error message for each failure

### 6. Downloading Results

- Click the "⬇️ Download Markdown File" button at the bottom
- The file will be downloaded to your browser's default download location
- The file is also saved to the current working directory

## Features

### Real-time Updates
The UI automatically updates as pages are discovered and processed, giving you live feedback on the scraping progress.

### Error Handling
- Invalid URLs are detected before scraping begins
- Network errors are gracefully handled
- All errors are logged and displayed in the Errors tab

### Responsive Design
- Works on desktop and tablet screens
- Wide layout for better visibility of data tables and content

### Sidebar Information
The sidebar provides:
- Feature overview
- Usage tips
- Links to documentation and GitHub repository

## Tips for Best Results

1. **Start with the Root:** Use the base documentation URL (e.g., `/docs/` not `/docs/page1/`)
2. **Check Errors:** Review the Errors tab to identify problematic pages
3. **Use Max Pages:** For very large sites, set a max page limit for testing
4. **Custom Filename:** Use descriptive names for easier organization of multiple scrapes

## Troubleshooting

**Issue: Scraping is very slow**
- Increase the timeout setting if pages are loading slowly
- Some sites may have rate limiting - consider reducing concurrent requests

**Issue: Many "No main content found" errors**
- The scraper looks for `<main>`, `<article>`, `.main-content`, or `#content` elements
- If your site uses different selectors, you may need to modify the scraper logic

**Issue: Pages are missing**
- Ensure the pages are linked from the base URL
- Check that pages are within the same domain/path
- Some pages may require JavaScript - this scraper only works with static HTML

## Comparison: UI vs CLI

**Use the Streamlit UI when:**
- You want visual feedback during scraping
- You need to preview results before downloading
- You want to see detailed error reports
- You prefer a graphical interface

**Use the CLI when:**
- You're scripting or automating scrapes
- You prefer working in the terminal
- You're running on a headless server
- You want maximum performance (no UI overhead)

## Security Considerations

- Only scrape sites you have permission to access
- Respect robots.txt and terms of service
- Be mindful of server load - avoid excessive requests
- The scraper saves files to the current directory - ensure proper permissions

## Advanced Usage

### Running on a Remote Server

If running on a remote server, use port forwarding:

```bash
# On remote server
streamlit run src/scrape_api_docs/streamlit_app.py --server.port 8501

# On local machine (in another terminal)
ssh -L 8501:localhost:8501 user@remote-server
```

Then access the UI at `http://localhost:8501` on your local machine.

### Custom Port

Run on a custom port:

```bash
streamlit run src/scrape_api_docs/streamlit_app.py --server.port 8080
```

### Disable CORS (for development)

```bash
streamlit run src/scrape_api_docs/streamlit_app.py --server.enableCORS false
```

## Support

For issues or questions:
- Check the main [README.md](README.md)
- Visit the [GitHub repository](https://github.com/thepingdoctor/scrape-api-docs)
- Review existing issues or create a new one
