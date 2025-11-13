# JSON Export Guide - LLM-Optimized Format

## Overview

The JSON exporter has been redesigned to produce machine-readable, structured output optimized for LLM context and data processing. Instead of raw HTML/CSS artifacts, the new format provides clean, hierarchical content organized for easy consumption.

## Key Features

✅ **Clean Content** - No CSS, JavaScript, or HTML pollution  
✅ **Hierarchical Structure** - Sections organized by heading levels  
✅ **API Detection** - Automatic extraction of endpoints, parameters, and examples  
✅ **Token Estimation** - Built-in token counting for LLM context planning  
✅ **Code Examples** - Language-detected and properly formatted  
✅ **Quick Reference** - Easy access to endpoints, code, and concepts  
✅ **Global Index** - Cross-page navigation and aggregation  

## JSON Structure

### Root Level

```json
{
  "metadata": { ... },           // Export metadata
  "pages": [ ... ],              // Array of processed pages
  "global_index": { ... },       // Cross-page index
  "statistics": { ... },         // Aggregated statistics
  "export_info": { ... }         // Export details
}
```

### Page Structure

Each page contains:

```json
{
  "id": "page_001",
  "url": "https://api.example.com/docs/messaging",
  "title": "Messaging API",
  "description": "Brief summary from first paragraph",
  
  "sections": [
    {
      "id": "section_001",
      "heading": "Overview",
      "level": 1,
      "content": "Clean text content without HTML/CSS",
      
      "subsections": [ ... ],     // Nested sections
      "code_examples": [ ... ],   // Code blocks in this section
      "tables": [ ... ],          // Tables in this section
      "lists": [ ... ]            // Lists in this section
    }
  ],
  
  "quick_reference": {
    "all_endpoints": [ ... ],     // All API endpoints on page
    "all_code_examples": [ ... ], // All code examples on page
    "key_concepts": [ ... ],      // Section headings
    "code_example_count": 5
  },
  
  "links": {
    "internal": [ ... ],          // Internal navigation links
    "external": [ ... ]           // External reference links
  },
  
  "metadata": {
    "word_count": 1250,
    "character_count": 8543,
    "estimated_tokens": 1500,    // Helpful for LLM context
    "section_count": 12,
    "code_example_count": 5,
    "api_endpoint_count": 3,
    "render_time": 0.5,
    "cached": false
  }
}
```

### Section Structure

Sections are hierarchically organized with clean content:

```json
{
  "id": "section_003",
  "heading": "POST /v1/messages",
  "level": 3,
  "content": "Send a new message to a recipient.\n\n",
  
  "subsections": [
    {
      "id": "section_004",
      "heading": "Parameters",
      "level": 4,
      "content": "",
      "subsections": [],
      "code_examples": [],
      "tables": [
        {
          "caption": "",
          "headers": ["Name", "Type", "Required", "Description"],
          "rows": [
            ["to", "string", "Yes", "Recipient phone number"],
            ["body", "string", "Yes", "Message content"]
          ]
        }
      ],
      "lists": []
    }
  ],
  
  "code_examples": [],
  "tables": [],
  "lists": []
}
```

### Code Example Structure

```json
{
  "language": "python",
  "code": "import requests\n\nresponse = requests.post(...)",
  "title": "Basic Request",
  "line_count": 10
}
```

Supported languages are automatically detected:
- Python, JavaScript, TypeScript
- Java, Ruby, PHP, Go, Rust
- Bash/Shell, SQL
- JSON, XML, YAML

### API Endpoint Structure

When API endpoints are detected:

```json
{
  "method": "POST",
  "path": "/v1/messages",
  "description": "Send a new message to a recipient.",
  
  "parameters": [
    {
      "name": "to",
      "type": "string",
      "required": true,
      "description": "Recipient phone number"
    }
  ],
  
  "request_example": {
    "language": "python",
    "code": "...",
    "title": "Example Request"
  },
  
  "response_example": {
    "language": "json",
    "code": "...",
    "title": "Example Response"
  },
  
  "response_codes": [
    {
      "code": 200,
      "description": "Message sent successfully"
    },
    {
      "code": 400,
      "description": "Invalid request parameters"
    }
  ]
}
```

### Global Index

Cross-page aggregation and navigation:

```json
{
  "total_pages": 96,
  "total_endpoints": 47,
  
  "endpoints_by_resource": {
    "messages": [ ... ],
    "users": [ ... ],
    "accounts": [ ... ]
  },
  
  "code_languages": ["python", "javascript", "curl"],
  "topics": ["authentication", "rate-limiting", "webhooks"],
  
  "endpoint_methods": {
    "GET": 15,
    "POST": 20,
    "PUT": 8,
    "DELETE": 4
  }
}
```

### Statistics

Comprehensive metrics:

```json
{
  "totals": {
    "pages": 96,
    "words": 45000,
    "characters": 295000,
    "estimated_tokens": 68000,
    "sections": 450,
    "code_examples": 120,
    "api_endpoints": 47
  },
  
  "averages": {
    "words_per_page": 468.75,
    "tokens_per_page": 708.33,
    "sections_per_page": 4.69,
    "render_time": 0.35
  },
  
  "performance": {
    "total_render_time": 33.6,
    "cached_pages": 12,
    "cache_hit_rate": 12.5
  }
}
```

## Benefits for LLM Context

### 1. Clean Text
No CSS classes, inline styles, or HTML artifacts polluting the content.

