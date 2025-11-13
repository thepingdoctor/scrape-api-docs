# User Agent Selection Guide

This guide explains how to use the user agent selection feature in the scrape-api-docs project.

## Overview

The user agent selection feature allows you to specify which browser/device the scraper should identify as when making HTTP requests. Different websites may serve different content based on the user agent, making this feature useful for:

- **Mobile scraping**: Get mobile versions of sites
- **Compatibility testing**: Test how sites respond to different browsers
- **Bypassing restrictions**: Some sites block generic scrapers but allow known browsers
- **Bot identification**: Use search engine bot user agents for specific use cases

## Available User Agents

### Desktop Browsers

- **Chrome (Windows)** - Latest Chrome on Windows 10/11 (Default)
- **Chrome (macOS)** - Latest Chrome on macOS
- **Chrome (Linux)** - Latest Chrome on Linux
- **Firefox (Windows)** - Latest Firefox on Windows 10/11
- **Firefox (macOS)** - Latest Firefox on macOS
- **Firefox (Linux)** - Latest Firefox on Linux
- **Safari (macOS)** - Latest Safari on macOS
- **Edge (Windows)** - Latest Edge on Windows 10/11
- **Edge (macOS)** - Latest Edge on macOS

### Mobile Browsers

- **Chrome Mobile (Android)** - Chrome on Android smartphone
- **Chrome (Android Tablet)** - Chrome on Android tablet
- **Safari (iPhone)** - Safari on iPhone
- **Safari (iPad)** - Safari on iPad
- **Firefox Mobile (Android)** - Firefox on Android

### Search Engine Bots

- **Googlebot** - Google search crawler (desktop)
- **Googlebot Smartphone** - Google search crawler (mobile)
- **Bingbot** - Bing search crawler
- **DuckDuckBot** - DuckDuckGo search crawler

### Other

- **scrape-api-docs (Default)** - Project default identifier
- **Internet Explorer 11** - Legacy IE11 (for testing)
- **Custom** - Provide your own user agent string

## Usage

### Streamlit UI

1. Open the **Advanced Settings** section
2. Find the **User Agent** dropdown under the 🌐 heading
3. Select your desired user agent from the list
4. For custom user agents, select "Custom..." and enter your string

### API

When making API requests, include the `user_agent` field in the `options` object:

```json
{
  "url": "https://docs.example.com",
  "options": {
    "user_agent": "chrome_windows"
  }
}
```

You can use either:
- **Predefined identifiers**: `"chrome_windows"`, `"safari_iphone"`, `"googlebot"`, etc.
- **Custom strings**: Any valid user agent string

Example with custom user agent:

```json
{
  "url": "https://docs.example.com",
  "options": {
    "user_agent": "Mozilla/5.0 (custom) My Scraper/1.0"
  }
}
```

### Python Code

When using the scraper directly in Python:

```python
from scrape_api_docs.scraper import scrape_site

# Using predefined identifier
result = scrape_site(
    base_url="https://docs.example.com",
    user_agent="chrome_windows"
)

# Using custom user agent string
result = scrape_site(
    base_url="https://docs.example.com",
    user_agent="Mozilla/5.0 (custom) My Scraper/1.0"
)
```

### Configuration File

Set a default user agent in your `config.yaml`:

```yaml
scraper:
  user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
```

### Environment Variable

Override the user agent via environment variable:

```bash
export SCRAPER_USER_AGENT="chrome_mac"
```

## Predefined Identifiers

Here's the complete list of predefined identifiers you can use:

| Identifier | Category | Description |
|-----------|----------|-------------|
| `chrome_windows` | Desktop | Chrome on Windows |
| `chrome_mac` | Desktop | Chrome on macOS |
| `chrome_linux` | Desktop | Chrome on Linux |
| `firefox_windows` | Desktop | Firefox on Windows |
| `firefox_mac` | Desktop | Firefox on macOS |
| `firefox_linux` | Desktop | Firefox on Linux |
| `safari_mac` | Desktop | Safari on macOS |
| `edge_windows` | Desktop | Edge on Windows |
| `edge_mac` | Desktop | Edge on macOS |
| `chrome_android` | Mobile | Chrome on Android phone |
| `chrome_android_tablet` | Mobile | Chrome on Android tablet |
| `safari_iphone` | Mobile | Safari on iPhone |
| `safari_ipad` | Mobile | Safari on iPad |
| `firefox_android` | Mobile | Firefox on Android |
| `googlebot` | Bot | Google crawler (desktop) |
| `googlebot_smartphone` | Bot | Google crawler (mobile) |
| `bingbot` | Bot | Bing crawler |
| `duckduckbot` | Bot | DuckDuckGo crawler |
| `scraper_default` | Default | Project default |
| `ie11_windows` | Legacy | Internet Explorer 11 |

## Best Practices

1. **Use realistic user agents**: Stick to well-known browser user agents
2. **Match your target**: Use mobile user agents for mobile sites
3. **Respect robots.txt**: Even with different user agents, respect site policies
4. **Test compatibility**: Try different user agents if you're getting unexpected results
5. **Be transparent**: Consider using a custom user agent that identifies your scraper

## Security Considerations

User agent strings are validated to prevent:
- Newline injection attacks
- Null byte injection
- Excessively long strings (>2000 characters)
- Excessively short strings (<3 characters)

## Examples

### Scraping a Mobile Site

```python
from scrape_api_docs.scraper import scrape_site

# Get mobile version of documentation
result = scrape_site(
    base_url="https://docs.example.com",
    user_agent="safari_iphone",
    max_pages=50
)
```

### Testing Different Browsers

```python
browsers = ["chrome_windows", "firefox_mac", "safari_mac"]

for browser in browsers:
    result = scrape_site(
        base_url="https://docs.example.com",
        user_agent=browser
    )
    print(f"Scraped with {browser}: {result}")
```

### Custom Bot Identification

```python
result = scrape_site(
    base_url="https://docs.example.com",
    user_agent="MyDocBot/1.0 (+https://mysite.com/bot)"
)
```

## Troubleshooting

### Site Blocking Requests

If a site is blocking your requests, try:
1. Using a standard browser user agent
2. Adding delays between requests (rate limiting)
3. Checking if the site allows your IP/user agent in robots.txt

### Getting Different Content

If you're getting unexpected content:
1. Try different user agents (mobile vs desktop)
2. Check if the site uses JavaScript (enable JS rendering)
3. Verify the URL is correct for your target content

## API Reference

### UserAgents Class

```python
from scrape_api_docs.user_agents import UserAgents

# Get all available user agents
all_agents = UserAgents.get_all()

# Get user agents by category
desktop_agents = UserAgents.get_by_category(UserAgentCategory.DESKTOP_BROWSER)

# Get specific user agent string
chrome_ua = UserAgents.get_user_agent_string('chrome_windows')

# List all identifiers
identifiers = UserAgents.list_identifiers()
```

### get_user_agent Function

```python
from scrape_api_docs.user_agents import get_user_agent

# Get by identifier
ua = get_user_agent('chrome_windows')

# Use custom string (overrides identifier)
ua = get_user_agent('chrome_windows', custom='My Custom UA')
```

### validate_user_agent Function

```python
from scrape_api_docs.user_agents import validate_user_agent

is_valid = validate_user_agent("Mozilla/5.0...")  # Returns True/False
```

## Further Reading

- [User Agent Strings Reference](https://www.useragentstring.com/)
- [MDN Web Docs: User-Agent](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent)
- [RFC 7231: User-Agent Header](https://tools.ietf.org/html/rfc7231#section-5.5.3)
