# scripts/powershell/validacion_completa_final.ps1
# Script de validación completa que combina todos los enfoques

param(
    [string]$BaseUrl = "https://pagos-f2qf.onrender.com",
    [switch]$WaitForDeploy = $false
)

Write-Host "🔍 VALIDACIÓN COMPLETA FINAL - TODOS LOS ENFOQUES" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# Función para verificar si el despliegue está listo
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

# Función para hacer requests HTTP
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

# Verificar si el despliegue está listo
if ($WaitForDeploy) {
    Write-Host "⏳ Esperando que el despliegue esté listo..." -ForegroundColor Yellow
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
        Write-Host "   ⚠️ Timeout esperando despliegue, continuando con validación..." -ForegroundColor Yellow
    }
}

Write-Host ""

# ============================================
# VALIDACIÓN COMPLETA DE TODOS LOS ENFOQUES
# ============================================

$allResults = @{}
$totalTests = 0
$successfulTests = 0

# 1. ENFOQUE FORENSE
Write-Host "1️⃣ ENFOQUE FORENSE: Análisis de Logs y Trazas" -ForegroundColor Yellow
Write-Host "=============================================" -ForegroundColor Yellow

$forensicTests = @(
    @{ Name = "Resumen Forense"; Url = "/api/v1/forensic/forensic-summary" },
    @{ Name = "Historial de Validación"; Url = "/api/v1/cross-validation/validation-history" }
)

foreach ($test in $forensicTests) {
    $totalTests++
    Write-Host "   🔍 Probando: $($test.Name)..." -ForegroundColor Gray
    $result = Invoke-TestRequest -Url "$BaseUrl$($test.Url)"
    
    if ($result.Success) {
        Write-Host "   ✅ $($test.Name): Funcionando" -ForegroundColor Green
        $successfulTests++
    } else {
        Write-Host "   ❌ $($test.Name): Error - $($result.Error)" -ForegroundColor Red
    }
}

Write-Host ""

# 2. ENFOQUE EXPERIMENTAL
Write-Host "2️⃣ ENFOQUE EXPERIMENTAL: Tests Controlados" -ForegroundColor Yellow
Write-Host "===========================================" -ForegroundColor Yellow

$experimentalTests = @(
    @{ Name = "Resumen Experimental"; Url = "/api/v1/experimental/experimental-summary" },
    @{ Name = "Tests de Conectividad"; Url = "/api/v1/network/test-connectivity"; Method = "POST" }
)

foreach ($test in $experimentalTests) {
    $totalTests++
    Write-Host "   🧪 Probando: $($test.Name)..." -ForegroundColor Gray
    $result = Invoke-TestRequest -Url "$BaseUrl$($test.Url)" -Method $test.Method
    
    if ($result.Success) {
        Write-Host "   ✅ $($test.Name): Funcionando" -ForegroundColor Green
        $successfulTests++
    } else {
        Write-Host "   ❌ $($test.Name): Error - $($result.Error)" -ForegroundColor Red
    }
}

Write-Host ""

# 3. ENFOQUE COMPARATIVO
Write-Host "3️⃣ ENFOQUE COMPARATIVO: Análisis Diferencial" -ForegroundColor Yellow
Write-Host "=============================================" -ForegroundColor Yellow

$comparativeTests = @(
    @{ Name = "Resumen Comparativo"; Url = "/api/v1/comparative/comparative-summary" },
    @{ Name = "Análisis Intermitente"; Url = "/api/v1/intermittent/intermittent-summary" }
)

foreach ($test in $comparativeTests) {
    $totalTests++
    Write-Host "   📊 Probando: $($test.Name)..." -ForegroundColor Gray
    $result = Invoke-TestRequest -Url "$BaseUrl$($test.Url)"
    
    if ($result.Success) {
        Write-Host "   ✅ $($test.Name): Funcionando" -ForegroundColor Green
        $successfulTests++
    } else {
        Write-Host "   ❌ $($test.Name): Error - $($result.Error)" -ForegroundColor Red
    }
}

Write-Host ""

# 4. ENFOQUE TEMPORAL
Write-Host "4️⃣ ENFOQUE TEMPORAL: Análisis de Timing" -ForegroundColor Yellow
Write-Host "=======================================" -ForegroundColor Yellow

$temporalTests = @(
    @{ Name = "Resumen Temporal"; Url = "/api/v1/temporal/temporal-summary" },
    @{ Name = "Sincronización de Reloj"; Url = "/api/v1/temporal/clock-synchronization" }
)

foreach ($test in $temporalTests) {
    $totalTests++
    Write-Host "   ⏰ Probando: $($test.Name)..." -ForegroundColor Gray
    $result = Invoke-TestRequest -Url "$BaseUrl$($test.Url)"
    
    if ($result.Success) {
        Write-Host "   ✅ $($test.Name): Funcionando" -ForegroundColor Green
        $successfulTests++
    } else {
        Write-Host "   ❌ $($test.Name): Error - $($result.Error)" -ForegroundColor Red
    }
}

