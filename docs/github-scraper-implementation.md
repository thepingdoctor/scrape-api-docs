# GitHub Repository Scraper Implementation

## Overview

The GitHub Repository Scraper module provides functionality to download and consolidate documentation from public GitHub repositories using the GitHub REST API. This module integrates seamlessly with the existing scraper architecture while adding specialized support for GitHub repositories.

## Features

### Core Functionality

✅ **URL Detection and Parsing**
- Detects various GitHub URL formats (HTTPS, SSH)
- Parses owner, repository, branch, and path components
- Supports single files and directory trees
- Handles blob (file) and tree (directory) URLs

✅ **GitHub API Integration**
- Uses GitHub REST API v3 (no authentication required for public repos)
- Fetches repository tree structure recursively
- Downloads raw file content via Contents API
- Handles rate limiting (60 requests/hour unauthenticated)

✅ **Content Processing**
- Filters for documentation file types (.md, .rst, .txt, .adoc, .textile, .org, .rdoc)
- Preserves directory structure in output
- Converts relative markdown links to absolute GitHub URLs
- Consolidates multiple files into single markdown output

✅ **Integration**
- Uses existing `Config` system for settings
- Integrates with `logging_config` for structured logging
- Leverages `security` module for filename sanitization
- Compatible with existing exception hierarchy
- Follows same patterns as `scrape_site()` function

## Architecture

### Module Structure

```
src/scrape_api_docs/github_scraper.py
├── URL Detection & Parsing
│   ├── is_github_url()
│   └── parse_github_url()
├── GitHub API Integration
│   ├── get_repo_tree()
│   └── get_file_content()
├── Content Processing
│   └── convert_relative_links()
└── Main Function
    └── scrape_github_repo()
```

### Key Components

#### 1. URL Detection
```python
def is_github_url(url: str) -> bool:
    """Check if URL is a GitHub repository URL"""
```

Supports:
- `https://github.com/owner/repo`
- `https://github.com/owner/repo/tree/branch/path`
- `https://github.com/owner/repo/blob/branch/file.md`
- `git@github.com:owner/repo.git`

#### 2. URL Parsing
```python
def parse_github_url(url: str) -> Dict[str, str]:
    """Parse GitHub URL into components"""
    # Returns: {owner, repo, branch, path, is_file}
```

#### 3. Repository Tree
```python
def get_repo_tree(owner, repo, branch, path, config, session):
    """Get repository directory tree using GitHub API"""
```

Uses:
- `/repos/{owner}/{repo}/git/refs/heads/{branch}` - Get branch SHA
- `/repos/{owner}/{repo}/git/trees/{sha}?recursive=1` - Get tree recursively

#### 4. File Content
```python
def get_file_content(owner, repo, branch, filepath, config, session):
    """Get raw file content from GitHub"""
```

Uses:
- `/repos/{owner}/{repo}/contents/{filepath}?ref={branch}` - Get file content (base64 encoded)

#### 5. Link Conversion
```python
def convert_relative_links(content, owner, repo, branch, current_file_path):
    """Convert relative links to absolute GitHub URLs"""
```

Converts:
- `[Link](./other.md)` → `[Link](https://github.com/owner/repo/blob/branch/other.md)`
- `[Link](../parent/file.md)` → Resolves path correctly
- Preserves absolute URLs and anchors

## Usage

### Basic Usage

```python
from scrape_api_docs import scrape_github_repo

# Scrape entire repository
output = scrape_github_repo(
    'https://github.com/owner/repo',
    output_dir='./docs',
    max_files=100
)
```

### Scrape Specific Directory

```python
# Scrape only the docs folder
output = scrape_github_repo(
    'https://github.com/python/cpython/tree/main/Doc',
    output_dir='./output',
    max_files=50
)
```

### Scrape Single File

```python
# Scrape a specific markdown file
output = scrape_github_repo(
    'https://github.com/owner/repo/blob/main/README.md',
    output_dir='./output'
)
```

### With Custom Configuration

```python
from scrape_api_docs import scrape_github_repo, Config

config = Config.load()
config.set('scraper.timeout', 15)
config.set('scraper.user_agent', 'MyBot/1.0')

output = scrape_github_repo(
    'https://github.com/owner/repo',
    config=config,
    max_files=100
)
```

## API Reference

### Main Function

#### `scrape_github_repo(url, output_dir='.', max_files=100, config=None)`

