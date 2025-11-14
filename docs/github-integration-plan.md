# GitHub Scraper Integration Plan

**Version:** 1.0
**Date:** 2025-11-14
**Analyst:** Hive Mind Analyst Agent
**Session:** swarm-1763159183466-ozce54lgp

---

## Executive Summary

This document outlines the integration strategy for adding GitHub repository documentation scraping capabilities to the existing web scraper application. The integration will support both web and GitHub sources through a unified interface while maintaining backwards compatibility.

### Key Objectives
1. ✅ Enable seamless GitHub repository documentation scraping
2. ✅ Maintain backwards compatibility with existing web scraping
3. ✅ Provide unified user experience in both CLI and Streamlit UI
4. ✅ Leverage existing export system for multiple output formats
5. ✅ Implement intelligent URL detection and routing

---

## 1. Current Codebase Analysis

### 1.1 Existing Architecture

**Core Components:**

```
src/scrape_api_docs/
├── scraper.py              # Web scraping logic (485 lines)
├── streamlit_app.py        # UI interface (768 lines)
├── __main__.py             # CLI entry point (26 lines)
├── config.py               # Configuration management (312 lines)
├── rate_limiter.py         # Rate limiting
├── robots.py               # Robots.txt compliance
├── security.py             # Security validation
└── exporters/              # Export format handlers
    ├── orchestrator.py     # Multi-format export coordination
    ├── pdf_exporter.py
    ├── epub_exporter.py
    ├── json_exporter.py
    └── html_exporter.py
```

**Key Features:**
- ✅ Robots.txt compliance
- ✅ Rate limiting (adaptive throttling)
- ✅ SSRF protection
- ✅ Multiple user agents
- ✅ Multi-format export (MD, PDF, EPUB, HTML, JSON)
- ✅ Real-time progress tracking
- ✅ Async support

### 1.2 Integration Points Identified

1. **URL Entry Points**
   - Streamlit: `st.text_input()` at line 300
   - CLI: `args.url` at line 19

2. **Processing Pipeline**
   - `get_all_site_links()` - URL discovery
   - `scrape_with_progress()` - Content extraction
   - `ExportOrchestrator.generate_exports()` - Format conversion

3. **Configuration System**
   - YAML-based with environment variable overrides
   - Extensible for GitHub-specific settings

4. **Export System**
   - Format-agnostic `PageResult` objects
   - Parallel export generation
   - Error handling per format

---

## 2. GitHub Scraper Integration Strategy

### 2.1 Unified Scraper Interface

**Design Pattern:** Strategy Pattern with Factory

```python
# New file: src/scrape_api_docs/scraper_factory.py

from abc import ABC, abstractmethod
from typing import List, Optional
from .exporters.base import PageResult

class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    @abstractmethod
    def detect_url_type(self, url: str) -> bool:
        """Check if this scraper can handle the URL."""
        pass

    @abstractmethod
    def scrape(
        self,
        url: str,
        max_pages: Optional[int] = None,
        **kwargs
    ) -> List[PageResult]:
        """Scrape content and return PageResult objects."""
        pass

    @abstractmethod
    def get_metadata(self, url: str) -> dict:
        """Get metadata about the source."""
        pass

class WebScraper(BaseScraper):
    """Web documentation scraper (existing logic)."""

    def detect_url_type(self, url: str) -> bool:
        return not GitHubScraper().detect_url_type(url)

    def scrape(self, url: str, **kwargs) -> List[PageResult]:
        # Existing scraper.py logic
        pass

class GitHubScraper(BaseScraper):
    """GitHub repository scraper (new)."""

    def detect_url_type(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.netloc in ['github.com', 'raw.githubusercontent.com']

    def scrape(self, url: str, **kwargs) -> List[PageResult]:
        # GitHub-specific scraping logic
        pass

class ScraperFactory:
    """Factory to create appropriate scraper based on URL."""

    @staticmethod
    def create_scraper(url: str) -> BaseScraper:
        if GitHubScraper().detect_url_type(url):
            return GitHubScraper()
        return WebScraper()
```

### 2.2 URL Detection Strategy

**GitHub URL Patterns:**

