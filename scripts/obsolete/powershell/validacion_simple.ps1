# scripts/powershell/validacion_simple.ps1
# Script simple de validacion para las soluciones integrales

param(
    [string]$BaseUrl = "https://pagos-f2qf.onrender.com"
)

Write-Host "VALIDACION DE SOLUCIONES INTEGRALES" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Funcion para hacer requests HTTP
function Invoke-TestRequest {
    param(
        [string]$Url,
        [string]$Method = "GET"
    )
    
    try {
        $response = Invoke-RestMethod -Uri $Url -Method $Method -TimeoutSec 10
        return @{
            Success = $true
            Data = $response
        }
    }
    catch {
        return @{
            Success = $false
            Error = $_.Exception.Message
        }
    }
}

# ============================================
# VALIDACION DE DESPLIEGUE
# ============================================
Write-Host "1. VALIDACION DE DESPLIEGUE" -ForegroundColor Yellow
Write-Host "============================" -ForegroundColor Yellow

Write-Host "   Verificando salud del servidor..." -ForegroundColor Gray
$healthResult = Invoke-TestRequest -Url "$BaseUrl/api/v1/health"

if ($healthResult.Success) {
    Write-Host "   ✅ Servidor saludable: $($healthResult.Data.status)" -ForegroundColor Green
} else {
    Write-Host "   ❌ Servidor no disponible: $($healthResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# VALIDACION DE HERRAMIENTAS NUEVAS
# ============================================
Write-Host "2. VALIDACION DE HERRAMIENTAS NUEVAS" -ForegroundColor Yellow
Write-Host "=====================================" -ForegroundColor Yellow

$totalTests = 0
$successfulTests = 0

# A. Analisis de Esquema
Write-Host "   A. Analisis de Esquema" -ForegroundColor Gray
$schemaTests = @(
    @{ Name = "Inconsistencias de Esquema"; Url = "/api/v1/schema/schema-inconsistencies" },
    @{ Name = "Fixes de Esquema"; Url = "/api/v1/schema/schema-fixes" },
    @{ Name = "Monitoreo de Esquema"; Url = "/api/v1/schema/schema-monitoring" }
)

foreach ($test in $schemaTests) {
    $totalTests++
    Write-Host "      Probando: $($test.Name)..." -ForegroundColor Gray
    $result = Invoke-TestRequest -Url "$BaseUrl$($test.Url)"
    
    if ($result.Success) {
        Write-Host "      ✅ $($test.Name): Funcionando" -ForegroundColor Green
        $successfulTests++
    } else {
        Write-Host "      ❌ $($test.Name): Error - $($result.Error)" -ForegroundColor Red
    }
}

Write-Host ""

# B. Monitor de Errores Criticos
Write-Host "   B. Monitor de Errores Criticos" -ForegroundColor Gray
$criticalErrorTests = @(
    @{ Name = "Analisis de Errores Criticos"; Url = "/api/v1/critical-errors/critical-error-analysis" },
    @{ Name = "Resumen de Errores Criticos"; Url = "/api/v1/critical-errors/critical-error-summary" }
)

foreach ($test in $criticalErrorTests) {
    $totalTests++
    Write-Host "      Probando: $($test.Name)..." -ForegroundColor Gray
    $result = Invoke-TestRequest -Url "$BaseUrl$($test.Url)"
    
    if ($result.Success) {
        Write-Host "      ✅ $($test.Name): Funcionando" -ForegroundColor Green
        $successfulTests++
    } else {
        Write-Host "      ❌ $($test.Name): Error - $($result.Error)" -ForegroundColor Red
    }
}

Write-Host ""

# C. Mediciones Estrategicas
Write-Host "   C. Mediciones Estrategicas" -ForegroundColor Gray
$measurementTests = @(
    @{ Name = "Salud de Despliegue"; Url = "/api/v1/measurements/deployment-health" },
    @{ Name = "Consistencia de Esquema"; Url = "/api/v1/measurements/schema-consistency" },
    @{ Name = "Estabilidad de Frontend"; Url = "/api/v1/measurements/frontend-stability" },
    @{ Name = "Rendimiento del Sistema"; Url = "/api/v1/measurements/system-performance" },
    @{ Name = "Resumen de Mediciones"; Url = "/api/v1/measurements/measurement-summary" }
)

foreach ($test in $measurementTests) {
    $totalTests++
    Write-Host "      Probando: $($test.Name)..." -ForegroundColor Gray
    $result = Invoke-TestRequest -Url "$BaseUrl$($test.Url)"
    
    if ($result.Success) {
        Write-Host "      ✅ $($test.Name): Funcionando" -ForegroundColor Green
        $successfulTests++
    } else {
        Write-Host "      ❌ $($test.Name): Error - $($result.Error)" -ForegroundColor Red
    }
}

Write-Host ""

# ============================================
# RESUMEN FINAL
# ============================================
Write-Host "RESUMEN FINAL DE VALIDACION" -ForegroundColor Yellow
Write-Host "============================" -ForegroundColor Yellow

$successRate = if ($totalTests -gt 0) { ($successfulTests / $totalTests) * 100 } else { 0 }

Write-Host "   Resultados:" -ForegroundColor Gray
Write-Host "      - Tests totales: $totalTests" -ForegroundColor Gray
Write-Host "      - Tests exitosos: $successfulTests" -ForegroundColor Gray
Write-Host "      - Tasa de exito: $([math]::Round($successRate, 1))%" -ForegroundColor Gray

if ($successRate -ge 90) {
    Write-Host "   🎉 ¡EXCELENTE! Soluciones integrales funcionando correctamente" -ForegroundColor Green
} elseif ($successRate -ge 70) {
    Write-Host "   ✅ BUENO! La mayoria de herramientas funcionan" -ForegroundColor Green
} elseif ($successRate -ge 50) {
    Write-Host "   ⚠️ REGULAR! Algunas herramientas funcionan" -ForegroundColor Yellow
} else {
    Write-Host "   ❌ PROBLEMATICO! Pocas herramientas funcionan" -ForegroundColor Red
}

Write-Host ""
Write-Host "VALIDACION COMPLETADA" -ForegroundColor Green
Write-Host "=====================" -ForegroundColor Green
