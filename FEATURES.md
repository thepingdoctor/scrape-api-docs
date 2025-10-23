# Documentation Scraper - Feature Overview

## Core Functionality

### Documentation Crawling
- **Automatic Page Discovery**: Recursively discovers all pages within a documentation site
- **Domain Filtering**: Only scrapes pages within the same domain and path
- **Link Deduplication**: Prevents duplicate page processing
- **Query Parameter Stripping**: Removes URL query parameters and fragments for cleaner crawling

### Content Extraction
- **Intelligent Content Detection**: Prioritizes common documentation structures:
  - `<main>` elements
  - `<article>` elements
  - `.main-content` classes
  - `#content` IDs
- **HTML to Markdown Conversion**: Clean conversion using markdownify library
- **Title Extraction**: Automatically extracts and cleans page titles

### Output Generation
- **Single File Output**: All content consolidated into one Markdown file
- **Structured Format**: Clear section headers with original URLs
- **Dynamic Filenames**: Auto-generates descriptive filenames from source URL
- **Timestamp Recording**: Documents when content was scraped

## User Interfaces

### Streamlit Web UI

#### Layout & Design
- **Wide Layout**: Optimized for viewing tables and content
- **Responsive Design**: Works on desktop and tablet screens
- **Custom Styling**: Professional color scheme and progress indicators
- **Informative Sidebar**: Quick access to features, tips, and resources

#### Input & Configuration
- **URL Input Field**: With real-time validation
- **Advanced Settings Panel**:
  - Request timeout configuration (5-60 seconds)
  - Max pages limit (0 = unlimited)
  - Custom output filename option
- **Smart Defaults**: Sensible default values for quick starts

#### Progress Tracking
- **Real-time Updates**: Live feedback during scraping
- **Visual Progress Bar**: Shows completion percentage
- **Metrics Dashboard**:
  - Total pages discovered
  - Pages successfully processed
  - Error count
  - Time elapsed
- **Current Status**: Displays currently processing URL
- **Stop Functionality**: Gracefully cancel ongoing scrapes

#### Results Display
- **Tabbed Interface**:
  - **Overview Tab**: Summary statistics and URL list with status
  - **Preview Tab**: First 5000 characters of generated content
  - **Errors Tab**: Detailed error log with URLs and messages
- **Data Tables**: Sortable, searchable tables for URLs and errors
- **Download Button**: One-click download of results

#### Error Handling
- **URL Validation**: Pre-checks URLs before scraping
- **Network Error Handling**: Graceful failure with detailed messages
- **Error Logging**: All errors captured and displayed
- **Visual Feedback**: Color-coded status indicators

### Command-Line Interface

#### Features
- **Simple Syntax**: `scrape-docs <URL>`
- **Console Output**: Real-time progress messages
- **Error Reporting**: Detailed error messages in terminal
- **File Generation**: Auto-saves to current directory

#### Use Cases
- Scripting and automation
- Server-side execution
- CI/CD integration
- Minimal resource usage

## Technical Features

### Performance
- **Efficient Crawling**: Uses BFS algorithm for page discovery
- **Session Management**: Reuses HTTP sessions for better performance
- **Timeout Controls**: Configurable per-request timeouts
- **Memory Efficient**: Processes pages one at a time

### Reliability
- **Error Recovery**: Continues processing after individual page failures
- **Network Resilience**: Handles connection errors gracefully
- **Status Tracking**: Maintains state throughout operation
- **Safe File Writing**: UTF-8 encoding for international characters

### Flexibility
- **Configurable Timeouts**: Adapt to slow or fast sites
- **Page Limiting**: Option to cap total pages scraped
- **Custom Filenames**: User-defined output names
- **Multiple Entry Points**: CLI and UI available

## Developer Features

### Code Quality
- **Type Hints**: Comprehensive type annotations
- **Documentation**: Detailed docstrings throughout
- **Modular Design**: Separation of concerns
- **Clean Architecture**: UI separated from core logic

### Extensibility
- **Pluggable Scrapers**: Easy to extend content extraction
- **Customizable Selectors**: Can modify HTML selectors
- **Format Flexibility**: Can add new output formats
- **Hook Points**: Can extend with custom processing

### Development Tools
- **Poetry Integration**: Modern dependency management
- **Black Formatting**: Consistent code style
- **Flake8 Linting**: Code quality checks
- **MyPy Support**: Static type checking

## Package Distribution

### Installation Methods
- **Poetry**: `poetry install`
- **Pip**: `pip install git+https://...`
- **Development Mode**: `pip install -e .`

### Entry Points
- **CLI**: `scrape-docs`
- **UI**: `scrape-docs-ui`
- **Direct**: `streamlit run src/scrape_api_docs/streamlit_app.py`

### Dependencies
- **Core**: requests, beautifulsoup4, markdownify
- **UI**: streamlit, pandas
- **Dev**: pytest, black, flake8, mypy

## Use Cases

### Personal
- Offline documentation reading
- Personal knowledge base creation
- Research and reference

### Professional
- Documentation archival
- Internal knowledge management
- Team reference materials
- API documentation backup

### Educational
- Learning resource compilation
- Course material aggregation
- Study guide creation

## Future Enhancement Possibilities

### Potential Features
- PDF export option
- Custom CSS styling for HTML output
- Search index generation
- Multi-language support
- Incremental updates (diff mode)
- Parallel page processing
- Custom content filters
- API endpoint exposure
- Sitemap.xml integration
- robots.txt respect
- Rate limiting controls

### UI Improvements
- Dark mode support
- Export format options
- Scraping history/favorites
- Scheduled scraping
- Browser integration
- Comparison tools

## Limitations

### Current Constraints
- JavaScript-rendered content not supported
- No authentication handling
- Single-threaded processing
- Limited to same-domain crawling
- Requires network connectivity

### Best Practices
- Respect website terms of service
- Follow robots.txt guidelines
- Avoid excessive requests
- Use appropriate timeouts
- Limit page counts for testing

## Performance Benchmarks

### Typical Performance
- Small sites (10-50 pages): 30-60 seconds
- Medium sites (100-500 pages): 2-10 minutes
- Large sites (1000+ pages): 20+ minutes

### Factors Affecting Speed
- Network latency
- Site response time
- Page size
- Number of pages
- Timeout settings
- Content complexity

## Security Considerations

### Data Handling
- Local file storage only
- No external data transmission
- UTF-8 encoding for safety
- No credential storage

### Responsible Use
- Permission-based scraping
- Terms of service compliance
- robots.txt respect
- Rate limiting consideration