```python
# New file: src/scrape_api_docs/url_detector.py

import re
from urllib.parse import urlparse
from typing import Tuple, Optional

class URLDetector:
    """Intelligent URL type detection."""

    GITHUB_PATTERNS = [
        r'^https?://github\.com/[\w-]+/[\w-]+/?.*',
        r'^https?://raw\.githubusercontent\.com/.*',
        r'^https?://[\w-]+\.github\.io/.*',
    ]

    @classmethod
    def detect_source_type(cls, url: str) -> Tuple[str, dict]:
        """
        Detect URL source type.

        Returns:
            Tuple of (source_type, metadata)
            source_type: 'github' | 'web'
        """
        parsed = urlparse(url)

        # GitHub detection
        if parsed.netloc == 'github.com':
            parts = parsed.path.strip('/').split('/')
            if len(parts) >= 2:
                return 'github', {
                    'owner': parts[0],
                    'repo': parts[1],
                    'path': '/'.join(parts[2:]) if len(parts) > 2 else '',
                    'type': 'repository'
                }

        if parsed.netloc == 'raw.githubusercontent.com':
            return 'github', {'type': 'raw'}

        if parsed.netloc.endswith('.github.io'):
            return 'github', {'type': 'github_pages'}

        # Default to web
        return 'web', {'domain': parsed.netloc}

    @classmethod
    def extract_github_info(cls, url: str) -> Optional[dict]:
        """Extract GitHub owner/repo/path from URL."""
        parsed = urlparse(url)

        if parsed.netloc != 'github.com':
            return None

        parts = parsed.path.strip('/').split('/')
        if len(parts) < 2:
            return None

        return {
            'owner': parts[0],
            'repo': parts[1],
            'branch': parts[3] if len(parts) > 3 and parts[2] == 'tree' else 'main',
            'path': '/'.join(parts[4:]) if len(parts) > 4 and parts[2] == 'tree' else '',
            'url_type': parts[2] if len(parts) > 2 else 'root'
        }
```

---

## 3. Streamlit UI Modifications

### 3.1 URL Input Detection

**Location:** `streamlit_app.py`, line 300

**Changes Required:**

```python
# Current:
url = st.text_input(
    "Documentation URL",
    placeholder="https://example.com/docs/",
    ...
)

# Enhanced:
url = st.text_input(
    "Documentation URL or GitHub Repository",
    placeholder="https://github.com/owner/repo or https://example.com/docs/",
    help="Enter a website URL or GitHub repository to scrape",
    key="url_input",
)

# Add URL type indicator
if url:
    source_type, metadata = URLDetector.detect_source_type(url)

    if source_type == 'github':
        st.info(
            f"🐙 **GitHub Repository Detected**\n\n"
            f"Owner: `{metadata.get('owner', 'N/A')}`  \n"
            f"Repository: `{metadata.get('repo', 'N/A')}`  \n"
            f"Path: `{metadata.get('path', '/') or '/'}`"
        )

        # GitHub-specific options
        with st.expander("🐙 GitHub Options"):
            col1, col2 = st.columns(2)

            with col1:
                github_token = st.text_input(
                    "GitHub Token (optional)",
                    type="password",
                    help="Provide token for higher rate limits and private repos"
                )

                include_issues = st.checkbox(
                    "Include Issues",
                    value=False,
                    help="Scrape repository issues as documentation"
                )

            with col2:
                include_wiki = st.checkbox(
                    "Include Wiki",
                    value=True,
                    help="Include repository wiki pages"
                )

                include_discussions = st.checkbox(
                    "Include Discussions",
                    value=False,
                    help="Include GitHub Discussions"
                )

    else:
        st.success(f"🌐 **Web Documentation Detected**: {metadata.get('domain')}")
```

### 3.2 Progress Tracking Enhancement

**Location:** `streamlit_app.py`, function `scrape_with_progress`

**Changes:**

```python
def scrape_with_progress(
    state: ScraperState,
    base_url: str,
    source_type: str = 'web',  # NEW
    github_options: dict = None,  # NEW
    **kwargs
):
    """
    Scrape documentation with source-specific handling.

    Args:
        source_type: 'web' or 'github'
        github_options: GitHub-specific options (token, include_wiki, etc.)
    """
    state.source_type = source_type  # Track source type

    if source_type == 'github':
        state.status_message = "Initializing GitHub scraper..."
        # Use GitHub scraper
        scraper = ScraperFactory.create_scraper(base_url)
        # ... GitHub-specific progress tracking
    else:
        # Existing web scraping logic
        ...
```

### 3.3 Results Section Updates

**Location:** `streamlit_app.py`, function `render_results_section`