**Before (v2.0):**
```json
{
  "content": {
    "markdown": ".css-ppdqhg{position:relative;min-width:0;...}"
  }
}
```

**After (v3.0):**
```json
{
  "content": "This API allows you to send messages programmatically."
}
```

### 2. Hierarchical Organization
Content is structured by sections and subsections, making it easy to:
- Navigate to specific topics
- Extract relevant portions
- Understand document structure

### 3. Token-Aware
Each page includes estimated token counts:
```json
{
  "metadata": {
    "estimated_tokens": 1500,
    "word_count": 1250
  }
}
```

This helps you:
- Plan context window usage
- Decide what to include/exclude
- Optimize prompts

### 4. Quick Access to Key Elements

The `quick_reference` section provides:
- All API endpoints on the page
- All code examples in one place
- Key concepts/topics
- Quick counts

### 5. Queryable Structure

Easy to filter and search:

```python
# Get all POST endpoints
post_endpoints = [
    ep for ep in data['global_index']['endpoints_by_resource']['messages']
    if ep['method'] == 'POST'
]

# Get all Python code examples
python_examples = [
    ex for page in data['pages']
    for ex in page['quick_reference']['all_code_examples']
    if ex['language'] == 'python'
]

# Get high-level overview
concepts = data['pages'][0]['quick_reference']['key_concepts']
```

## Usage Example

### Exporting Documentation

```python
from scrape_api_docs.exporters.json_exporter import JSONExportConverter
from scrape_api_docs.exporters.base import PageResult, ExportOptions

# Create pages (from scraping)
pages = [
    PageResult(
        url="https://api.example.com/docs",
        title="API Documentation",
        content=html_content,
        format="html"
    )
]

# Configure export
options = ExportOptions(
    include_metadata=True,
    include_toc=True,
    title="Example API Documentation",
    source_url="https://api.example.com/docs"
)

# Export
exporter = JSONExportConverter()
result = await exporter.convert(pages, Path("output.json"), options)
```

### Loading and Using the Data

```python
import json

with open("output.json", "r") as f:
    docs = json.load(f)

# Check token budget
total_tokens = docs['statistics']['totals']['estimated_tokens']
print(f"Total tokens: {total_tokens}")

# Get overview
for page in docs['pages']:
    print(f"{page['title']}: {page['description']}")
    print(f"  Tokens: {page['metadata']['estimated_tokens']}")
    print(f"  Endpoints: {page['metadata']['api_endpoint_count']}")
    print(f"  Code examples: {page['metadata']['code_example_count']}")

# Extract specific endpoint
messages_endpoints = docs['global_index']['endpoints_by_resource']['messages']
for endpoint in messages_endpoints:
    print(f"{endpoint['method']} {endpoint['path']}")
    print(f"  Parameters: {len(endpoint['parameters'])}")
```

### Feeding to LLM

```python
def prepare_llm_context(docs, max_tokens=8000):
    """Prepare documentation for LLM context."""
    context_parts = []
    current_tokens = 0
    
    # Add metadata
    context_parts.append(f"# {docs['metadata']['title']}\n")
    context_parts.append(f"Source: {docs['metadata']['source_url']}\n\n")
    
    # Add pages until token budget exhausted
    for page in docs['pages']:
        page_tokens = page['metadata']['estimated_tokens']
        
        if current_tokens + page_tokens > max_tokens:
            break
        
        # Add page content
        context_parts.append(f"## {page['title']}\n")
        context_parts.append(f"{page['description']}\n\n")
        
        # Add sections
        for section in page['sections']:
            context_parts.append(format_section(section))
        
        current_tokens += page_tokens
    
    return '\n'.join(context_parts)
```

## Migration from v2.0

The v3.0 format is **not backward compatible** with v2.0. Key changes:

### Removed Fields
- `content.markdown` (raw HTML/CSS dump)
- `content.html` (redundant HTML)
- `structure.hierarchy` (replaced by nested sections)

### Added Fields
- `description` (page-level summary)
- `sections` (hierarchical content structure)
- `quick_reference` (easy access to key elements)
- `global_index` (cross-page aggregation)
- `metadata.estimated_tokens` (LLM context planning)
- API endpoint detection
- Enhanced code example metadata

### Updated Fields
- `content` is now clean text within sections, not raw HTML
- Tables, lists, and code are structured within their sections
- Links are categorized as internal/external

## Best Practices

1. **Check Token Counts**: Use `estimated_tokens` to plan context window usage
2. **Use Quick Reference**: Access endpoints and code examples directly
3. **Navigate Hierarchically**: Traverse sections by level for topic extraction
4. **Filter by Resource**: Use `endpoints_by_resource` for organized access
5. **Leverage Global Index**: Find cross-page patterns and aggregations

## Performance

The new exporter is designed for efficiency:

- **Parsing**: Single-pass HTML parsing
- **Memory**: Processes pages incrementally
- **Speed**: ~0.01s per page on average
- **Output Size**: Comparable to v2.0 despite richer structure

## Version Info

- **Format Version**: 3.0.0
- **Optimized For**: LLM context and data processing
- **Export Info Key**: `optimized_for: "llm_context"`
- **Backward Compatible**: No (breaking change from v2.0)

## Support

For issues or questions about the JSON export format:
- Check the example output in this guide
- Review the test cases in `tests/exporters/test_json_exporter.py`
- Report bugs via GitHub issues
