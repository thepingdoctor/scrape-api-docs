#!/bin/bash
# Test runner script for Stoplight.io scraping tests
#
# Usage:
#   ./run_stoplight_tests.sh [category]
#
# Categories:
#   all        - Run all tests (default)
#   unit       - Run unit tests only
#   integration - Run integration tests
#   e2e        - Run end-to-end tests (slow, requires network)
#   performance - Run performance tests
#   coverage   - Run with coverage report

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Stoplight.io Scraping Test Suite${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Install with: pip install pytest pytest-asyncio pytest-cov"
    exit 1
fi

# Default to running all tests
TEST_CATEGORY="${1:-all}"

case "$TEST_CATEGORY" in
    all)
        echo -e "${YELLOW}Running ALL tests (excluding E2E)...${NC}"
        pytest "$SCRIPT_DIR/test_stoplight_scraper.py" \
            -v \
            -m "not e2e" \
            --tb=short
        ;;

    unit)
        echo -e "${YELLOW}Running UNIT tests...${NC}"
        pytest "$SCRIPT_DIR/test_stoplight_scraper.py" \
            -v \
            -m "unit" \
            --tb=short
        ;;

    integration)
        echo -e "${YELLOW}Running INTEGRATION tests...${NC}"
        pytest "$SCRIPT_DIR/test_stoplight_scraper.py" \
            -v \
            -m "integration" \
            --tb=short
        ;;

    e2e)
        echo -e "${YELLOW}Running E2E tests (requires network)...${NC}"
        echo -e "${YELLOW}Warning: These tests make real HTTP requests${NC}"
        pytest "$SCRIPT_DIR/test_stoplight_scraper.py" \
            -v \
            -m "e2e" \
            --run-e2e \
            --tb=short
        ;;

    performance)
        echo -e "${YELLOW}Running PERFORMANCE tests...${NC}"
        pytest "$SCRIPT_DIR/test_stoplight_scraper.py" \
            -v \
            -m "performance" \
            --tb=short
        ;;

    coverage)
        echo -e "${YELLOW}Running tests with COVERAGE report...${NC}"
        pytest "$SCRIPT_DIR/test_stoplight_scraper.py" \
            -v \
            -m "not e2e" \
            --cov=scrape_api_docs \
            --cov-report=html \
            --cov-report=term-missing \
            --cov-report=xml \
            --tb=short

        echo ""
        echo -e "${GREEN}Coverage report generated:${NC}"
        echo "  HTML: htmlcov/index.html"
        echo "  XML:  coverage.xml"
        ;;

    *)
        echo -e "${RED}Unknown test category: $TEST_CATEGORY${NC}"
        echo ""
        echo "Valid categories:"
        echo "  all        - Run all tests (default)"
        echo "  unit       - Run unit tests only"
        echo "  integration - Run integration tests"
        echo "  e2e        - Run end-to-end tests (slow, requires network)"
        echo "  performance - Run performance tests"
        echo "  coverage   - Run with coverage report"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Test run complete!${NC}"
echo -e "${GREEN}==================================================${NC}"
