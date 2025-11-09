# Script de PowerShell para verificar y ajustar el dashboard
# Uso: .\scripts\verificar_dashboard.ps1

param(
    [switch]$Execute,
    [switch]$SkipDiagnostico,
    [switch]$SkipAjustes,
    [switch]$SkipTest
)

$ErrorActionPreference = "Stop"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "🔍 VERIFICACIÓN Y AJUSTE DEL DASHBOARD" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "backend")) {
    Write-Host "❌ Error: No se encontró el directorio 'backend'" -ForegroundColor Red
    Write-Host "   Ejecuta este script desde la raíz del proyecto" -ForegroundColor Yellow
    exit 1
}

# Cambiar al directorio backend
Push-Location backend

try {
    # Verificar que Python esté disponible
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Error: Python no está disponible" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Python encontrado: $pythonVersion" -ForegroundColor Green
    Write-Host ""

    # Paso 1: Diagnóstico
    if (-not $SkipDiagnostico) {
        Write-Host "📋 PASO 1: Ejecutando diagnóstico..." -ForegroundColor Yellow
        Write-Host ""
        python scripts\diagnostico_dashboard_rangos.py
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⚠️  El diagnóstico tuvo algunos problemas" -ForegroundColor Yellow
        }
        Write-Host ""
        Write-Host "================================================================================" -ForegroundColor Cyan
        Write-Host ""
    }

    # Paso 2: Ajustes
    if (-not $SkipAjustes) {
        if ($Execute) {
            Write-Host "🔧 PASO 2: Ejecutando ajustes de fechas..." -ForegroundColor Yellow
            Write-Host ""
            python scripts\ajustar_fechas_prestamos.py --execute
            if ($LASTEXITCODE -ne 0) {
                Write-Host "⚠️  Los ajustes tuvieron algunos problemas" -ForegroundColor Yellow
            }
        } else {
            Write-Host "🔧 PASO 2: Revisando ajustes necesarios (modo dry-run)..." -ForegroundColor Yellow
            Write-Host ""
            python scripts\ajustar_fechas_prestamos.py
            Write-Host ""
            Write-Host "💡 Para ejecutar los ajustes, usa: -Execute" -ForegroundColor Cyan
        }
        Write-Host ""
        Write-Host "================================================================================" -ForegroundColor Cyan
        Write-Host ""
    }

    # Paso 3: Prueba del endpoint
    if (-not $SkipTest) {
        Write-Host "🧪 PASO 3: Probando endpoint..." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "⚠️  Nota: Asegúrate de que el backend esté corriendo" -ForegroundColor Yellow
        Write-Host ""
        python scripts\test_endpoint_rangos.py
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⚠️  La prueba del endpoint tuvo algunos problemas" -ForegroundColor Yellow
            Write-Host "   Verifica que el backend esté corriendo en http://localhost:8000" -ForegroundColor Yellow
        }
        Write-Host ""
        Write-Host "================================================================================" -ForegroundColor Cyan
        Write-Host ""
    }

    Write-Host "✅ Verificación completada" -ForegroundColor Green
    Write-Host ""
    Write-Host "📝 Próximos pasos:" -ForegroundColor Cyan
    Write-Host "   1. Revisar los resultados del diagnóstico" -ForegroundColor White
    Write-Host "   2. Si hay problemas, ejecutar ajustes con -Execute" -ForegroundColor White
    Write-Host "   3. Verificar que el dashboard muestre los datos correctamente" -ForegroundColor White
    Write-Host ""

} catch {
    Write-Host "❌ Error durante la ejecución: $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