Write-Host ""

# 5. ENFOQUE ARQUITECTURAL
Write-Host "5️⃣ ENFOQUE ARQUITECTURAL: Análisis de Componentes" -ForegroundColor Yellow
Write-Host "=================================================" -ForegroundColor Yellow

$architecturalTests = @(
    @{ Name = "Resumen Arquitectural"; Url = "/api/v1/architectural/architectural-summary" },
    @{ Name = "Salud de Componentes"; Url = "/api/v1/architectural/all-components-health" }
)

foreach ($test in $architecturalTests) {
    $totalTests++
    Write-Host "   🏗️ Probando: $($test.Name)..." -ForegroundColor Gray
    $result = Invoke-TestRequest -Url "$BaseUrl$($test.Url)"
    
    if ($result.Success) {
        Write-Host "   ✅ $($test.Name): Funcionando" -ForegroundColor Green
        $successfulTests++
    } else {
        Write-Host "   ❌ $($test.Name): Error - $($result.Error)" -ForegroundColor Red
    }
}

Write-Host ""

# 6. ENFOQUE INTERMITENTE (NUEVO)
Write-Host "6️⃣ ENFOQUE INTERMITENTE: Análisis de Fallos Intermitentes" -ForegroundColor Yellow
Write-Host "=======================================================" -ForegroundColor Yellow

$intermittentTests = @(
    @{ Name = "Patrones Intermitentes"; Url = "/api/v1/intermittent/intermittent-patterns" },
    @{ Name = "Monitoreo Tiempo Real"; Url = "/api/v1/realtime/real-time-status" }
)

foreach ($test in $intermittentTests) {
    $totalTests++
    Write-Host "   🔄 Probando: $($test.Name)..." -ForegroundColor Gray
    $result = Invoke-TestRequest -Url "$BaseUrl$($test.Url)"
    
    if ($result.Success) {
        Write-Host "   ✅ $($test.Name): Funcionando" -ForegroundColor Green
        $successfulTests++
    } else {
        Write-Host "   ❌ $($test.Name): Error - $($result.Error)" -ForegroundColor Red
    }
}

Write-Host ""

# ============================================
# RESUMEN FINAL
# ============================================
Write-Host "📊 RESUMEN FINAL DE VALIDACIÓN" -ForegroundColor Yellow
Write-Host "=============================" -ForegroundColor Yellow

$successRate = if ($totalTests -gt 0) { ($successfulTests / $totalTests) * 100 } else { 0 }

Write-Host "   🎯 Resultados:" -ForegroundColor Gray
Write-Host "      - Tests totales: $totalTests" -ForegroundColor Gray
Write-Host "      - Tests exitosos: $successfulTests" -ForegroundColor Gray
Write-Host "      - Tasa de éxito: $([math]::Round($successRate, 1))%" -ForegroundColor Gray

if ($successRate -ge 90) {
    Write-Host "   🎉 ¡EXCELENTE! Todos los sistemas funcionan correctamente" -ForegroundColor Green
    Write-Host "   ✅ Sistema de validación de causa raíz completamente operativo" -ForegroundColor Green
} elseif ($successRate -ge 70) {
    Write-Host "   ✅ BUENO! La mayoría de sistemas funcionan" -ForegroundColor Green
    Write-Host "   ⚠️ Algunos sistemas requieren atención" -ForegroundColor Yellow
} elseif ($successRate -ge 50) {
    Write-Host "   ⚠️ REGULAR! Algunos sistemas funcionan" -ForegroundColor Yellow
    Write-Host "   🔧 Varios sistemas requieren revisión" -ForegroundColor Yellow
} else {
    Write-Host "   ❌ PROBLEMÁTICO! Pocos sistemas funcionan" -ForegroundColor Red
    Write-Host "   🚨 Revisar configuración del servidor" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎯 ESTRATEGIA FINAL RECOMENDADA:" -ForegroundColor Cyan
Write-Host "   1. Activar monitoreo intermitente durante uso normal" -ForegroundColor White
Write-Host "   2. Cuando ocurra fallo 401, analizar inmediatamente" -ForegroundColor White
Write-Host "   3. Usar análisis forense para reconstruir secuencia" -ForegroundColor White
Write-Host "   4. Comparar con momentos de éxito usando análisis comparativo" -ForegroundColor White
Write-Host "   5. Verificar timing y sincronización" -ForegroundColor White
Write-Host "   6. Analizar salud de componentes arquitecturales" -ForegroundColor White

Write-Host ""
Write-Host "🚀 VALIDACIÓN COMPLETA FINALIZADA" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
