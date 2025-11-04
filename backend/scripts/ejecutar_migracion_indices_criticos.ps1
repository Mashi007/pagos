# Script para ejecutar la migración de índices críticos de performance
Write-Host "========================================"
Write-Host "EJECUTANDO MIGRACION: Índices Críticos"
Write-Host "========================================"
Write-Host ""

# Cambiar al directorio backend
Set-Location -Path "backend"

Write-Host "📋 Esta migración creará índices para resolver timeouts de 57+ segundos"
Write-Host "📈 Impacto esperado: Reducción de timeouts de 57s a <500ms (114x mejora)"
Write-Host ""

# Ejecutar migración usando el script Python
Write-Host "Ejecutando migración de Alembic..."
python scripts/ejecutar_migracion_indices_criticos.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================"
    Write-Host "✅ MIGRACION COMPLETADA EXITOSAMENTE"
    Write-Host "========================================"
    Write-Host ""
    Write-Host "📊 PRÓXIMOS PASOS:"
    Write-Host "1. Verificar que los índices se crearon correctamente"
    Write-Host "2. Monitorear tiempos de respuesta en producción"
    Write-Host "3. El endpoint debería responder en <500ms ahora"
} else {
    Write-Host ""
    Write-Host "========================================"
    Write-Host "❌ ERROR EJECUTANDO MIGRACION"
    Write-Host "========================================"
    exit 1
}

# Volver al directorio original
Set-Location -Path ".."

