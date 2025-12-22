# ============================================================================
# Script para monitorear el progreso de generación de cuotas
# ============================================================================
# Uso: .\scripts\monitorear_progreso_cuotas.ps1
# ============================================================================

$projectRoot = "C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos"
$outputFile = Join-Path $projectRoot "output_generacion_cuotas.txt"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "MONITOREO DE PROGRESO - GENERACIÓN DE CUOTAS" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $outputFile)) {
    Write-Host "[INFO] Archivo de salida no encontrado aún." -ForegroundColor Yellow
    Write-Host "       El script puede estar iniciando..." -ForegroundColor Gray
    exit 0
}

# Obtener contenido del archivo
$contenido = Get-Content $outputFile -ErrorAction SilentlyContinue

if (-not $contenido) {
    Write-Host "[INFO] Archivo vacío o en proceso de escritura..." -ForegroundColor Yellow
    exit 0
}

# Extraer información de progreso
$lineasProgreso = $contenido | Select-String -Pattern "PROGRESO" | Select-Object -Last 1
$lineasResumen = $contenido | Select-String -Pattern "RESUMEN|Exitosos|Fallidos|Total procesados|Total cuotas generadas"
$ultimasLineas = $contenido | Select-Object -Last 15

# Mostrar progreso actual
Write-Host "=== PROGRESO ACTUAL ===" -ForegroundColor Green
if ($lineasProgreso) {
    Write-Host $lineasProgreso.Line -ForegroundColor Yellow
} else {
    Write-Host "Procesando..." -ForegroundColor Gray
}

Write-Host ""

# Mostrar resumen si existe
if ($lineasResumen) {
    Write-Host "=== RESUMEN ===" -ForegroundColor Green
    $lineasResumen | ForEach-Object {
        Write-Host $_.Line -ForegroundColor White
    }
    Write-Host ""
}

# Mostrar últimas líneas
Write-Host "=== ÚLTIMAS LÍNEAS ===" -ForegroundColor Green
$ultimasLineas | ForEach-Object {
    if ($_ -match "PROGRESO") {
        Write-Host $_ -ForegroundColor Cyan
    } elseif ($_ -match "OK|cuotas generadas") {
        Write-Host $_ -ForegroundColor Green
    } elseif ($_ -match "ERROR") {
        Write-Host $_ -ForegroundColor Red
    } else {
        Write-Host $_ -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "Archivo completo: $outputFile" -ForegroundColor Gray
Write-Host "================================================================================" -ForegroundColor Cyan
