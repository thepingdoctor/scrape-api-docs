# GitHub Repository Scraping Guide

## Overview

The scrape-api-docs tool now supports scraping documentation directly from GitHub repositories! This powerful feature allows you to extract documentation from public (and private with auth) GitHub repos without needing to clone them locally.

## Features

✅ **URL Auto-Detection**: Automatically detects GitHub repository URLs
✅ **Multiple URL Formats**: Supports various GitHub URL formats (HTTPS, SSH, tree, blob)
✅ **Folder-Specific Scraping**: Scrape specific directories or entire repositories
✅ **Documentation Filtering**: Automatically filters for documentation files (.md, .rst, .txt, .adoc)
✅ **Rate Limiting**: Handles GitHub API rate limits (60/hr unauthenticated, 5,000/hr with token)
✅ **Link Conversion**: Converts relative links to absolute GitHub URLs
✅ **Multiple Export Formats**: Export to Markdown, PDF, EPUB, HTML, or JSON

## Quick Start

### Example: BMAD-METHOD Documentation

To scrape the documentation from the BMAD-METHOD repository:

```bash
# Using the Streamlit UI
streamlit run src/scrape_api_docs/streamlit_app.py
# Enter: https://github.com/bmad-code-org/BMAD-METHOD/tree/main/src/modules/bmm/docs

# Using the CLI (coming soon)
scrape-docs --url https://github.com/bmad-code-org/BMAD-METHOD/tree/main/src/modules/bmm/docs
```

## Supported URL Formats

The GitHub scraper recognizes these URL patterns:

```
# Full repository
https://github.com/owner/repo

# Specific branch
https://github.com/owner/repo/tree/branch-name

# Specific directory
https://github.com/owner/repo/tree/main/docs

# Specific file
https://github.com/owner/repo/blob/main/README.md

# SSH URLs
git@github.com:owner/repo.git
```

## Using the Streamlit UI

1. **Launch the UI**:
   ```bash
   streamlit run src/scrape_api_docs/streamlit_app.py
   ```

2. **Enter a GitHub URL**:
   - The UI will auto-detect it's a GitHub repository
   - View repository metadata (owner, repo, branch, path)

3. **Configure GitHub Options** (optional):
   - **Personal Access Token**: Increase rate limit from 60 to 5,000 requests/hour
   - **Max Files**: Limit files to prevent rate limiting on large repos (default: 100)
   - **Include Metadata**: Add commit info, authors, and modification dates

4. **Select Export Formats**:
   - Choose from Markdown, PDF, EPUB, HTML, or JSON
   - Multiple formats can be selected

5. **Start Scraping**:
   - Click "🚀 Start Scraping"
   - Monitor progress in real-time
   - Download files when complete

## Authentication (Optional but Recommended)

### Why Use a Token?

Without authentication:
- **60 requests/hour** rate limit
- Public repositories only

With a Personal Access Token (PAT):
- **5,000 requests/hour** rate limit
- Access to private repositories (if granted)
- Fewer rate limit issues on large repos

### Creating a GitHub Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name (e.g., "scrape-api-docs")
4. Select scopes:
   - For public repos: `public_repo`
   - For private repos: `repo`
