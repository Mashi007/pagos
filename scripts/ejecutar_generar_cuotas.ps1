# ============================================================================
# Script PowerShell para generar cuotas de préstamos faltantes
# ============================================================================
# Uso: .\scripts\ejecutar_generar_cuotas.ps1
# ============================================================================

# Configurar encoding UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Variables
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
$outputFile = Join-Path $projectRoot "output_generacion_cuotas.txt"
$pythonScript = Join-Path $projectRoot "scripts\python\Generar_Amortizacion_Prestamos_Faltantes.py"

# Cambiar al directorio raíz del proyecto
Set-Location $projectRoot

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "GENERACIÓN DE CUOTAS PARA PRÉSTAMOS FALTANTES" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Directorio de trabajo: $projectRoot" -ForegroundColor Gray
Write-Host "Archivo de salida: $outputFile" -ForegroundColor Gray
Write-Host ""

# Verificar que existe el script Python
if (-not (Test-Path $pythonScript)) {
    Write-Host "[ERROR] No se encuentra el script Python: $pythonScript" -ForegroundColor Red
    exit 1
}

# Verificar que Python está instalado
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python encontrado: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python no está instalado o no está en el PATH" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Iniciando generación de cuotas..." -ForegroundColor Yellow
Write-Host ""

# Configurar variable de entorno para salida sin buffer
$env:PYTHONUNBUFFERED = "1"

# Ejecutar script Python y guardar salida
try {
    python $pythonScript --yes 2>&1 | Tee-Object -FilePath $outputFile
    
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host "PROCESO COMPLETADO" -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Resultados guardados en: $outputFile" -ForegroundColor Gray
    Write-Host ""
    
    # Mostrar resumen final si existe
    if (Test-Path $outputFile) {
        Write-Host "=== RESUMEN FINAL ===" -ForegroundColor Cyan
        Get-Content $outputFile | Select-String -Pattern "RESUMEN|Exitosos|Fallidos|Total" | Select-Object -Last 10
    }
    
} catch {
    Write-Host ""
    Write-Host "[ERROR] Error durante la ejecución: $_" -ForegroundColor Red
    Write-Host "Revisa el archivo de salida: $outputFile" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Para ver el progreso completo, ejecuta:" -ForegroundColor Gray
Write-Host "  Get-Content `"$outputFile`" -Tail 50" -ForegroundColor White
Write-Host ""
