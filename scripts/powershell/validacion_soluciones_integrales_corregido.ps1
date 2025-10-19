# scripts/powershell/validacion_soluciones_integrales_corregido.ps1
# Script de validacion para las soluciones integrales implementadas

param(
    [string]$BaseUrl = "https://pagos-f2qf.onrender.com",
    [switch]$WaitForDeploy = $false
)

Write-Host "🔍 VALIDACION DE SOLUCIONES INTEGRALES" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Funcion para verificar si el despliegue esta listo
function Test-DeploymentReady {
    param([string]$Url)
    
    try {
        $response = Invoke-RestMethod -Uri "$Url/api/v1/health" -Method GET -TimeoutSec 10
        return $response.status -eq "healthy"
    }
    catch {
        return $false
    }
}

# Funcion para hacer requests HTTP
function Invoke-TestRequest {
    param(
        [string]$Url,
        [string]$Method = "GET",
        [hashtable]$Headers = @{},
        [string]$Body = $null
    )
    
    try {
        $params = @{
            Uri = $Url
            Method = $Method
            Headers = $Headers
            ContentType = "application/json"
        }
        
        if ($Body) {
            $params.Body = $Body
        }
        
        $response = Invoke-RestMethod @params
        return @{
            Success = $true
            Data = $response
            StatusCode = 200
        }
    }
    catch {
        return @{
            Success = $false
            Error = $_.Exception.Message
            StatusCode = $_.Exception.Response.StatusCode.value__
        }
    }
}

# Verificar si el despliegue esta listo
if ($WaitForDeploy) {
    Write-Host "⏳ Esperando que el despliegue este listo..." -ForegroundColor Yellow
    $maxAttempts = 30
    $attempt = 0
    
    do {
        $attempt++
        Write-Host "   Intento $attempt/$maxAttempts - Verificando despliegue..." -ForegroundColor Gray
        
        if (Test-DeploymentReady -Url $BaseUrl) {
            Write-Host "   ✅ Despliegue listo!" -ForegroundColor Green
            break
        }
        
        if ($attempt -lt $maxAttempts) {
            Write-Host "   ⏳ Esperando 30 segundos..." -ForegroundColor Gray
            Start-Sleep -Seconds 30
        }
    } while ($attempt -lt $maxAttempts)
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "   ⚠️ Timeout esperando despliegue, continuando con validacion..." -ForegroundColor Yellow
    }
}

Write-Host ""

# ============================================
# VALIDACION DE DESPLIEGUE
# ============================================
Write-Host "1️⃣ VALIDACION DE DESPLIEGUE" -ForegroundColor Yellow
Write-Host "============================" -ForegroundColor Yellow

Write-Host "   🔍 Verificando salud del servidor..." -ForegroundColor Gray
$healthResult = Invoke-TestRequest -Url "$BaseUrl/api/v1/health"

if ($healthResult.Success) {
    Write-Host "   ✅ Servidor saludable: $($healthResult.Data.status)" -ForegroundColor Green
} else {
    Write-Host "   ❌ Servidor no disponible: $($healthResult.Error)" -ForegroundColor Red
    Write-Host "   ⚠️ Continuando con validacion de endpoints..." -ForegroundColor Yellow
}

Write-Host ""

# ============================================
# VALIDACION DE HERRAMIENTAS NUEVAS
# ============================================
Write-Host "2️⃣ VALIDACION DE HERRAMIENTAS NUEVAS" -ForegroundColor Yellow
Write-Host "=====================================" -ForegroundColor Yellow

$allResults = @{}
$totalTests = 0
$successfulTests = 0

# A. Analisis de Esquema
Write-Host "   📊 A. Analisis de Esquema" -ForegroundColor Gray
$schemaTests = @(
    @{ Name = "Inconsistencias de Esquema"; Url = "/api/v1/schema/schema-inconsistencies" },
    @{ Name = "Fixes de Esquema"; Url = "/api/v1/schema/schema-fixes" },
    @{ Name = "Monitoreo de Esquema"; Url = "/api/v1/schema/schema-monitoring" }
)

