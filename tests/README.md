# Test Suite for scrape-api-docs

Comprehensive test suite with 85%+ code coverage for the documentation scraper project.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── pytest.ini               # Pytest configuration
├── requirements.txt         # Test dependencies
├── unit/                    # Unit tests (60% of tests)
│   ├── test_scraper.py      # Core scraper functions (95+ tests)
│   ├── test_streamlit_app.py # Streamlit UI logic
│   ├── test_cli.py          # CLI module tests
│   └── test_rate_limiter.py # Rate limiting logic
├── integration/             # Integration tests (30% of tests)
│   ├── test_http_integration.py    # HTTP client integration
│   └── test_parsing_integration.py # BeautifulSoup + Markdownify
├── security/                # Security tests (10% of tests)
│   ├── test_input_validation.py # Input validation security
│   └── test_ssrf_prevention.py  # SSRF attack prevention
└── e2e/                     # End-to-end tests
    └── test_cli_e2e.py      # Full CLI workflows

```

## Running Tests

### Install Dependencies

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Or with poetry
poetry install --with dev
```

### Run All Tests

```bash
# Run full test suite with coverage
pytest

# Run with verbose output
pytest -v

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/security/
```

### Run by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only security tests
pytest -m security

# Run integration tests
pytest -m integration

# Run E2E tests
pytest -m e2e

# Skip slow tests
pytest -m "not slow"
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=src/scrape_api_docs --cov-report=html

# View in browser
open htmlcov/index.html

# Terminal report with missing lines
pytest --cov=src/scrape_api_docs --cov-report=term-missing

# XML report for CI/CD
pytest --cov=src/scrape_api_docs --cov-report=xml
```

## Test Categories

### Unit Tests (160+ tests)
- **test_scraper.py**: 95+ tests covering all scraper functions
- **test_streamlit_app.py**: Tests for Streamlit UI logic
- **test_cli.py**: CLI argument parsing and execution
- **test_rate_limiter.py**: Rate limiting algorithms

### Integration Tests (40+ tests)
- **test_http_integration.py**: HTTP client, sessions, redirects
- **test_parsing_integration.py**: HTML parsing and Markdown conversion

### Security Tests (25+ tests)
- **test_input_validation.py**: XSS, path traversal, command injection
- **test_ssrf_prevention.py**: SSRF attack vectors, private IP blocking

### E2E Tests
- **test_cli_e2e.py**: Complete CLI workflows

## Test Coverage Goals

- **Overall Coverage**: ≥ 85%
- **Core scraper.py**: ≥ 90%
- **Streamlit app**: ≥ 80%
- **CLI modules**: ≥ 75%

## Key Test Fixtures

### HTML Fixtures
- `simple_html`: Basic HTML page
- `complex_html`: Nested structures, tables, code blocks
- `malformed_html`: Broken HTML for edge cases
- `multi_link_html`: Multiple internal/external links

### URL Fixtures
- `valid_urls`: Collection of valid URLs
- `invalid_urls`: Invalid/malicious URLs
- `ssrf_urls`: SSRF attack vectors

### Mock Fixtures
- `mock_responses`: HTTP response mocking
- `mock_site_structure`: Multi-page site simulation
- `temp_dir`: Temporary directory for file output

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r tests/requirements.txt
          pip install -e .
      - name: Run tests
        run: pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Test Best Practices

1. **Isolation**: Each test is independent
2. **Speed**: Unit tests run in < 30 seconds
3. **Mocking**: No live HTTP calls in tests
4. **Clarity**: Descriptive test names
5. **AAA Pattern**: Arrange-Act-Assert structure

## Troubleshooting

### Import Errors
```bash
# Ensure package is installed
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
```

### Coverage Not Detected
```bash
# Ensure you're testing the source, not installed package
pytest --cov=src/scrape_api_docs --cov-report=term
```

### Slow Tests
```bash
# Skip slow tests
pytest -m "not slow"

# Run with pytest-xdist for parallel execution
pytest -n auto
```

## Contributing Tests

When adding new tests:

1. Place in appropriate category (unit/integration/security)
2. Use existing fixtures when possible
3. Add appropriate markers (@pytest.mark.unit, etc.)
4. Follow naming convention: `test_<what>_<condition>`
5. Include docstrings explaining the test
6. Maintain ≥ 85% coverage

## Security Testing

Security tests focus on:
- **Input Validation**: XSS, path traversal, command injection
- **SSRF Prevention**: Private IP blocking, localhost filtering
- **URL Sanitization**: Malicious URL patterns
- **Output Safety**: Safe Markdown generation

Run security-focused tests:
```bash
pytest -m security -v
```

## Performance Testing

Performance benchmarks are included:
```bash
# Run performance tests
pytest tests/performance/ -v

# Generate benchmark report
pytest --benchmark-only
```

## Documentation

Each test file includes comprehensive docstrings:
- Purpose of the test
- What is being tested
- Expected behavior
- Edge cases covered

See individual test files for detailed documentation.
