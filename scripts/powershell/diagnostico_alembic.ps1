# Script de diagnóstico para problemas con Alembic
# Ejecuta verificaciones de configuración y conexión

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DIAGNÓSTICO DE ALEMBIC" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Guardar el directorio actual
$originalLocation = Get-Location

try {
    # Cambiar al directorio backend
    $backendPath = Join-Path $PSScriptRoot ".." ".." "backend"
    $backendPath = Resolve-Path $backendPath -ErrorAction Stop
    Set-Location $backendPath
    Write-Host "📁 Directorio: $backendPath" -ForegroundColor Green
    Write-Host ""

    # Ejecutar script de diagnóstico
    python scripts\diagnostico_alembic.py
    
    exit $LASTEXITCODE
}
catch {
    Write-Host ""
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit 1
}
finally {
    # Volver al directorio original
    Set-Location $originalLocation
}










