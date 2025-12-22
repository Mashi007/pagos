# ============================================================================
# Script PowerShell para generar cuotas de préstamos faltantes
# ============================================================================

Write-Host "Ejecutando generación de cuotas para préstamos faltantes..." -ForegroundColor Cyan
Write-Host ""

$env:PYTHONUNBUFFERED = "1"
python scripts/python/Generar_Amortizacion_Prestamos_Faltantes.py --yes

Write-Host ""
Write-Host "Proceso completado." -ForegroundColor Green