**Add source-specific metadata display:**

```python
# In Summary tab
if state.source_type == 'github':
    summary_data["Source Type"] = "🐙 GitHub Repository"
    summary_data["Repository"] = f"{metadata['owner']}/{metadata['repo']}"
    summary_data["Files Scraped"] = len(state.processed_files)
else:
    summary_data["Source Type"] = "🌐 Web Documentation"
    summary_data["Pages Scraped"] = len(state.processed_urls)
```

---

## 4. CLI Modifications

### 4.1 Argument Additions

**Location:** `__main__.py`

**Current CLI:**
```bash
scrape-api-docs https://example.com/docs/
```

**Enhanced CLI:**
```bash
# Existing web scraping
scrape-api-docs https://example.com/docs/

# GitHub scraping (auto-detected)
scrape-api-docs https://github.com/owner/repo

# GitHub with options
scrape-api-docs https://github.com/owner/repo \
    --github-token $GITHUB_TOKEN \
    --include-wiki \
    --include-issues \
    --max-files 100

# Explicit source type
scrape-api-docs https://example.com \
    --source-type web
```

**Implementation:**

```python
# src/scrape_api_docs/__main__.py

import argparse
from .url_detector import URLDetector
from .scraper_factory import ScraperFactory

def main():
    parser = argparse.ArgumentParser(
        description="Scrape documentation from websites or GitHub repositories."
    )

    # Core arguments
    parser.add_argument(
        'url',
        type=str,
        help="Documentation URL or GitHub repository"
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default='.',
        help="Output directory for scraped content"
    )

    parser.add_argument(
        '--formats',
        nargs='+',
        default=['markdown'],
        choices=['markdown', 'pdf', 'epub', 'html', 'json'],
        help="Export formats (default: markdown)"
    )

    # Source type (usually auto-detected)
    parser.add_argument(
        '--source-type',
        choices=['auto', 'web', 'github'],
        default='auto',
        help="Source type (auto-detected if not specified)"
    )

    # Web scraping options
    web_group = parser.add_argument_group('web scraping options')
    web_group.add_argument(
        '--max-pages',
        type=int,
        default=100,
        help="Maximum pages to scrape (web only)"
    )
    web_group.add_argument(
        '--user-agent',
        type=str,
        help="User agent string or identifier"
    )
    web_group.add_argument(
        '--no-robots',
        action='store_true',
        help="Ignore robots.txt rules"
    )

    # GitHub-specific options
    github_group = parser.add_argument_group('github scraping options')
    github_group.add_argument(
        '--github-token',
        type=str,
        help="GitHub personal access token"
    )
    github_group.add_argument(
        '--include-wiki',
        action='store_true',
        help="Include repository wiki pages"
    )
    github_group.add_argument(
        '--include-issues',
        action='store_true',
        help="Include repository issues"
    )
    github_group.add_argument(
        '--include-discussions',
        action='store_true',
        help="Include GitHub Discussions"
    )
    github_group.add_argument(
        '--max-files',
        type=int,
        default=1000,
        help="Maximum files to scrape (GitHub only)"
    )
    github_group.add_argument(
        '--branch',
        type=str,
        default='main',
        help="Git branch to scrape (default: main)"
    )

    args = parser.parse_args()

    # Detect source type
    if args.source_type == 'auto':
        source_type, metadata = URLDetector.detect_source_type(args.url)
    else:
        source_type = args.source_type

    # Create appropriate scraper
    scraper = ScraperFactory.create_scraper(args.url)

    # Build options dict
    options = {
        'output_dir': args.output_dir,
        'formats': args.formats,
    }

    if source_type == 'github':
        options.update({
            'github_token': args.github_token,
            'include_wiki': args.include_wiki,
            'include_issues': args.include_issues,
            'include_discussions': args.include_discussions,
            'max_files': args.max_files,
            'branch': args.branch,
        })
    else:
        options.update({
            'max_pages': args.max_pages,
            'user_agent': args.user_agent,
            'respect_robots': not args.no_robots,
        })

    # Execute scraping
    print(f"Scraping {source_type} source: {args.url}")
    results = scraper.scrape(args.url, **options)

    print(f"\nScraping complete: {len(results)} items processed")

if __name__ == "__main__":
    main()
```

---

## 5. Configuration Management

### 5.1 GitHub Configuration Section

**Location:** `config.py`, DEFAULTS dict

**Add GitHub section:**

