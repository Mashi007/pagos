# Script para ejecutar flake8 en el proyecto
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Ejecutando Flake8 - Analisis de Codigo Python" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Cambiar al directorio del proyecto
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Join-Path $scriptPath ".."
Set-Location $projectRoot

# Verificar si flake8 está instalado
try {
    $flake8Version = python -m flake8 --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Flake8 no encontrado"
    }
} catch {
    Write-Host "Flake8 no está instalado. Instalando..." -ForegroundColor Yellow
    python -m pip install flake8 flake8-docstrings flake8-bugbear flake8-import-order mccabe
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error al instalar flake8" -ForegroundColor Red
        Read-Host "Presiona Enter para salir"
        exit 1
    }
}

Write-Host ""
Write-Host "Analizando codigo Python..." -ForegroundColor Green
Write-Host ""

# Ejecutar flake8 en el directorio app
python -m flake8 app --config=.flake8 --statistics --count

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Analisis completado" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Read-Host "Presiona Enter para salir"

