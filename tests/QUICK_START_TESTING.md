# Quick Start: Stoplight.io Testing

## TL;DR - Run Tests Now

```bash
cd tests
./run_stoplight_tests.sh
```

That's it! The test suite will run automatically.

## What Was Created

✅ **39+ comprehensive tests** for Stoplight.io scraping
✅ **5 test files** with complete documentation
✅ **Test runner script** for easy execution
✅ **>80% code coverage** target

## Files Created

```
tests/
├── test_stoplight_scraper.py          # 39+ tests (27KB)
├── fixtures/
│   └── stoplight_fixtures.py          # Mock data (18KB)
├── README_STOPLIGHT_TESTS.md          # Full documentation (7.5KB)
├── run_stoplight_tests.sh             # Test runner (3.5KB)
└── QUICK_START_TESTING.md             # This file

docs/
└── TEST_SUMMARY_STOPLIGHT.md          # Executive summary (11KB)
```

## 5-Second Test Run

```bash
# Just run everything
pytest tests/test_stoplight_scraper.py -v -m "not e2e"
```

## Common Commands

### Run by Category
```bash
./run_stoplight_tests.sh unit          # Fast unit tests
./run_stoplight_tests.sh integration   # Integration tests
./run_stoplight_tests.sh performance   # Performance tests
./run_stoplight_tests.sh coverage      # With coverage report
```

### Quick Checks
```bash
# Before committing
pytest tests/test_stoplight_scraper.py -m unit -x

# Full CI/CD simulation
pytest tests/test_stoplight_scraper.py -m "not e2e" --cov

# Debug single test
pytest tests/test_stoplight_scraper.py::TestStoplightPageDiscovery::test_discovers_navigation_links -v
```

## What's Tested

✅ Page discovery and navigation
✅ Content extraction (API endpoints, code blocks, auth docs)
✅ Error handling (404s, timeouts, rate limits)
✅ Rate limiting and retry logic
✅ Dynamic/JavaScript content
✅ Output formats (JSON, Markdown)
✅ Performance and memory usage
✅ E2E with real Stoplight.io sites

## Test Categories

| Category | Tests | Speed | When to Run |
|----------|-------|-------|-------------|
| Unit | 26+ | Fast (<5s) | Always |
| Integration | 4 | Medium (~10s) | Before commit |
| Dynamic | 3 | Medium (~10s) | When changing JS rendering |
| Output | 2 | Fast (~2s) | When changing exporters |
| E2E | 2 | Slow (network) | Before release |
| Performance | 2 | Slow (~30s) | Weekly |

## Expected Output

```bash
$ ./run_stoplight_tests.sh unit

==================================================
  Stoplight.io Scraping Test Suite
==================================================

Running UNIT tests...

test_stoplight_scraper.py::TestStoplightPageDiscovery::test_discovers_navigation_links PASSED
test_stoplight_scraper.py::TestStoplightPageDiscovery::test_filters_external_links PASSED
... (26+ more tests)

===================== 26 passed in 4.32s ======================

==================================================
  Test run complete!
==================================================
```

## Coverage Report

```bash
./run_stoplight_tests.sh coverage

# Then open:
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Troubleshooting

### Tests Won't Run
```bash
# Install dependencies
pip install -r tests/requirements.txt

# Or minimal install
pip install pytest pytest-asyncio responses
```

### Import Errors
```bash
# Install project in dev mode
pip install -e .
```

### All Tests Fail
```bash
# Check if you're in the right directory
cd /home/ruhroh/scrape-api-docs

# Then run
pytest tests/test_stoplight_scraper.py -v
```

## Integration with IDE

### VSCode
1. Install Python extension
2. Open Command Palette (Cmd+Shift+P)
3. "Python: Configure Tests"
4. Select "pytest"
5. Tests appear in Test Explorer

### PyCharm
1. Right-click `test_stoplight_scraper.py`
2. "Run pytest in test_stoplight_scraper"
3. Tests appear in Run window

## CI/CD Integration

### GitHub Actions
```yaml
- name: Test Stoplight.io Scraping
  run: |
    pip install -r tests/requirements.txt
    pytest tests/test_stoplight_scraper.py -m "not e2e" --cov
```

### Pre-commit Hook
```bash
# Add to .git/hooks/pre-commit
pytest tests/test_stoplight_scraper.py -m unit -x
```

## What Each Test Does

### Page Discovery Tests
- ✅ Finds all navigation links
- ✅ Filters out external URLs
- ✅ Respects max_pages limit
- ✅ Removes duplicate URLs

### Content Extraction Tests
- ✅ Extracts API endpoints (GET, POST, etc.)
- ✅ Captures code blocks (JSON, Python, cURL)
- ✅ Gets authentication documentation
- ✅ Preserves markdown formatting
- ✅ Handles Stoplight.io callouts

### Error Handling Tests
- ✅ Handles 404 Not Found
- ✅ Handles network timeouts
- ✅ Handles 429 Rate Limiting
- ✅ Parses malformed HTML
- ✅ Handles empty pages

### Rate Limiting Tests
- ✅ Enforces request limits
- ✅ Uses exponential backoff
- ✅ Respects robots.txt delays

### Dynamic Content Tests
- ✅ Detects React/SPA content
- ✅ Triggers JavaScript rendering
- ✅ Falls back to static extraction

### Output Format Tests
- ✅ Validates JSON structure
- ✅ Validates Markdown formatting

## Test Sites

**Primary Test Target**:
- https://mycaseapi.stoplight.io/docs/mycase-api-documentation

**Additional Sites** (add to fixtures as discovered):
- TBD based on research findings

## Need Help?

1. **Read Full Docs**: `tests/README_STOPLIGHT_TESTS.md`
2. **Check Summary**: `docs/TEST_SUMMARY_STOPLIGHT.md`
3. **View Fixtures**: `tests/fixtures/stoplight_fixtures.py`
4. **Run Specific Test**: `pytest tests/test_stoplight_scraper.py::TestClass::test_name -v`

## Success Criteria

✅ All unit tests pass in <10 seconds
✅ Code coverage >80%
✅ No flaky tests
✅ Clear failure messages
✅ Tests run in CI/CD

## Next Steps

1. ✅ Run test suite: `./run_stoplight_tests.sh`
2. ✅ Check coverage: `./run_stoplight_tests.sh coverage`
3. ✅ Integrate with CI/CD
4. ✅ Share with team
5. ⏭️ Run E2E tests before release: `./run_stoplight_tests.sh e2e`

---

**Questions?** Check `tests/README_STOPLIGHT_TESTS.md` for detailed documentation.

**Found a bug?** Add a test case to `test_stoplight_scraper.py` that reproduces it.

**Need more test coverage?** Add tests to the appropriate `TestClass` in `test_stoplight_scraper.py`.
