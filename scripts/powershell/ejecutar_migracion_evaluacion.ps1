# Script para ejecutar la migración de evaluación de 7 criterios
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "EJECUTANDO MIGRACIÓN: 7 Criterios" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Cambiar al directorio backend
Set-Location -Path "backend"

# Ejecutar migración de Alembic
Write-Host "`nEjecutando migración de Alembic..." -ForegroundColor Yellow

# Verificar si estamos en producción o desarrollo
if ($env:ENVIRONMENT -eq "production") {
    Write-Host "Modo: PRODUCCIÓN" -ForegroundColor Red
    alembic upgrade head
} else {
    Write-Host "Modo: DESARROLLO" -ForegroundColor Green
    python -m alembic upgrade head
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Migración ejecutada exitosamente" -ForegroundColor Green
} else {
    Write-Host "`n❌ Error ejecutando migración" -ForegroundColor Red
    exit 1
}

# Volver al directorio original
Set-Location -Path ".."

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "MIGRACIÓN COMPLETADA" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