```python
DEFAULTS = {
    # ... existing sections ...

    'github': {
        'enabled': True,
        'api_base_url': 'https://api.github.com',
        'rate_limit_requests': 60,  # Unauthenticated limit
        'rate_limit_authenticated': 5000,  # With token
        'timeout': 10,
        'max_file_size': 10 * 1024 * 1024,  # 10MB per file
        'supported_extensions': [
            '.md', '.rst', '.txt', '.adoc',
            '.py', '.js', '.ts', '.java', '.go', '.rs',
            # Documentation file extensions
        ],
        'exclude_paths': [
            'node_modules/',
            'vendor/',
            '.git/',
            '__pycache__/',
            'dist/',
            'build/',
        ],
        'include_wiki': True,
        'include_issues': False,
        'include_discussions': False,
        'default_branch': 'main',
    }
}

# Environment variable mapping
ENV_VARS = {
    # ... existing mappings ...
    'github.api_base_url': 'GITHUB_API_URL',
    'github.rate_limit_requests': 'GITHUB_RATE_LIMIT',
    'github.default_branch': 'GITHUB_DEFAULT_BRANCH',
}
```

---

## 6. Rate Limiting Strategy

### 6.1 Unified Rate Limiter

**Challenge:** Different rate limits for web vs GitHub

**Solution:** Polymorphic rate limiters

```python
# src/scrape_api_docs/rate_limiters.py

class BaseRateLimiter(ABC):
    @abstractmethod
    def acquire(self, resource: str):
        pass

class WebRateLimiter(BaseRateLimiter):
    """Existing rate limiter for web scraping."""
    # Current implementation
    pass

class GitHubRateLimiter(BaseRateLimiter):
    """GitHub API-specific rate limiter."""

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.limit = 5000 if token else 60
        self.remaining = self.limit
        self.reset_time = None

    def check_rate_limit_headers(self, response):
        """Parse GitHub rate limit headers."""
        self.remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
        self.reset_time = int(response.headers.get('X-RateLimit-Reset', 0))

    def acquire(self, resource: str):
        """Wait if necessary based on rate limits."""
        if self.remaining <= 1:
            wait_time = self.reset_time - time.time()
            if wait_time > 0:
                logger.warning(f"GitHub rate limit reached, waiting {wait_time}s")
                time.sleep(wait_time)
```

### 6.2 Rate Limit Coordination

**Web Scraping:**
- Respect robots.txt crawl-delay
- Adaptive throttling based on server responses
- Typical: 0.5-2 requests/second

**GitHub API:**
- 60 requests/hour (unauthenticated)
- 5,000 requests/hour (authenticated)
- Monitor `X-RateLimit-*` headers
- Implement exponential backoff

---

## 7. Error Handling & Edge Cases

### 7.1 GitHub-Specific Errors

```python
# src/scrape_api_docs/exceptions.py

class GitHubException(Exception):
    """Base exception for GitHub scraping errors."""
    pass

class GitHubRateLimitException(GitHubException):
    """GitHub API rate limit exceeded."""
    pass

class GitHubAuthException(GitHubException):
    """GitHub authentication failed."""
    pass

class GitHubNotFoundError(GitHubException):
    """Repository or resource not found."""
    pass

class GitHubPrivateRepoError(GitHubException):
    """Attempted to access private repo without auth."""
    pass
```

### 7.2 Error Scenarios

| Scenario | Detection | Handling |
|----------|-----------|----------|
| Invalid GitHub URL | URL parsing | Show error with valid format examples |
| Private repository | 404 response | Prompt for GitHub token |
| Rate limit exceeded | 403 + headers | Wait and retry, show progress |
| Network timeout | Request timeout | Retry with exponential backoff |
| Large repository (10k+ files) | Tree API response | Paginate or limit scope |
| Binary files | Content-Type header | Skip or extract metadata only |
| Mixed web/GitHub URLs | URL detector conflict | Explicit --source-type flag |

---

## 8. Backwards Compatibility

### 8.1 Compatibility Matrix

| Feature | Before | After | Compatible? |
|---------|--------|-------|-------------|
| CLI: `scrape-api-docs https://example.com` | ✅ Works | ✅ Works | ✅ Yes |
| Streamlit: Web URL input | ✅ Works | ✅ Works | ✅ Yes |
| Config files | ✅ YAML | ✅ YAML + GitHub section | ✅ Yes (optional) |
| Export formats | ✅ All formats | ✅ All formats | ✅ Yes |
| Python API: `scrape_site(url)` | ✅ Works | ⚠️ Use `ScraperFactory` | ⚠️ Deprecated path |