Main function to scrape GitHub repository documentation.

**Parameters:**
- `url` (str): GitHub repository URL
- `output_dir` (str): Output directory for documentation file (default: '.')
- `max_files` (int): Maximum number of files to process (default: 100)
- `config` (Config): Configuration instance (optional)

**Returns:**
- `str`: Path to the output markdown file

**Raises:**
- `ValidationException`: If URL is invalid or repository not found
- `NetworkException`: If API requests fail
- `RateLimitException`: If rate limit exceeded

**Example:**
```python
output = scrape_github_repo(
    'https://github.com/psf/requests/tree/main/docs',
    output_dir='./output',
    max_files=50
)
print(f"Documentation saved to: {output}")
```

### Utility Functions

#### `is_github_url(url)`

Check if URL is a GitHub repository URL.

**Returns:** `bool`

#### `parse_github_url(url)`

Parse GitHub URL into components.

**Returns:** `Dict[str, str]` with keys: `owner`, `repo`, `branch`, `path`, `is_file`

#### `get_repo_tree(owner, repo, branch, path, config, session)`

Get repository directory tree using GitHub API.

**Returns:** `List[Dict]` - List of file/directory objects

#### `get_file_content(owner, repo, branch, filepath, config, session)`

Get raw file content from GitHub.

**Returns:** `str` - File content

## Output Format

The scraper produces a consolidated Markdown file with the following structure:

```markdown
# Documentation for owner/repo/path

**Source:** https://github.com/owner/repo/tree/branch/path
**Branch:** branch
**Scraped:** 2025-11-14 22:30:00 UTC

## filename.md

**Path:** `path/to/filename.md`
**URL:** https://github.com/owner/repo/blob/branch/path/to/filename.md

[File content with converted links]

---

## another-file.md

...
```

### Filename Generation

Output filenames follow the pattern:
```
{owner}_{repo}_{branch}_{path}_documentation.md
```

Examples:
- `python_cpython_main_documentation.md`
- `psf_requests_main_docs_documentation.md`
- `owner_repo_main_path_to_docs_documentation.md`

## Rate Limiting

### GitHub API Limits

**Unauthenticated:**
- 60 requests per hour per IP address
- Shared across all API endpoints

**Best Practices:**
- Monitor `X-RateLimit-Remaining` header
- Implement 0.5s delay between requests (built-in)
- Handle `RateLimitException` gracefully
- Consider authenticated requests for higher limits (future enhancement)

### Rate Limit Handling

The scraper automatically:
1. Checks rate limit headers on each response
2. Throws `RateLimitException` when limit exceeded
3. Includes retry-after time in exception
4. Logs remaining requests for monitoring

Example:
```python
try:
    output = scrape_github_repo(url)
except RateLimitException as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
    # Wait and retry or handle gracefully
```

## Supported File Types

The scraper filters for documentation file extensions:

| Extension | Format |
|-----------|--------|
| `.md`, `.markdown` | Markdown |
| `.rst` | reStructuredText |
| `.txt` | Plain text |
| `.adoc`, `.asciidoc` | AsciiDoc |
| `.textile` | Textile |
| `.org` | Org-mode |
| `.rdoc` | RDoc |

## Error Handling

### Exception Types

1. **ValidationException**
   - Invalid GitHub URL
   - Repository not found
   - Branch doesn't exist

2. **NetworkException**
   - API request failures
   - Network timeouts
   - Connection errors

3. **RateLimitException**
   - Rate limit exceeded
   - Includes retry-after time

4. **ContentParsingException**
   - Base64 decoding errors
   - Content processing failures

### Example Error Handling

```python
from scrape_api_docs import scrape_github_repo
from scrape_api_docs.exceptions import (
    ValidationException,
    NetworkException,
    RateLimitException
)

try:
    output = scrape_github_repo(url)
except ValidationException as e:
    print(f"Invalid URL or repository: {e}")
except NetworkException as e:
    print(f"Network error: {e}")
except RateLimitException as e:
    print(f"Rate limited. Retry in {e.retry_after}s")
```

## Integration with Existing System

### Configuration

Uses existing `Config` system with standard settings:

```python
config = Config.load()
config.get('scraper.timeout', 10)           # Request timeout
config.get('scraper.user_agent', '...')     # User agent string
config.get('security.sanitize_filenames')   # Filename sanitization
config.get('output.encoding', 'utf-8')      # Output encoding
```

