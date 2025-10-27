# Script para ejecutar la migración de evaluación de 7 criterios
Write-Host "========================================"
Write-Host "EJECUTANDO MIGRACION: 7 Criterios"
Write-Host "========================================"

# Cambiar al directorio backend
Set-Location -Path "backend"

# Ejecutar migración de Alembic
Write-Host "Ejecutando migracion de Alembic..."

# Verificar si estamos en producción o desarrollo
if ($env:ENVIRONMENT -eq "production") {
    Write-Host "Modo: PRODUCCION"
    alembic upgrade head
} else {
    Write-Host "Modo: DESARROLLO"
    python -m alembic upgrade head
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "Migracion ejecutada exitosamente"
} else {
    Write-Host "Error ejecutando migracion"
    exit 1
}

# Volver al directorio original
Set-Location -Path ".."

Write-Host "========================================"
Write-Host "MIGRACION COMPLETADA"
Write-Host "========================================"


