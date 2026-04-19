# Test runner script for pagos and prestamos services (Windows)
# Usage: .\run_tests.ps1 [smoke|integration|pagos|prestamos|coverage|all] [vv]

param(
    [string]$TestType = "all",
    [string]$Verbose = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$Backend = Join-Path $RepoRoot "backend"
if (-not (Test-Path $Backend)) {
    Write-Host "No se encontro la carpeta backend en $RepoRoot" -ForegroundColor Red
    exit 1
}
$env:PYTHONPATH = (Resolve-Path $Backend).Path

if (-not $env:SECRET_KEY) {
    # Solo para pytest local; en produccion defina SECRET_KEY real en el entorno.
    $env:SECRET_KEY = "k7Xp2mN9qL4vR8wY3zA6bC1dE5fG0hJ2sT4uV6wX8yZ0"
}

Write-Host "======================================"
Write-Host "Pagos and Prestamos Test Runner"
Write-Host "======================================"
Write-Host ""

$needsPg = @("smoke", "integration", "pagos", "prestamos", "coverage", "all") -contains $TestType
$pgSet = ($env:TEST_DATABASE_URL -match "postgresql|postgres://") -or ($env:DATABASE_URL -match "postgresql|postgres://")
if ($needsPg -and -not $pgSet) {
    Write-Host "AVISO: smoke/integration y create_all requieren PostgreSQL." -ForegroundColor Yellow
    Write-Host "  Ej.: `$env:DATABASE_URL='postgresql+psycopg2://usuario:clave@127.0.0.1:5432/nombre_bd'" -ForegroundColor Yellow
    Write-Host "  Opcional: `$env:TEST_DATABASE_URL='...' para el motor de pytest sin tocar DATABASE_URL de la app." -ForegroundColor Yellow
    Write-Host ""
}

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