5. Click "Generate token"
6. Copy the token (you won't see it again!)

### Using the Token

**In Streamlit UI**:
- Paste token in "GitHub Personal Access Token" field
- Token is used for that session only (not saved)

**Via Environment Variable** (future):
```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
```

## Examples

### Scrape Entire Repository
```
https://github.com/bmad-code-org/BMAD-METHOD
```
Scrapes all documentation files from the main branch.

### Scrape Specific Documentation Folder
```
https://github.com/bmad-code-org/BMAD-METHOD/tree/main/src/modules/bmm/docs
```
Scrapes only files in the `/src/modules/bmm/docs` directory.

### Scrape from a Specific Branch
```
https://github.com/owner/repo/tree/develop/docs
```
Scrapes documentation from the `develop` branch.

### Scrape a Single File
```
https://github.com/owner/repo/blob/main/README.md
```
Scrapes just the README.md file.

## Output Format

### Markdown Structure

The generated markdown file follows this structure:

```markdown
# Documentation for owner/repo

**Source:** https://github.com/owner/repo/tree/main/docs
**Scraped:** 2025-01-14 22:00:00 UTC

---

## docs/README.md

**File Path:** `/docs/README.md`
**Repository:** owner/repo
**Branch:** main

[Content from README.md]

---

## docs/getting-started.md

**File Path:** `/docs/getting-started.md`
**Repository:** owner/repo
**Branch:** main

[Content from getting-started.md]

---
```

### Relative Link Conversion

The scraper automatically converts relative links to absolute GitHub URLs:

**Original** (in README.md):
```markdown
See [Configuration Guide](./config/guide.md)
```

**Converted**:
```markdown
See [Configuration Guide](https://github.com/owner/repo/blob/main/docs/config/guide.md)
```

## Rate Limiting

### Understanding GitHub Rate Limits

GitHub enforces these rate limits:

| Authentication | Requests/Hour | Best For |
|----------------|---------------|----------|
| None | 60 | Small repos (<50 files) |
| Personal Access Token | 5,000 | Large repos, frequent use |

### Rate Limit Headers

The scraper monitors these headers:
- `X-RateLimit-Limit`: Total requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: When limit resets (Unix timestamp)

### Handling Rate Limits

If you hit the rate limit:
1. **Wait**: The limit resets every hour
2. **Use a Token**: Increases limit to 5,000/hr
3. **Limit Files**: Use `max_files` parameter to scrape fewer files
4. **Be Selective**: Scrape specific folders instead of entire repos

## Supported File Types

The scraper automatically identifies and processes these documentation file types:

- **.md** - Markdown
- **.markdown** - Markdown
- **.rst** - reStructuredText
- **.txt** - Plain text
- **.adoc** - AsciiDoc
- **.textile** - Textile
- **.org** - Org-mode
- **.creole** - Creole
- **.mediawiki** - MediaWiki

Binary files and code files are automatically excluded.

## Troubleshooting

### "GitHub scraping failed: 404"
- **Cause**: Repository doesn't exist or is private
- **Solution**: Check URL spelling or provide authentication token for private repos

### "Rate limit exceeded"
- **Cause**: Hit the 60 requests/hour limit
- **Solution**: Wait an hour or use a Personal Access Token

### "No documentation files found"
- **Cause**: The repository/folder has no .md, .rst, or .txt files
- **Solution**: Check the repository structure or try a different path

### "Invalid GitHub URL format"
- **Cause**: URL doesn't match expected GitHub patterns
- **Solution**: Verify URL follows one of the supported formats above

## Performance Tips

1. **Use Specific Paths**: Scrape `/docs` folder instead of entire repo
2. **Set Max Files**: Limit to 50-100 files for large repositories
3. **Use Authentication**: Avoid rate limit issues with a PAT
4. **Choose Selective Exports**: Only generate formats you need

## Advanced Usage

### Python API

```python
from scrape_api_docs.github_scraper import scrape_github_repo

# Scrape a GitHub repository
output_path = scrape_github_repo(
    url='https://github.com/owner/repo/tree/main/docs',
    output_dir='output',
    max_files=100
)

print(f"Documentation saved to: {output_path}")
```

### With Configuration

```python
from scrape_api_docs.github_scraper import scrape_github_repo
from scrape_api_docs.config import Config

# Create custom config
config = Config.load()
config.set('github.token', 'ghp_xxxxxxxxxxxx')
config.set('github.max_files', 200)

# Scrape with config
output_path = scrape_github_repo(
    url='https://github.com/owner/repo',
    config=config
)
```

## Comparison: GitHub vs Web Scraping

| Feature | GitHub Scraping | Web Scraping |
|---------|----------------|--------------|
| **Speed** | Fast (API-based) | Slower (page rendering) |
| **Rate Limits** | 60-5,000/hr | Varies by site |
| **Auth Required** | Optional | Varies |
| **Robots.txt** | N/A | Required |
| **Private Content** | Yes (with token) | Varies |
| **Link Conversion** | Automatic | N/A |

## Future Enhancements

Planned features for future releases:

- [ ] GitHub wiki scraping
- [ ] GitHub issues as documentation
- [ ] GitHub discussions scraping
- [ ] Multi-repository scraping
- [ ] Commit history inclusion
- [ ] Author attribution
- [ ] CLI support for GitHub URLs

## Support

For issues or questions about GitHub scraping:

- **GitHub Issues**: https://github.com/thepingdoctor/scrape-api-docs/issues
- **Documentation**: https://github.com/thepingdoctor/scrape-api-docs
- **Examples**: See `/examples/github_scraper_example.py`

---

**Generated with ❤️ by the Hive Mind Collective Intelligence System**
