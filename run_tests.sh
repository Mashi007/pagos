#!/bin/bash
# Test runner script for pagos and prestamos services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/backend:${PYTHONPATH:-}"
if [ -z "${SECRET_KEY:-}" ]; then
  export SECRET_KEY="k7Xp2mN9qL4vR8wY3zA6bC1dE5fG0hJ2sT4uV6wX8yZ0"
fi

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

warn_pg_if_needed() {
  if [ -z "${TEST_DATABASE_URL:-}" ] && ! echo "${DATABASE_URL:-}" | grep -qE '^(postgresql|postgres)'; then
    echo -e "${YELLOW}AVISO: defina DATABASE_URL o TEST_DATABASE_URL (PostgreSQL) para crear el esquema en tests.${NC}"
  fi
}

case "$TEST_TYPE" in
    smoke)
        warn_pg_if_needed
        echo -e "${YELLOW}Running SMOKE tests (must pass before deploy)...${NC}"
        pytest tests/smoke/ $PYTEST_ARGS -m smoke
        ;;
    
    integration)
        warn_pg_if_needed
        echo -e "${YELLOW}Running INTEGRATION tests...${NC}"
        pytest tests/integration/ $PYTEST_ARGS -m integration
        ;;
    
    pagos)
        warn_pg_if_needed
        echo -e "${YELLOW}Running PAGOS tests...${NC}"
        pytest tests/ $PYTEST_ARGS -k pagos
        ;;
    
    prestamos)
        warn_pg_if_needed
        echo -e "${YELLOW}Running PRESTAMOS tests...${NC}"
        pytest tests/ $PYTEST_ARGS -k prestamos
        ;;
    
    coverage)
        warn_pg_if_needed
        echo -e "${YELLOW}Running tests with COVERAGE report...${NC}"
        pytest tests/ $PYTEST_ARGS --cov=app --cov-report=html --cov-report=term-missing
        echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
        ;;
    
    all|*)
        warn_pg_if_needed
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