### 8.2 Migration Path

**For existing users:**

1. **No changes required** - Web scraping works identically
2. **Optional GitHub features** - Activated by URL pattern
3. **Config backward compatible** - GitHub section optional
4. **Deprecation warnings** - Direct `scraper.py` imports

**Deprecation strategy:**

```python
# scraper.py

import warnings

def scrape_site(url: str, **kwargs):
    """
    Legacy function - maintained for backwards compatibility.

    .. deprecated:: 0.5.0
        Use :class:`ScraperFactory` instead.
    """
    warnings.warn(
        "scrape_site() is deprecated, use ScraperFactory.create_scraper()",
        DeprecationWarning,
        stacklevel=2
    )

    scraper = ScraperFactory.create_scraper(url)
    return scraper.scrape(url, **kwargs)
```

---

## 9. Output Format Differences

### 9.1 Web vs GitHub Output Structure

**Web Scraping Output:**
```markdown
# Documentation for Example Docs
**Source:** https://example.com/docs/
**Scraped:** 2025-11-14 22:00:00

## Getting Started
**Original Page:** `https://example.com/docs/start`
[content]

## API Reference
**Original Page:** `https://example.com/docs/api`
[content]
```

**GitHub Scraping Output:**
```markdown
# Documentation for owner/repository
**Source:** https://github.com/owner/repository
**Scraped:** 2025-11-14 22:00:00
**Branch:** main

## README.md
**File Path:** `/README.md`
[content]

## docs/getting-started.md
**File Path:** `/docs/getting-started.md`
[content]

## Wiki: Installation
**Wiki Page:** `Installation`
[content]
```

### 9.2 Metadata Differences

**PageResult adjustments:**

```python
# src/scrape_api_docs/exporters/base.py

@dataclass
class PageResult:
    url: str                    # Web URL or file path
    title: str
    content: str
    format: str = 'markdown'

    # Source-specific metadata
    source_type: str = 'web'    # NEW: 'web' or 'github'

    # GitHub-specific fields
    file_path: Optional[str] = None           # GitHub file path
    repository: Optional[str] = None          # owner/repo
    branch: Optional[str] = None              # Git branch
    commit_sha: Optional[str] = None          # Commit hash
    author: Optional[str] = None              # Last author
    last_modified: Optional[datetime] = None  # Last commit date

    # Web-specific fields
    original_url: Optional[str] = None        # Original page URL
    crawled_from: Optional[str] = None        # Parent URL
```

---

## 10. Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Create `URLDetector` class
- [ ] Implement `ScraperFactory` pattern
- [ ] Create `BaseScraper` abstract class
- [ ] Add GitHub config section
- [ ] Write unit tests for URL detection

### Phase 2: GitHub Scraper Core (Week 2)
- [ ] Implement `GitHubScraper` class
- [ ] Add GitHub API client
- [ ] Implement file tree traversal
- [ ] Add GitHub-specific rate limiter
- [ ] Handle authentication (token)

### Phase 3: UI Integration (Week 3)
- [ ] Update Streamlit URL input
- [ ] Add GitHub options UI
- [ ] Implement source-specific progress tracking
- [ ] Update results display
- [ ] Test multi-format export with GitHub

### Phase 4: CLI Enhancement (Week 4)
- [ ] Add CLI arguments for GitHub
- [ ] Implement argument validation
- [ ] Update help text and examples
- [ ] Test CLI with both sources

### Phase 5: Advanced Features (Week 5)
- [ ] Add wiki scraping
- [ ] Add issues scraping (optional)
- [ ] Implement discussions support (optional)
- [ ] Add repository metadata export
- [ ] Performance optimization

### Phase 6: Testing & Documentation (Week 6)
- [ ] Integration tests (web + GitHub)
- [ ] End-to-end tests
- [ ] Update documentation
- [ ] Create migration guide
- [ ] Performance benchmarks

---

## 11. Testing Strategy

### 11.1 Unit Tests

```python
# tests/test_url_detector.py

