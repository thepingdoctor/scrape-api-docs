"""
Shared fixtures for Stoplight.io scraping tests.

This module provides reusable test fixtures, mock data, and helper
functions specific to Stoplight.io documentation sites.
"""

import pytest
from typing import Dict, List
import json


# ============================================================================
# Real Stoplight.io Site URLs (for E2E testing)
# ============================================================================

STOPLIGHT_TEST_SITES = [
    "https://mycaseapi.stoplight.io/docs/mycase-api-documentation",
    # Add more discovered Stoplight.io sites here
]


# ============================================================================
# Mock HTML Structures
# ============================================================================

@pytest.fixture
def stoplight_homepage():
    """Complete Stoplight.io homepage with all typical elements."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>MyCase API Documentation - Home</title>
        <meta name="description" content="Official MyCase API documentation">
        <link rel="stylesheet" href="https://unpkg.com/@stoplight/elements/styles.min.css">
    </head>
    <body>
        <div id="root">
            <div class="sl-elements-api-docs">
                <!-- Sidebar Navigation -->
                <nav class="sl-elements-api-docs-nav">
                    <div class="sl-stack">
                        <div class="sl-stack-item">
                            <a href="/docs/mycase-api-documentation">Home</a>
                        </div>
                        <div class="sl-stack-item">
                            <a href="/docs/mycase-api-documentation/introduction">Introduction</a>
                        </div>
                        <div class="sl-stack-item">
                            <a href="/docs/mycase-api-documentation/authentication">Authentication</a>
                        </div>
                        <div class="sl-stack-group">
                            <div class="sl-stack-group-header">API Reference</div>
                            <a href="/docs/mycase-api-documentation/api/users">Users</a>
                            <a href="/docs/mycase-api-documentation/api/cases">Cases</a>
                            <a href="/docs/mycase-api-documentation/api/contacts">Contacts</a>
                        </div>
                        <div class="sl-stack-group">
                            <div class="sl-stack-group-header">Guides</div>
                            <a href="/docs/mycase-api-documentation/guides/getting-started">Getting Started</a>
                            <a href="/docs/mycase-api-documentation/guides/webhooks">Webhooks</a>
                        </div>
                    </div>
                </nav>

                <!-- Main Content -->
                <main class="sl-elements-article">
                    <h1>MyCase API Documentation</h1>
                    <p class="sl-text-lg">
                        Welcome to the MyCase API documentation. This API allows you to
                        integrate your applications with MyCase practice management software.
                    </p>

                    <div class="sl-callout sl-callout-info">
                        <strong>Getting Started:</strong> New to the MyCase API? Start with our
                        <a href="/docs/mycase-api-documentation/guides/getting-started">Getting Started Guide</a>.
                    </div>

                    <h2>Quick Links</h2>
                    <ul>
                        <li><a href="/docs/mycase-api-documentation/authentication">Authentication Guide</a></li>
                        <li><a href="/docs/mycase-api-documentation/api-reference">API Reference</a></li>
                        <li><a href="/docs/mycase-api-documentation/guides/webhooks">Webhooks</a></li>
                    </ul>
                </main>
            </div>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def stoplight_api_endpoint_full():
    """Detailed API endpoint documentation with all components."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>GET /api/v1/users - MyCase API</title></head>
    <body>
        <main class="sl-elements-article">
            <div class="sl-http-operation">
                <!-- Method and Path -->
                <div class="sl-http-operation-header">
                    <span class="sl-http-method sl-http-method-get">GET</span>
                    <span class="sl-http-path">/api/v1/users</span>
                </div>

                <!-- Description -->
                <div class="sl-http-operation-description">
                    <h2>Retrieve Users</h2>
                    <p>Returns a paginated list of users in your organization.</p>
                </div>

                <!-- Parameters -->
                <div class="sl-http-operation-parameters">
                    <h3>Query Parameters</h3>
                    <table class="sl-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Type</th>
                                <th>Required</th>
                                <th>Description</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><code>limit</code></td>
                                <td>integer</td>
                                <td>No</td>
                                <td>Maximum number of users to return (default: 25, max: 100)</td>
                            </tr>
                            <tr>
                                <td><code>offset</code></td>
                                <td>integer</td>
                                <td>No</td>
                                <td>Number of users to skip (for pagination)</td>
                            </tr>
                            <tr>
                                <td><code>status</code></td>
                                <td>string</td>
                                <td>No</td>
                                <td>Filter by status: active, inactive, pending</td>
                            </tr>
                        </tbody>
                    </table>

                    <h3>Headers</h3>
                    <table class="sl-table">
                        <tbody>
                            <tr>
                                <td><code>Authorization</code></td>
                                <td>string</td>
                                <td>Yes</td>
                                <td>Bearer token for authentication</td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <!-- Responses -->
                <div class="sl-http-operation-responses">
                    <h3>Responses</h3>

                    <div class="sl-http-response">
                        <h4>200 - Success</h4>
                        <div class="sl-code-block">
                            <pre><code class="language-json">{
  "data": [
    {
      "id": 12345,
      "email": "john.doe@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "status": "active",
      "role": "attorney",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "meta": {
    "total": 150,
    "limit": 25,
    "offset": 0
  }
}</code></pre>
                        </div>
                    </div>

                    <div class="sl-http-response">
                        <h4>401 - Unauthorized</h4>
                        <p>Invalid or missing authentication token</p>
                    </div>

                    <div class="sl-http-response">
                        <h4>429 - Too Many Requests</h4>
                        <p>Rate limit exceeded. Please retry after the specified time.</p>
                    </div>
                </div>

                <!-- Code Examples -->
                <div class="sl-http-operation-examples">
                    <h3>Code Examples</h3>

                    <div class="sl-code-example">
                        <h4>cURL</h4>
                        <pre><code class="language-bash">curl -X GET "https://api.mycase.com/api/v1/users?limit=25&offset=0" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json"</code></pre>
                    </div>

                    <div class="sl-code-example">
                        <h4>Python</h4>
                        <pre><code class="language-python">import requests

headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}

response = requests.get(
    "https://api.mycase.com/api/v1/users",
    headers=headers,
    params={"limit": 25, "offset": 0}
)

print(response.json())</code></pre>
                    </div>
                </div>
            </div>
        </main>
    </body>
    </html>
    """


@pytest.fixture
def stoplight_schema_definitions():
    """JSON schema definitions page."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Schemas - MyCase API</title></head>
    <body>
        <main class="sl-elements-article">
            <h1>Schema Definitions</h1>

            <div class="sl-schema">
                <h2>User Object</h2>
                <table class="sl-table">
                    <thead>
                        <tr>
                            <th>Field</th>
                            <th>Type</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><code>id</code></td>
                            <td>integer</td>
                            <td>Unique identifier for the user</td>
                        </tr>
                        <tr>
                            <td><code>email</code></td>
                            <td>string</td>
                            <td>User's email address</td>
                        </tr>
                        <tr>
                            <td><code>first_name</code></td>
                            <td>string</td>
                            <td>User's first name</td>
                        </tr>
                        <tr>
                            <td><code>last_name</code></td>
                            <td>string</td>
                            <td>User's last name</td>
                        </tr>
                        <tr>
                            <td><code>status</code></td>
                            <td>enum</td>
                            <td>Account status: active, inactive, pending</td>
                        </tr>
                    </tbody>
                </table>

                <h3>Example</h3>
                <pre><code class="language-json">{
  "id": 12345,
  "email": "user@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "status": "active"
}</code></pre>
            </div>
        </main>
    </body>
    </html>
    """


# ============================================================================
# Mock JSON Responses
# ============================================================================

@pytest.fixture
def stoplight_api_response_success():
    """Successful API response example."""
    return {
        "data": [
            {
                "id": 1,
                "email": "john@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "status": "active"
            },
            {
                "id": 2,
                "email": "jane@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "status": "active"
            }
        ],
        "meta": {
            "total": 2,
            "limit": 25,
            "offset": 0
        }
    }


@pytest.fixture
def stoplight_api_response_error():
    """Error API response examples."""
    return {
        "401": {
            "error": {
                "code": "unauthorized",
                "message": "Invalid authentication token",
                "details": "The provided Bearer token is invalid or expired"
            }
        },
        "429": {
            "error": {
                "code": "rate_limit_exceeded",
                "message": "Too many requests",
                "retry_after": 60
            }
        },
        "404": {
            "error": {
                "code": "not_found",
                "message": "Resource not found",
                "details": "The requested endpoint does not exist"
            }
        }
    }


# ============================================================================
# Expected Output Structures
# ============================================================================

@pytest.fixture
def expected_json_structure():
    """Expected structure for JSON export of Stoplight.io docs."""
    return {
        "metadata": {
            "source_url": str,
            "scraped_at": str,
            "total_pages": int,
            "scraper_version": str
        },
        "pages": list,
        "api_endpoints": list,
        "schemas": list,
        "guides": list
    }


@pytest.fixture
def expected_markdown_sections():
    """Expected sections in Markdown output."""
    return [
        "# MyCase API Documentation",
        "## Introduction",
        "## Authentication",
        "## API Reference",
        "### GET /api/v1/users",
        "#### Parameters",
        "#### Response",
        "```json",
        "```bash",
        "```python"
    ]


# ============================================================================
# Test Data Collections
# ============================================================================

@pytest.fixture
def stoplight_url_patterns():
    """Common URL patterns found in Stoplight.io sites."""
    return {
        "valid": [
            "https://mycaseapi.stoplight.io/docs/mycase-api-documentation",
            "https://mycaseapi.stoplight.io/docs/mycase-api-documentation/introduction",
            "https://mycaseapi.stoplight.io/docs/mycase-api-documentation/api/users",
        ],
        "invalid": [
            "https://mycaseapi.stoplight.io/admin",  # Not documentation
            "https://external.com/docs",  # Different domain
            "https://mycaseapi.stoplight.io/docs/../etc/passwd",  # Path traversal
        ]
    }


@pytest.fixture
def stoplight_css_selectors():
    """CSS selectors specific to Stoplight.io documentation."""
    return {
        "navigation": [
            ".sl-elements-api-docs-nav",
            ".sl-stack",
            ".sl-stack-item"
        ],
        "main_content": [
            ".sl-elements-article",
            "main",
            ".sl-markdown-viewer"
        ],
        "api_operations": [
            ".sl-http-operation",
            ".sl-http-method",
            ".sl-http-path"
        ],
        "code_blocks": [
            ".sl-code-block",
            "pre code",
            ".language-json"
        ],
        "callouts": [
            ".sl-callout",
            ".sl-callout-info",
            ".sl-callout-warning"
        ]
    }


@pytest.fixture
def rate_limit_scenarios():
    """Rate limiting test scenarios."""
    return {
        "normal": {
            "requests_per_second": 5.0,
            "expected_delay": 0.2
        },
        "conservative": {
            "requests_per_second": 1.0,
            "expected_delay": 1.0
        },
        "aggressive": {
            "requests_per_second": 10.0,
            "expected_delay": 0.1
        },
        "with_429": {
            "retry_after": 60,
            "max_retries": 3,
            "backoff_factor": 2.0
        }
    }


# ============================================================================
# Helper Functions
# ============================================================================

def create_stoplight_mock_response(url: str, html_content: str, status: int = 200) -> Dict:
    """Helper to create mock response for Stoplight.io requests."""
    return {
        "url": url,
        "body": html_content,
        "status": status,
        "headers": {
            "Content-Type": "text/html; charset=utf-8",
            "X-RateLimit-Limit": "60",
            "X-RateLimit-Remaining": "59"
        }
    }


def validate_stoplight_json_output(json_data: Dict) -> bool:
    """Validate that JSON output has correct structure for Stoplight.io docs."""
    required_keys = ["metadata", "pages"]
    return all(key in json_data for key in required_keys)


def extract_api_endpoints_from_html(html: str) -> List[Dict]:
    """Extract API endpoint information from Stoplight.io HTML."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'html.parser')
    endpoints = []

    for operation in soup.find_all('div', class_='sl-http-operation'):
        method_elem = operation.find(class_='sl-http-method')
        path_elem = operation.find(class_='sl-http-path')

        if method_elem and path_elem:
            endpoints.append({
                "method": method_elem.get_text().strip(),
                "path": path_elem.get_text().strip()
            })

    return endpoints
