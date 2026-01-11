# Script PowerShell para ejecutar análisis de estructura y coherencia
# Analiza estructura de columnas, relaciones entre tablas y coherencia con endpoints

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ANÁLISIS DE ESTRUCTURA Y COHERENCIA" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "backend")) {
    Write-Host "❌ Error: Este script debe ejecutarse desde la raíz del proyecto" -ForegroundColor Red
    exit 1
}

# Activar entorno virtual si existe
if (Test-Path "backend\.venv\Scripts\Activate.ps1") {
    Write-Host "🔧 Activando entorno virtual..." -ForegroundColor Yellow
    & "backend\.venv\Scripts\Activate.ps1"
} elseif (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "🔧 Activando entorno virtual..." -ForegroundColor Yellow
    & ".venv\Scripts\Activate.ps1"
}

# Ejecutar el script de análisis
Write-Host "🚀 Ejecutando análisis de estructura y coherencia..." -ForegroundColor Green
Write-Host ""

python scripts/analisis_estructura_coherencia.py

Write-Host ""
Write-Host "✅ Análisis completado" -ForegroundColor Green