class TestURLDetector:
    def test_detect_github_repo(self):
        url = "https://github.com/owner/repo"
        source_type, metadata = URLDetector.detect_source_type(url)

        assert source_type == 'github'
        assert metadata['owner'] == 'owner'
        assert metadata['repo'] == 'repo'

    def test_detect_web_url(self):
        url = "https://docs.example.com/api"
        source_type, metadata = URLDetector.detect_source_type(url)

        assert source_type == 'web'
        assert metadata['domain'] == 'docs.example.com'

    def test_github_pages_url(self):
        url = "https://owner.github.io/project"
        source_type, metadata = URLDetector.detect_source_type(url)

        assert source_type == 'github'
        assert metadata['type'] == 'github_pages'
```

### 11.2 Integration Tests

```python
# tests/integration/test_github_scraping.py

class TestGitHubScraping:
    @pytest.mark.integration
    def test_scrape_public_repo(self):
        """Test scraping a small public repository."""
        scraper = GitHubScraper()
        results = scraper.scrape(
            "https://github.com/octocat/Hello-World",
            max_files=10
        )

        assert len(results) > 0
        assert any(r.title == 'README' for r in results)

    @pytest.mark.integration
    def test_scrape_with_token(self):
        """Test authenticated scraping."""
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            pytest.skip("GITHUB_TOKEN not set")

        scraper = GitHubScraper(token=token)
        # Test with higher rate limits
        ...
```

---

## 12. Performance Considerations

### 12.1 Bottlenecks & Optimizations

| Component | Potential Bottleneck | Mitigation Strategy |
|-----------|---------------------|---------------------|
| **GitHub API** | Rate limits (60/hr) | Require token for large repos |
| **File downloads** | Sequential fetching | Parallel download with async |
| **Large repos** | 1000+ files | Pagination, selective scraping |
| **Binary files** | Wasted bandwidth | Filter by extension, content-type |
| **Export generation** | CPU-intensive (PDF) | Already parallelized ✅ |

### 12.2 Optimization Strategies

1. **Lazy Loading**: Only fetch file content when needed
2. **Tree API**: Use git tree API for bulk metadata
3. **Caching**: Cache API responses (repository metadata)
4. **Filtering**: User-configurable file type filters
5. **Streaming**: Stream large file downloads

---

## 13. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                          │
├───────────────────────────────┬─────────────────────────────────┤
│     Streamlit UI              │         CLI                      │
│  - URL input with detection   │  - Auto-detect source type       │
│  - Source-specific options    │  - Unified argument structure    │
│  - Real-time progress         │  - Format selection              │
└───────────────┬───────────────┴───────────────┬─────────────────┘
                │                               │
                └───────────────┬───────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   URLDetector         │
                    │  - Pattern matching   │
                    │  - Metadata extraction│
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   ScraperFactory      │
                    │  - Create scraper     │
                    │  - Route requests     │
                    └───────────┬───────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
    ┌───────────▼───────────┐       ┌──────────▼──────────┐
    │   WebScraper          │       │   GitHubScraper     │
    │ - Existing logic      │       │ - API client        │
    │ - robots.txt          │       │ - File tree         │
    │ - Rate limiting       │       │ - Wiki/Issues       │
    └───────────┬───────────┘       └──────────┬──────────┘
                │                               │
                └───────────────┬───────────────┘
                                │
                                │ PageResult[]
                                │
                    ┌───────────▼───────────┐
                    │  ExportOrchestrator   │
                    │  - Multi-format       │
                    │  - Parallel export    │
                    │  - Error handling     │
                    └───────────┬───────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │           │           │           │           │
    ┌───▼───┐   ┌───▼───┐  ┌───▼───┐  ┌───▼───┐   ┌───▼───┐
    │  MD   │   │  PDF  │  │  EPUB │  │  HTML │   │  JSON │
    └───────┘   └───────┘  └───────┘  └───────┘   └───────┘
```

---

## 14. Recommendations

### 14.1 Critical Path Items

1. **✅ HIGH PRIORITY**
   - URL detection (blocks all other work)
   - ScraperFactory implementation
   - GitHub API client with rate limiting
   - Basic file scraping functionality

2. **✅ MEDIUM PRIORITY**
   - Streamlit UI updates
   - CLI argument additions
   - Wiki scraping support
   - Configuration management

3. **✅ LOW PRIORITY**
   - Issues scraping
   - Discussions scraping
   - Advanced filtering
   - Performance optimizations

