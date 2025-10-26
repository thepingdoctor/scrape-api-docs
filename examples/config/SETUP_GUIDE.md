# Enhanced Documentation Scraper - Setup Guide
===============================================

This guide walks through setting up and configuring the enhanced documentation scraper with rate limiting, caching, and authentication features.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration](#configuration)
3. [Authentication Setup](#authentication-setup)
4. [Rate Limiting](#rate-limiting)
5. [Caching](#caching)
6. [Advanced Usage](#advanced-usage)
7. [Troubleshooting](#troubleshooting)

## Quick Start

### Installation

```bash
# Navigate to examples directory
cd examples

# Install dependencies
pip install -r integration/requirements.txt

# Verify installation
python -c "from integration.scraper_integration import EnhancedScraper; print('✓ Installation successful')"
```

### Basic Usage

```bash
# Scrape public documentation
python integration/scraper_integration.py https://example.com/docs

# With custom rate limit
python integration/scraper_integration.py https://example.com/docs --rate 1.0

# With custom output file
python integration/scraper_integration.py https://example.com/docs --output my_docs.md
```

## Configuration

### Using Configuration File

1. **Copy the example configuration**:
```bash
cp config/scraper_config.yaml config/my_config.yaml
```

2. **Edit configuration**:
```yaml
rate_limiting:
  default_rate: 2.0  # Adjust based on target site

caching:
  enabled: true
  cache_dir: .cache

authentication:
  enabled: false  # Set to true if needed
```

3. **Load configuration in code**:
```python
import yaml
from integration.scraper_integration import EnhancedScraper

# Load config
with open('config/my_config.yaml') as f:
    config = yaml.safe_load(f)

# Initialize scraper with config
scraper = EnhancedScraper(
    requests_per_second=config['rate_limiting']['default_rate'],
    cache_dir=config['caching']['cache_dir'],
    enable_auth=config['authentication']['enabled']
)
```

### Environment Variables

For sensitive configuration (recommended for production):

```bash
# Set environment variables
export SCRAPER_RATE_LIMIT=2.0
export SCRAPER_CACHE_DIR=.cache
export SCRAPER_ENABLE_AUTH=true

# Use in code
import os

scraper = EnhancedScraper(
    requests_per_second=float(os.getenv('SCRAPER_RATE_LIMIT', 2.0)),
    cache_dir=os.getenv('SCRAPER_CACHE_DIR', '.cache'),
    enable_auth=os.getenv('SCRAPER_ENABLE_AUTH', 'false').lower() == 'true'
)
```

## Authentication Setup

### Step 1: Create Credential File

```bash
# Copy example credential file
cp config/auth_credentials.example.json ~/.scraper_auth.json

# Secure the file (important!)
chmod 600 ~/.scraper_auth.json
```

### Step 2: Add Your Credentials

Edit `~/.scraper_auth.json`:

```json
{
  "api.example.com": {
    "auth_type": "bearer",
    "token": "your_actual_bearer_token"
  }
}
```

**IMPORTANT**: Never commit this file to version control!

Add to `.gitignore`:
```
.scraper_auth.json
**/auth_credentials*.json
```

### Step 3: Use Authentication

```python
from integration.scraper_integration import EnhancedScraper

# Enable authentication
scraper = EnhancedScraper(enable_auth=True)

# Scrape protected documentation
stats = scraper.scrape_site('https://api.example.com/docs')
```

### Authentication Types

#### 1. Bearer Token

```json
{
  "api.example.com": {
    "auth_type": "bearer",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

#### 2. Basic Authentication

```json
{
  "docs.example.com": {
    "auth_type": "basic",
    "username": "my_username",
    "password": "my_password"
  }
}
```

#### 3. API Key (Header)

```json
{
  "api.example.com": {
    "auth_type": "api_key",
    "api_key": "sk_live_abc123...",
    "key_name": "X-API-Key",
    "location": "header"
  }
}
```

#### 4. API Key (Query Parameter)

```json
{
  "api.example.com": {
    "auth_type": "api_key",
    "api_key": "abc123",
    "key_name": "api_key",
    "location": "query"
  }
}
```

#### 5. OAuth 2.0 Client Credentials

```json
{
  "oauth-api.example.com": {
    "auth_type": "oauth2",
    "token_url": "https://oauth-api.example.com/oauth/token",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "scope": "read:docs"
  }
}
```

**Note**: OAuth2 requires manual setup in code:

```python
from auth.auth_manager import AuthManager

auth = AuthManager()
auth.add_oauth2(
    'oauth-api.example.com',
    token_url='https://oauth-api.example.com/oauth/token',
    client_id='your_client_id',
    client_secret='your_client_secret',
    scope='read:docs'
)
```

#### 6. Cookie-based Session

```json
{
  "cookie-site.example.com": {
    "auth_type": "cookie",
    "cookies": {
      "session_id": "abc123xyz",
      "auth_token": "def456uvw"
    }
  }
}
```

#### 7. Custom Headers

```json
{
  "custom-api.example.com": {
    "auth_type": "custom_header",
    "headers": {
      "X-Custom-Auth": "custom_value",
      "X-API-Version": "v2",
      "X-Client-ID": "12345"
    }
  }
}
```

### Testing Authentication

```python
from auth.auth_manager import AuthManager

auth = AuthManager()

# List configured credentials
print("Configured credentials:")
for domain, auth_type in auth.list_credentials().items():
    print(f"  {domain}: {auth_type}")

# Test a specific credential
session = auth.get_authenticated_session('https://api.example.com/docs')
response = session.get('https://api.example.com/docs')
print(f"Test request: {response.status_code}")
```

## Rate Limiting

### Default Configuration

```python
from integration.scraper_integration import EnhancedScraper

# 2 requests per second (default)
scraper = EnhancedScraper(requests_per_second=2.0)
```

### Per-Domain Limits

```python
# Set different limits for different domains
scraper.rate_limiter.set_domain_limit('slow-api.com', 0.5)  # 0.5 req/s
scraper.rate_limiter.set_domain_limit('fast-api.com', 5.0)  # 5 req/s
```

### Monitoring Rate Limits

```python
# Check rate limiter statistics
stats = scraper.rate_limiter.get_stats()

for domain, domain_stats in stats.items():
    print(f"\n{domain}:")
    print(f"  Requests: {domain_stats['requests']}")
    print(f"  Throttled: {domain_stats['throttled']}")
    print(f"  Errors: {domain_stats['errors']}")
    print(f"  In backoff: {domain_stats['in_backoff']}")
```

### Best Practices

1. **Start Conservative**: Begin with 1-2 req/s, increase if needed
2. **Respect 429 Responses**: The rate limiter automatically backs off
3. **Monitor Backoff Events**: Check logs for backoff warnings
4. **Set Domain-Specific Limits**: Customize for each site's capacity

```python
# Example: Conservative scraping
scraper = EnhancedScraper(
    requests_per_second=1.0,  # Conservative default
    max_retries=5             # More retries for stability
)

# Increase rate for known fast sites
scraper.rate_limiter.set_domain_limit('internal-docs.company.com', 10.0)
```

## Caching

### Enable/Disable Caching

```python
from integration.scraper_integration import EnhancedScraper

# With caching (default)
scraper = EnhancedScraper(
    cache_dir='.cache',
    cache_ttl=3600  # 1 hour
)

# Disable caching
scraper = EnhancedScraper(
    cache_dir='/tmp/no_cache',  # Temporary cache
    cache_ttl=0                  # No TTL
)
```

### Cache Management

```python
# View cache statistics
stats = scraper.cache_manager.stats()

print("Memory Cache:")
print(f"  Size: {stats['memory']['size']}/{stats['memory']['max_size']}")
print(f"  Hit rate: {stats['memory']['hit_rate']:.1%}")

print("\nDisk Cache:")
print(f"  Entries: {stats['disk']['count']}")
print(f"  Size: {stats['disk']['total_size_bytes']/1024/1024:.1f} MB")
print(f"  Hit rate: {stats['disk']['hit_rate']:.1%}")

# Cleanup expired entries
removed = scraper.cleanup()
print(f"\nCleaned up {removed} expired entries")
```

### Cache Invalidation

```python
# Clear memory cache only
scraper.cache_manager.clear()

# Delete specific cached URL
scraper.cache_manager.delete('https://example.com/page1')

# Cleanup all expired entries
scraper.cleanup()
```

### Finding Duplicates

```python
# Find duplicate content
duplicates = scraper.cache_manager.find_duplicates()

print("Duplicate content detected:")
for content_hash, urls in duplicates.items():
    print(f"\nContent hash: {content_hash[:16]}...")
    for url in urls:
        print(f"  - {url}")
```

## Advanced Usage

### Custom Configuration Class

```python
from dataclasses import dataclass
from integration.scraper_integration import EnhancedScraper

@dataclass
class ScraperConfig:
    rate_limit: float = 2.0
    cache_dir: str = '.cache'
    cache_ttl: int = 3600
    enable_auth: bool = False
    timeout: int = 10

    def create_scraper(self) -> EnhancedScraper:
        return EnhancedScraper(
            requests_per_second=self.rate_limit,
            cache_dir=self.cache_dir,
            cache_ttl=self.cache_ttl,
            enable_auth=self.enable_auth,
            timeout=self.timeout
        )

# Use configuration
config = ScraperConfig(
    rate_limit=1.0,
    enable_auth=True
)
scraper = config.create_scraper()
```

### Batch Scraping

```python
from integration.scraper_integration import EnhancedScraper
import json

# Configuration for multiple sites
sites = [
    {
        'url': 'https://api1.example.com/docs',
        'rate': 1.0,
        'auth': True,
        'output': 'api1_docs.md'
    },
    {
        'url': 'https://docs.example.com',
        'rate': 2.0,
        'auth': False,
        'output': 'public_docs.md'
    }
]

# Scrape all sites
results = []
for site in sites:
    scraper = EnhancedScraper(
        requests_per_second=site['rate'],
        enable_auth=site['auth']
    )

    stats = scraper.scrape_site(site['url'], site['output'])
    results.append({
        'url': site['url'],
        'stats': stats
    })

# Save results
with open('batch_results.json', 'w') as f:
    json.dump(results, f, indent=2)
```

### Progress Callbacks

```python
from integration.scraper_integration import EnhancedScraper

class ProgressTracker:
    def __init__(self):
        self.current_page = 0
        self.total_pages = 0

    def on_page_discovered(self, url: str):
        self.total_pages += 1
        print(f"Discovered: {url} (total: {self.total_pages})")

    def on_page_processed(self, url: str):
        self.current_page += 1
        print(f"Processed [{self.current_page}/{self.total_pages}]: {url}")

# Extend scraper with callbacks
# (Would require minor modifications to scraper_integration.py)
```

## Troubleshooting

### Common Issues

#### 1. Rate Limit Errors (429)

**Symptoms**: Getting 429 Too Many Requests errors

**Solution**:
```python
# Reduce rate limit
scraper = EnhancedScraper(requests_per_second=0.5)

# Or increase retry attempts
scraper.rate_limiter.max_retries = 5
```

#### 2. Authentication Failures (401/403)

**Symptoms**: Getting 401 Unauthorized or 403 Forbidden errors

**Solution**:
```python
# Verify credentials
auth = AuthManager()
print(auth.list_credentials())

# Test authentication manually
session = auth.get_authenticated_session('https://api.example.com')
response = session.get('https://api.example.com/test')
print(f"Status: {response.status_code}")
print(f"Headers: {response.headers}")
```

#### 3. Stale Cache Data

**Symptoms**: Getting old/outdated content

**Solution**:
```python
# Reduce TTL
scraper = EnhancedScraper(cache_ttl=600)  # 10 minutes

# Or clear cache
scraper.cache_manager.clear()

# Or disable caching for this run
scraper = EnhancedScraper(cache_ttl=0)
```

#### 4. Slow Performance

**Symptoms**: Scraping takes too long

**Solution**:
```python
# Check if rate limiting is too strict
scraper.rate_limiter.set_domain_limit('fast-site.com', 5.0)

# Enable caching if not already
scraper = EnhancedScraper(cache_ttl=3600)

# Check cache hit rate
stats = scraper.cache_manager.stats()
print(f"Cache hit rate: {stats['memory']['hit_rate']:.1%}")
```

#### 5. Memory Issues

**Symptoms**: High memory usage or OOM errors

**Solution**:
```python
# Reduce memory cache size
scraper = EnhancedScraper(max_memory_cache=50)

# Or disable memory cache (disk only)
scraper = EnhancedScraper(max_memory_cache=0)

# Cleanup periodically
scraper.cleanup()
```

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now run scraper with verbose output
scraper = EnhancedScraper()
stats = scraper.scrape_site('https://example.com/docs')
```

### Getting Help

1. **Check logs**: Review scraper.log for detailed error messages
2. **Test components individually**: Test rate limiter, cache, and auth separately
3. **Verify configuration**: Print configuration values before running
4. **Monitor statistics**: Check stats() output for anomalies

## Next Steps

- Review the [main examples README](../README.md) for usage examples
- Check the inline documentation in each module
- Experiment with the configuration options
- Integrate features into your existing scraper

## Security Checklist

- [ ] Credentials file has restricted permissions (chmod 600)
- [ ] Credential file is in .gitignore
- [ ] Using environment variables for CI/CD
- [ ] Not committing auth_credentials.json to version control
- [ ] Regularly rotating API keys/tokens
- [ ] Using HTTPS for all requests