### Logging

Integrates with `logging_config`:

```python
from scrape_api_docs.logging_config import setup_logging

setup_logging(level='INFO')
# GitHub scraper will use configured logging
```

Log messages include:
- URL parsing results
- API request details
- Rate limit status
- Files processed/failed
- Performance metrics

### Security

Uses `SecurityValidator` for:
- Filename sanitization (prevents path traversal)
- Safe file writing

## Performance Considerations

### Optimization Strategies

1. **Session Reuse**
   - Single `requests.Session` for all API calls
   - Connection pooling and keep-alive

2. **Politeness Delay**
   - 0.5s delay between file fetches
   - Respects GitHub API guidelines

3. **Efficient API Usage**
   - Recursive tree fetch (single API call)
   - Content API for file fetching

4. **Filtering**
   - Early filtering of non-documentation files
   - Reduces unnecessary API calls

### Benchmarks

Typical performance (unauthenticated):
- Tree fetch: ~1 second
- File fetch: ~1 second per file + 0.5s delay
- 10 files: ~15 seconds
- 50 files: ~75 seconds
- Rate limit: 60 files/hour maximum

## Future Enhancements

### Planned Features

1. **Authentication Support**
   - GitHub token support
   - 5000 requests/hour limit
   - Access to private repositories

2. **Caching**
   - Local cache of tree structures
   - ETag support for conditional requests
   - Reduced API usage

3. **Parallel Fetching**
   - Async/concurrent file downloads
   - Respect rate limits across workers
   - Improved performance

4. **Advanced Filtering**
   - Custom file patterns
   - Directory exclusions
   - Size-based filtering

5. **GraphQL API**
   - More efficient queries
   - Reduced API calls
   - Better rate limit usage

## Testing

### Unit Tests

```python
# Test URL detection
assert is_github_url('https://github.com/owner/repo')
assert not is_github_url('https://example.com')

# Test URL parsing
parsed = parse_github_url('https://github.com/owner/repo/tree/main/docs')
assert parsed['owner'] == 'owner'
assert parsed['repo'] == 'repo'
assert parsed['branch'] == 'main'
assert parsed['path'] == 'docs'
```

### Integration Tests

```python
# Test actual scraping (requires network)
output = scrape_github_repo(
    'https://github.com/psf/requests',
    max_files=5
)
assert Path(output).exists()
```

## Examples

See `/home/ruhroh/scrape-api-docs/examples/github_scraper_example.py` for comprehensive usage examples including:
- Basic repository scraping
- Directory-specific scraping
- Single file scraping
- URL parsing demonstrations
- Custom configuration
- Error handling
- Rate limit handling

## Implementation Notes

### Design Decisions

1. **REST API over Git Clone**
   - No local git installation required
   - Selective file downloading
   - Better rate limiting control
   - Smaller download footprint

2. **Single File Output**
   - Maintains consistency with `scrape_site()`
   - Easy to process and distribute
   - Preserves file organization in headers

3. **Relative Link Conversion**
   - Maintains link functionality
   - Points to canonical GitHub URLs
   - Works without local repository

4. **Default Branch Detection**
   - Tries 'main' first (modern default)
   - Falls back to 'master' if not found
   - User can specify branch in URL

### Code Quality

- Comprehensive docstrings for all functions
- Type hints for better IDE support
- Consistent error handling
- Integration with existing architecture
- Follows project coding standards

## Coordination

This implementation was developed as part of the Hive Mind swarm coordination:

**Task ID:** `github-scraper-implementation`
**Session:** `swarm-1763159183466-ozce54lgp`
**Agent:** Coder
**Memory Key:** `swarm/coder/github-scraper-progress`

Progress saved to `.swarm/memory.db` for coordination with other agents.

## Summary

The GitHub scraper module successfully extends the scrape-api-docs project with specialized GitHub repository support while maintaining architectural consistency. It provides robust error handling, rate limit awareness, and comprehensive documentation processing capabilities.

**Key Achievements:**
- ✅ Full GitHub API integration
- ✅ Multiple URL format support
- ✅ Documentation filtering and processing
- ✅ Link conversion for portability
- ✅ Rate limiting awareness
- ✅ Comprehensive error handling
- ✅ Integration with existing systems
- ✅ Example code and documentation