### 14.2 Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| GitHub rate limit issues | HIGH | HIGH | Require token, add retry logic, show clear errors |
| Large repo performance | MEDIUM | HIGH | Add file count limits, selective scraping, progress feedback |
| Breaking changes to web scraping | LOW | HIGH | Comprehensive test suite, deprecation warnings |
| Export format compatibility | LOW | MEDIUM | Use existing PageResult structure, add optional fields |
| Complex UI changes | MEDIUM | MEDIUM | Incremental updates, feature flags |

### 14.3 Success Metrics

- ✅ No regression in web scraping functionality
- ✅ GitHub repos scraped successfully (public)
- ✅ Rate limits handled gracefully
- ✅ All export formats work with GitHub content
- ✅ UI remains intuitive for both source types
- ✅ CLI maintains backwards compatibility
- ✅ Performance: <5s for small repos (<100 files)
- ✅ Test coverage: >80% for new code

---

## 15. Open Questions

1. **Should we support GitHub Enterprise?**
   - Custom API base URLs?
   - SSO authentication?

2. **How to handle very large repositories?**
   - Prompt user to specify subdirectory?
   - Auto-limit to `/docs` folder?
   - Show warning at 1000+ files?

3. **Git history integration?**
   - Include commit messages?
   - Show file change history?
   - Link to blame view?

4. **Private repository access?**
   - OAuth flow in Streamlit?
   - SSH key support?
   - GitHub App integration?

5. **Monorepo support?**
   - How to handle multi-project repositories?
   - Separate export per project?
   - Custom path filtering?

---

## Appendix A: File Structure Changes

### New Files
```
src/scrape_api_docs/
├── url_detector.py          # URL type detection
├── scraper_factory.py       # Scraper factory pattern
├── github_scraper.py        # GitHub-specific scraper
├── github_client.py         # GitHub API client
├── github_rate_limiter.py   # GitHub rate limiting
└── github_auth.py           # Authentication handling

docs/
└── github-integration-plan.md  # This document

tests/
├── test_url_detector.py
├── test_scraper_factory.py
├── test_github_scraper.py
└── integration/
    └── test_github_integration.py
```

### Modified Files
```
src/scrape_api_docs/
├── __main__.py              # Add GitHub CLI args
├── streamlit_app.py         # Add GitHub UI options
├── config.py                # Add GitHub config section
├── exceptions.py            # Add GitHub exceptions
└── exporters/
    └── base.py              # Extend PageResult metadata
```

---

## Appendix B: Configuration Example

```yaml
# config/github.yaml

github:
  enabled: true
  api_base_url: https://api.github.com
  rate_limit_requests: 60
  rate_limit_authenticated: 5000
  timeout: 10
  max_file_size: 10485760  # 10MB

  supported_extensions:
    - .md
    - .markdown
    - .rst
    - .txt
    - .adoc
    - .py
    - .js
    - .ts

  exclude_paths:
    - node_modules/
    - vendor/
    - .git/
    - dist/
    - build/

  include_wiki: true
  include_issues: false
  include_discussions: false
  default_branch: main

  # Authentication (prefer env var)
  token: ${GITHUB_TOKEN}

# Use with:
# scrape-api-docs https://github.com/owner/repo --config config/github.yaml
```

---

## Appendix C: Example Usage

### Web Scraping (Unchanged)
```bash
# CLI
scrape-api-docs https://docs.python.org/3/ --max-pages 50

# Python
from scrape_api_docs.scraper_factory import ScraperFactory

scraper = ScraperFactory.create_scraper("https://docs.python.org/3/")
results = scraper.scrape("https://docs.python.org/3/", max_pages=50)
```

### GitHub Scraping (New)
```bash
# CLI - Public repo
scrape-api-docs https://github.com/psf/requests --include-wiki

# CLI - With token for private repo
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
scrape-api-docs https://github.com/myorg/private-repo \
    --github-token $GITHUB_TOKEN \
    --formats markdown pdf epub

# Python API
from scrape_api_docs.scraper_factory import ScraperFactory

scraper = ScraperFactory.create_scraper("https://github.com/psf/requests")
results = scraper.scrape(
    "https://github.com/psf/requests",
    include_wiki=True,
    github_token=os.getenv('GITHUB_TOKEN')
)
```

---

## Document Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-14 | Hive Mind Analyst | Initial integration plan |

---

**Next Steps:**
1. Review this plan with development team
2. Prioritize features and create sprints
3. Set up development environment
4. Begin Phase 1 implementation
5. Schedule code reviews and testing milestones
