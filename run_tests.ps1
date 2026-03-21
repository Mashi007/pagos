# Test runner script for pagos and prestamos services (Windows)
# Usage: .\run_tests.ps1 [smoke|integration|pagos|prestamos|coverage|all] [vv]

param(
    [string]$TestType = "all",
    [string]$Verbose = ""
)

$ErrorActionPreference = "Stop"

Write-Host "======================================"
Write-Host "Pagos and Prestamos Test Runner"
Write-Host "======================================"
Write-Host ""

$pytest_args = "-v", "--tb=short"

if ($Verbose -eq "vv") {
    $pytest_args = "-vv", "--tb=long"
}

try {
    switch ($TestType) {
        "smoke" {
            Write-Host -ForegroundColor Yellow "Running SMOKE tests (must pass before deploy)..."
            & pytest tests/smoke/ @pytest_args -m smoke
        }
        
        "integration" {
            Write-Host -ForegroundColor Yellow "Running INTEGRATION tests..."
            & pytest tests/integration/ @pytest_args -m integration
        }
        
        "pagos" {
            Write-Host -ForegroundColor Yellow "Running PAGOS tests..."
            & pytest tests/ @pytest_args -k pagos
        }
        
        "prestamos" {
            Write-Host -ForegroundColor Yellow "Running PRESTAMOS tests..."
            & pytest tests/ @pytest_args -k prestamos
        }
        
        "coverage" {
            Write-Host -ForegroundColor Yellow "Running tests with COVERAGE report..."
            & pytest tests/ @pytest_args --cov=app --cov-report=html --cov-report=term-missing
            Write-Host -ForegroundColor Green "Coverage report generated: htmlcov/index.html"
        }
        
        default {
            Write-Host -ForegroundColor Yellow "Running ALL tests..."
            & pytest tests/ @pytest_args
        }
    }
    
    Write-Host -ForegroundColor Green "✓ Tests passed!"
    exit 0
}
catch {
    Write-Host -ForegroundColor Red "✗ Tests failed!"
    exit 1
}
