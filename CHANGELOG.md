# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-14

### Added - GitHub Repository Scraping

#### Core Features
- **GitHub repository scraping**: Scrape documentation directly from GitHub repositories using GitHub REST API v3
- **URL auto-detection**: Automatically detects and parses GitHub URLs in Streamlit UI
- **Multiple URL format support**:
  - Full repository: `https://github.com/owner/repo`
  - Specific branch: `https://github.com/owner/repo/tree/branch`
  - Folder-specific: `https://github.com/owner/repo/tree/main/docs`
  - Single file: `https://github.com/owner/repo/blob/main/README.md`
  - SSH URLs: `git@github.com:owner/repo.git`

#### GitHub Scraper Module (`src/scrape_api_docs/github_scraper.py`)
- `is_github_url()`: Detects GitHub repository URLs
- `parse_github_url()`: Parses owner, repo, branch, and path from URLs
- `get_repo_tree()`: Fetches repository directory structure using GitHub Trees API
- `get_file_content()`: Downloads raw file content from GitHub
- `convert_relative_links()`: Converts relative markdown links to absolute GitHub URLs
- `scrape_github_repo()`: Main scraping function with rate limiting and error handling

#### Streamlit UI Enhancements
- Auto-detection of GitHub URLs with metadata display (owner, repo, branch, path)
- GitHub-specific configuration section:
  - Personal Access Token input for higher rate limits (5,000/hr vs 60/hr)
  - Max files limiter to prevent rate limiting on large repositories
  - Include metadata toggle for commit info and authors
- Unified interface for both web and GitHub scraping
- Real-time progress tracking for GitHub scraping

#### Documentation
- `docs/github-api-research.md`: Comprehensive GitHub API research and best practices
- `docs/github-integration-plan.md`: Detailed integration architecture and implementation plan
- `docs/github-scraper-implementation.md`: Complete API reference for GitHub scraper
- `docs/github-scraping-guide.md`: User guide with examples and troubleshooting
- `docs/IMPLEMENTATION_SUMMARY.md`: Implementation summary and statistics
- `examples/github_scraper_example.py`: Python usage examples

#### Testing
- `tests/unit/test_github_scraper.py`: Comprehensive test suite with 50+ test cases
  - URL detection and parsing tests
  - GitHub API integration tests with mocks
  - Content processing and filtering tests
  - Integration tests with real repositories (BMAD-METHOD example)
  - Performance and error handling tests

#### Features
- **Documentation file filtering**: Automatically filters for .md, .rst, .txt, .adoc, .textile, .org, .creole, .mediawiki files
- **Directory structure preservation**: Maintains folder hierarchy in output
- **Relative link conversion**: Converts `./file.md` to `https://github.com/owner/repo/blob/branch/file.md`
- **Rate limit monitoring**: Monitors `X-RateLimit-*` headers and handles limits gracefully
- **Authentication support**: Optional Personal Access Token for private repos and higher rate limits
- **Multi-format export**: Compatible with existing PDF, EPUB, HTML, JSON exporters

#### Performance
- Efficient API usage: Uses Git Trees API with `recursive=1` for single-request directory traversal
- Minimal API calls: ~1 + file_count total calls
- Concurrent file downloads: Parallel processing of multiple files
- Smart caching: Reuses HTTP sessions for better performance

#### Security
- Token safety: Tokens stored in memory only, never persisted to disk
- URL validation: All URLs validated before API calls
- Filename sanitization: SecurityValidator prevents path traversal attacks
- SSRF prevention: Validates all generated URLs
- Error handling: Graceful degradation on API failures

### Changed
- **Version**: Bumped from 0.1.0 to 0.2.0
- **Description**: Updated package description to mention GitHub repository scraping
- **Keywords**: Added "github", "github-scraper", "api-docs", "repository-docs"
- **README.md**: Added GitHub repository scraping section to key features
- **streamlit_app.py**: Extended `scrape_with_progress()` to support both web and GitHub URLs
- **__init__.py**: Exported GitHub scraper functions for public API

### Dependencies
No new dependencies added - GitHub scraping uses existing packages:
- `requests`: For GitHub API calls
- `beautifulsoup4`: For HTML parsing (existing)
- `markdownify`: For markdown conversion (existing)

### Fixed
- Improved error handling for invalid GitHub URLs
- Better rate limiting feedback in UI

### Documentation
- 5 new comprehensive documentation files totaling 2,000+ lines
- Updated README.md with GitHub scraping features
- Added CHANGELOG.md for version tracking
- Created usage examples and troubleshooting guides

### Testing
- Added 50+ test cases for GitHub scraper
- Integration tests with real repositories
- Mock fixtures for GitHub API responses
- Performance and error handling tests

---

## [0.1.0] - 2024-XX-XX

### Added
- Initial release with web scraping functionality
- Async architecture with 5-10x performance improvement
- FastAPI REST API with 23+ endpoints
- JavaScript rendering and SPA support via Playwright
- Multiple export formats: Markdown, PDF, EPUB, HTML, JSON
- Streamlit web UI for interactive scraping
- Security features: SSRF prevention, robots.txt compliance
- Docker and Kubernetes deployment support
- Comprehensive test suite with 90%+ coverage

[0.2.0]: https://github.com/thepingdoctor/scrape-api-docs/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/thepingdoctor/scrape-api-docs/releases/tag/v0.1.0