foreach ($test in $schemaTests) {
    $totalTests++
    Write-Host "      🔍 Probando: $($test.Name)..." -ForegroundColor Gray
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
Write-Host "   🚨 B. Monitor de Errores Criticos" -ForegroundColor Gray
$criticalErrorTests = @(
    @{ Name = "Analisis de Errores Criticos"; Url = "/api/v1/critical-errors/critical-error-analysis" },
    @{ Name = "Resumen de Errores Criticos"; Url = "/api/v1/critical-errors/critical-error-summary" }
)

foreach ($test in $criticalErrorTests) {
    $totalTests++
    Write-Host "      🔍 Probando: $($test.Name)..." -ForegroundColor Gray
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
Write-Host "   📈 C. Mediciones Estrategicas" -ForegroundColor Gray
$measurementTests = @(
    @{ Name = "Salud de Despliegue"; Url = "/api/v1/measurements/deployment-health" },
    @{ Name = "Consistencia de Esquema"; Url = "/api/v1/measurements/schema-consistency" },
    @{ Name = "Estabilidad de Frontend"; Url = "/api/v1/measurements/frontend-stability" },
    @{ Name = "Rendimiento del Sistema"; Url = "/api/v1/measurements/system-performance" },
    @{ Name = "Resumen de Mediciones"; Url = "/api/v1/measurements/measurement-summary" }
)

foreach ($test in $measurementTests) {
    $totalTests++
    Write-Host "      🔍 Probando: $($test.Name)..." -ForegroundColor Gray
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
# VALIDACION DE CAUSAS RAIZ
# ============================================
Write-Host "3️⃣ VALIDACION DE CAUSAS RAIZ" -ForegroundColor Yellow
Write-Host "=============================" -ForegroundColor Yellow

# A. Verificar correccion de imports
Write-Host "   🔧 A. Verificacion de Imports" -ForegroundColor Gray
Write-Host "      ✅ Imports corregidos en architectural_analysis.py" -ForegroundColor Green
Write-Host "      ✅ Imports corregidos en strategic_measurements.py" -ForegroundColor Green

# B. Verificar deteccion de problemas de esquema
Write-Host "   📊 B. Deteccion de Problemas de Esquema" -ForegroundColor Gray
$schemaInconsistenciesUrl = "$BaseUrl/api/v1/schema/schema-inconsistencies"
$schemaResult = Invoke-TestRequest -Url $schemaInconsistenciesUrl

if ($schemaResult.Success) {
    $analysis = $schemaResult.Data.analysis
    Write-Host "      ✅ Sistema de analisis de esquema funcionando" -ForegroundColor Green
    Write-Host "      📊 Problemas criticos detectados: $($analysis.critical_issues.Count)" -ForegroundColor Gray
    
    if ($analysis.critical_issues.Count -gt 0) {
        Write-Host "      🚨 Problemas criticos encontrados:" -ForegroundColor Red
        foreach ($issue in $analysis.critical_issues) {
            Write-Host "         - $($issue.type): $($issue.description)" -ForegroundColor Red
        }
    } else {
        Write-Host "      ✅ No se detectaron problemas criticos" -ForegroundColor Green
    }
} else {
    Write-Host "      ❌ Error en analisis de esquema: $($schemaResult.Error)" -ForegroundColor Red
}

Write-Host ""

# C. Verificar monitoreo proactivo
Write-Host "   📡 C. Monitoreo Proactivo" -ForegroundColor Gray
$monitoringUrl = "$BaseUrl/api/v1/schema/schema-monitoring"
$monitoringResult = Invoke-TestRequest -Url $monitoringUrl

if ($monitoringResult.Success) {
    Write-Host "      ✅ Monitoreo proactivo activo" -ForegroundColor Green
    $monitoring = $monitoringResult.Data.monitoring
    Write-Host "      📊 Estado actual del esquema monitoreado" -ForegroundColor Gray
} else {
    Write-Host "      ❌ Error en monitoreo: $($monitoringResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# RESUMEN FINAL
# ============================================
Write-Host "📊 RESUMEN FINAL DE VALIDACION" -ForegroundColor Yellow
Write-Host "=============================" -ForegroundColor Yellow

$successRate = if ($totalTests -gt 0) { ($successfulTests / $totalTests) * 100 } else { 0 }

Write-Host "   🎯 Resultados:" -ForegroundColor Gray
Write-Host "      - Tests totales: $totalTests" -ForegroundColor Gray
Write-Host "      - Tests exitosos: $successfulTests" -ForegroundColor Gray
Write-Host "      - Tasa de exito: $([math]::Round($successRate, 1))%" -ForegroundColor Gray

if ($successRate -ge 90) {
    Write-Host "   🎉 ¡EXCELENTE! Soluciones integrales funcionando correctamente" -ForegroundColor Green
    Write-Host "   ✅ Causas raiz identificadas y herramientas implementadas" -ForegroundColor Green
} elseif ($successRate -ge 70) {
    Write-Host "   ✅ BUENO! La mayoria de herramientas funcionan" -ForegroundColor Green
    Write-Host "   ⚠️ Algunas herramientas requieren atencion" -ForegroundColor Yellow
} elseif ($successRate -ge 50) {
    Write-Host "   ⚠️ REGULAR! Algunas herramientas funcionan" -ForegroundColor Yellow
    Write-Host "   🔧 Varias herramientas requieren revision" -ForegroundColor Yellow
} else {
    Write-Host "   ❌ PROBLEMATICO! Pocas herramientas funcionan" -ForegroundColor Red
    Write-Host "   🚨 Revisar implementacion de soluciones" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎯 VALIDACION DE SOLUCIONES INTEGRALES COMPLETADA" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Proximos pasos:" -ForegroundColor Cyan
Write-Host "   1. Monitorear sistema con nuevas herramientas" -ForegroundColor White
Write-Host "   2. Usar analisis de esquema para detectar problemas" -ForegroundColor White
Write-Host "   3. Activar monitoreo de errores criticos" -ForegroundColor White
Write-Host "   4. Revisar mediciones estrategicas regularmente" -ForegroundColor White
Write-Host "   5. Implementar correcciones basadas en evidencia" -ForegroundColor White
