# Stoplight.io Scraping Test Suite

Comprehensive test suite for Stoplight.io documentation scraping functionality.

## Overview

This test suite ensures robust scraping of Stoplight.io-based API documentation sites like:
- https://mycaseapi.stoplight.io/docs/mycase-api-documentation
- Other Stoplight.io hosted documentation

## Test Structure

```
tests/
├── test_stoplight_scraper.py      # Main test suite
├── fixtures/
│   └── stoplight_fixtures.py      # Shared fixtures and mock data
└── README_STOPLIGHT_TESTS.md      # This file
```

## Test Categories

### 1. Unit Tests (26+ tests)

#### Page Discovery (5 tests)
- `test_discovers_navigation_links` - Navigation link extraction
- `test_filters_external_links` - External link filtering
- `test_max_pages_limit_respected` - Max pages enforcement
- `test_deduplicates_urls` - URL deduplication
- Additional edge cases

#### Content Extraction (5 tests)
- `test_extracts_api_endpoints` - API endpoint documentation
- `test_extracts_code_blocks` - Code block extraction
- `test_extracts_authentication_info` - Auth documentation
- `test_preserves_markdown_formatting` - Markdown conversion
- `test_handles_callouts_and_alerts` - Stoplight.io callouts

#### Error Handling (5 tests)
- `test_handles_404_pages` - 404 error handling
- `test_handles_network_timeout` - Timeout handling
- `test_handles_rate_limiting_429` - Rate limit responses
- `test_handles_malformed_html` - Malformed HTML parsing
- `test_handles_empty_content` - Empty page handling

#### Rate Limiting (3 tests)
- `test_rate_limiter_respects_limits` - Rate limit enforcement
- `test_exponential_backoff_on_errors` - Retry backoff
- `test_respects_robots_txt_crawl_delay` - robots.txt compliance

### 2. Integration Tests (4 tests)

- `test_scrapes_multi_page_documentation` - Multi-page scraping
- `test_async_scraper_performance` - Async performance
- `test_output_format_validation` - Format validation

### 3. Dynamic Content Tests (3 tests)

- `test_detects_spa_content` - SPA detection
- `test_javascript_rendering_required` - JS rendering
- `test_fallback_to_static_extraction` - Static fallback

### 4. Output Format Tests (2 tests)

- `test_json_output_structure` - JSON structure validation
- `test_markdown_output_formatting` - Markdown formatting

### 5. E2E Tests (2 tests)

- `test_scrape_mycase_api_docs` - Real MyCase API docs
- `test_multiple_stoplight_sites` - Multiple sites

### 6. Performance Tests (2 tests)

- `test_scraping_throughput` - Throughput benchmarks
- `test_memory_usage_bounded` - Memory profiling

## Running Tests

### Run All Tests
```bash
pytest tests/test_stoplight_scraper.py -v
```

### Run by Category
```bash
# Unit tests only
pytest tests/test_stoplight_scraper.py -m unit -v

# Integration tests
pytest tests/test_stoplight_scraper.py -m integration -v

# E2E tests (slow, requires network)
pytest tests/test_stoplight_scraper.py -m e2e --run-e2e -v

# Performance tests
pytest tests/test_stoplight_scraper.py -m performance -v
```

### Run with Coverage
```bash
pytest tests/test_stoplight_scraper.py --cov=scrape_api_docs --cov-report=html
```

### Run Specific Tests
```bash
# Test page discovery only
pytest tests/test_stoplight_scraper.py::TestStoplightPageDiscovery -v

# Test content extraction only
pytest tests/test_stoplight_scraper.py::TestStoplightContentExtraction -v

# Test error handling
pytest tests/test_stoplight_scraper.py::TestStoplightErrorHandling -v
```

## Test Markers

