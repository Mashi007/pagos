#!/bin/bash
# Test runner script for pagos and prestamos services

set -e

echo "======================================"
echo "Pagos and Prestamos Test Runner"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
TEST_TYPE="${1:-all}"  # all, smoke, integration, pagos, prestamos
VERBOSE="${2:-}"       # v for verbose

PYTEST_ARGS="-v --tb=short"

if [ "$VERBOSE" = "vv" ]; then
    PYTEST_ARGS="-vv --tb=long"
fi

case "$TEST_TYPE" in
    smoke)
        echo -e "${YELLOW}Running SMOKE tests (must pass before deploy)...${NC}"
        pytest tests/smoke/ $PYTEST_ARGS -m smoke
        ;;
    
    integration)
        echo -e "${YELLOW}Running INTEGRATION tests...${NC}"
        pytest tests/integration/ $PYTEST_ARGS -m integration
        ;;
    
    pagos)
        echo -e "${YELLOW}Running PAGOS tests...${NC}"
        pytest tests/ $PYTEST_ARGS -k pagos
        ;;
    
    prestamos)
        echo -e "${YELLOW}Running PRESTAMOS tests...${NC}"
        pytest tests/ $PYTEST_ARGS -k prestamos
        ;;
    
    coverage)
        echo -e "${YELLOW}Running tests with COVERAGE report...${NC}"
        pytest tests/ $PYTEST_ARGS --cov=app --cov-report=html --cov-report=term-missing
        echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
        ;;
    
    all|*)
        echo -e "${YELLOW}Running ALL tests...${NC}"
        pytest tests/ $PYTEST_ARGS
        ;;
esac

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Tests failed!${NC}"
    exit 1
fi