Tests are marked with pytest markers for selective execution:

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests (slow, network required)
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.performance` - Performance benchmarks
- `@pytest.mark.asyncio` - Async tests

## Test Coverage Goals

- **Overall Coverage**: >80%
- **Page Discovery**: >90%
- **Content Extraction**: >85%
- **Error Handling**: >95%
- **Rate Limiting**: >90%

## Mock Data

The test suite uses realistic mock data that matches actual Stoplight.io structure:

1. **Navigation HTML** - Sidebar navigation with grouped links
2. **API Reference HTML** - HTTP operations with parameters and responses
3. **Authentication HTML** - Auth documentation with code examples
4. **Dynamic Content HTML** - React/SPA-based content
5. **Error Pages** - 404 and other error responses

## Test Sites

### MyCase API Documentation
- URL: https://mycaseapi.stoplight.io/docs/mycase-api-documentation
- Features: Complete REST API documentation with OpenAPI spec
- Use Case: Primary test target for E2E tests

### Additional Sites
Add discovered Stoplight.io sites to `fixtures/stoplight_fixtures.py:STOPLIGHT_TEST_SITES`

## Known Edge Cases

1. **Dynamic Loading**: Some content loads via JavaScript
2. **Rate Limiting**: Stoplight.io may enforce rate limits
3. **Navigation Structure**: Can vary between sites
4. **Code Examples**: Multiple languages in tabs
5. **Schema Definitions**: Complex nested object structures

## Error Scenarios Tested

- 404 Not Found pages
- 429 Too Many Requests (rate limiting)
- Network timeouts
- Malformed HTML
- Empty content pages
- Missing authentication
- Invalid URLs

## Performance Expectations

- **Throughput**: 2-5 pages/second (async mode)
- **Memory**: <500MB for 100-page site
- **Network**: Respects rate limits and delays
- **Retry Logic**: Exponential backoff on errors

## Integration with CI/CD

### GitHub Actions
```yaml
- name: Run Stoplight.io Tests
  run: |
    pytest tests/test_stoplight_scraper.py -m "not e2e" -v
    pytest tests/test_stoplight_scraper.py -m e2e --run-e2e || true
```

### Coverage Reporting
```bash
pytest tests/test_stoplight_scraper.py \
  --cov=scrape_api_docs \
  --cov-report=xml \
  --cov-report=term-missing
```

## Troubleshooting

### Tests Failing Locally

1. **Install test dependencies**:
   ```bash
   pip install -r tests/requirements.txt
   ```

2. **Check network access** (for E2E tests):
   ```bash
   curl -I https://mycaseapi.stoplight.io/docs/mycase-api-documentation
   ```

3. **Verify pytest markers**:
   ```bash
   pytest --markers
   ```

### Mock Data Issues

If mocks don't match real site structure:

1. Visit actual Stoplight.io site
2. Inspect HTML structure
3. Update fixtures in `stoplight_fixtures.py`
4. Re-run tests

### Rate Limiting in Tests

If encountering rate limits during testing:

1. Increase delays in `rate_limiter.py`
2. Use VCR.py to record/replay HTTP interactions
3. Skip E2E tests in CI: `pytest -m "not e2e"`

## Contributing

When adding new tests:

1. Follow existing naming conventions
2. Add appropriate pytest markers
3. Update this README with test descriptions
4. Ensure tests are deterministic (no flakiness)
5. Mock external dependencies
6. Document expected behavior

## Test Quality Metrics

Current Status:
- ✅ 26+ unit tests
- ✅ 4 integration tests
- ✅ 3 dynamic content tests
- ✅ 2 output format tests
- ✅ 2 E2E tests
- ✅ 2 performance tests

**Total: 39+ comprehensive tests**

## Future Enhancements

- [ ] Add VCR.py for HTTP recording/replay
- [ ] Implement snapshot testing for HTML structures
- [ ] Add property-based testing with Hypothesis
- [ ] Create visual regression tests
- [ ] Add mutation testing for robustness
- [ ] Implement contract testing for API responses

## Resources

- [Stoplight.io Documentation](https://docs.stoplight.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [responses Library](https://github.com/getsentry/responses)
- [Project Test Strategy](../docs/testing-strategy.md)
