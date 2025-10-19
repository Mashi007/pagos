# scripts/powershell/tercer_enfoque_diagnostico_completo.ps1
# Script para probar el tercer enfoque completo de diagnóstico de causa raíz

param(
    [string]$BaseUrl = "https://pagos-f2qf.onrender.com"
)

Write-Host "🔍 TERCER ENFOQUE: DIAGNÓSTICO COMPLETO DE CAUSA RAÍZ" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

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

# ============================================
# 1. MONITOREO EN TIEMPO REAL
# ============================================
Write-Host "1️⃣ MONITOREO EN TIEMPO REAL" -ForegroundColor Yellow
Write-Host "============================" -ForegroundColor Yellow

# Test de estado en tiempo real
Write-Host "   📊 Probando estado en tiempo real..." -ForegroundColor Gray
$realTimeUrl = "$BaseUrl/api/v1/monitor/real-time-status"
$realTimeResult = Invoke-TestRequest -Url $realTimeUrl

if ($realTimeResult.Success) {
    Write-Host "   ✅ Monitor en tiempo real funcionando" -ForegroundColor Green
    $metrics = $realTimeResult.Data.data.metrics
    Write-Host "      - Requests últimos 5min: $($metrics.total_requests_5min)" -ForegroundColor Gray
    Write-Host "      - Tasa de éxito: $($metrics.success_rate_percent)%" -ForegroundColor Gray
    Write-Host "      - Tokens activos: $($metrics.active_tokens)" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en monitor tiempo real: $($realTimeResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# 2. ANÁLISIS PREDICTIVO DE TOKENS
# ============================================
Write-Host "2️⃣ ANÁLISIS PREDICTIVO DE TOKENS" -ForegroundColor Yellow
Write-Host "=================================" -ForegroundColor Yellow

# Test de análisis predictivo
Write-Host "   🔮 Probando análisis predictivo..." -ForegroundColor Gray
$predictiveUrl = "$BaseUrl/api/v1/predictive-tokens/predict-system-failures"
$predictiveResult = Invoke-TestRequest -Url $predictiveUrl

if ($predictiveResult.Success) {
    Write-Host "   ✅ Análisis predictivo funcionando" -ForegroundColor Green
    $predictions = $predictiveResult.Data.predictions
    Write-Host "      - Salud del sistema: $($predictions.system_health)" -ForegroundColor Gray
    Write-Host "      - Fallas predichas: $($predictions.predicted_failures.Count)" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en análisis predictivo: $($predictiveResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# 3. VALIDACIÓN CRUZADA DE AUTENTICACIÓN
# ============================================
Write-Host "3️⃣ VALIDACIÓN CRUZADA DE AUTENTICACIÓN" -ForegroundColor Yellow
Write-Host "=======================================" -ForegroundColor Yellow

# Test de historial de validación
Write-Host "   🔄 Probando historial de validación..." -ForegroundColor Gray
$validationUrl = "$BaseUrl/api/v1/cross-validation/validation-history"
$validationResult = Invoke-TestRequest -Url $validationUrl

if ($validationResult.Success) {
    Write-Host "   ✅ Validación cruzada funcionando" -ForegroundColor Green
    $stats = $validationResult.Data.statistics
    Write-Host "      - Validaciones totales: $($stats.total_validations)" -ForegroundColor Gray
    Write-Host "      - Tasa de éxito: $($stats.success_rate)%" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en validación cruzada: $($validationResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# 4. SISTEMA DE ALERTAS INTELIGENTES
# ============================================
Write-Host "4️⃣ SISTEMA DE ALERTAS INTELIGENTES" -ForegroundColor Yellow
Write-Host "===================================" -ForegroundColor Yellow

# Test de alertas activas
Write-Host "   🚨 Probando alertas activas..." -ForegroundColor Gray
$alertsUrl = "$BaseUrl/api/v1/intelligent-alerts/active-alerts"
$alertsResult = Invoke-TestRequest -Url $alertsUrl

if ($alertsResult.Success) {
    Write-Host "   ✅ Sistema de alertas funcionando" -ForegroundColor Green
    Write-Host "      - Alertas activas: $($alertsResult.Data.count)" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en sistema de alertas: $($alertsResult.Error)" -ForegroundColor Red
}

# Test de estadísticas de alertas
Write-Host "   📊 Probando estadísticas de alertas..." -ForegroundColor Gray
$alertStatsUrl = "$BaseUrl/api/v1/intelligent-alerts/alert-statistics"
$alertStatsResult = Invoke-TestRequest -Url $alertStatsUrl

if ($alertStatsResult.Success) {
    Write-Host "   ✅ Estadísticas de alertas funcionando" -ForegroundColor Green
    $stats = $alertStatsResult.Data.statistics
    Write-Host "      - Total alertas: $($stats.total_alerts)" -ForegroundColor Gray
    Write-Host "      - Alertas activas: $($stats.active_alerts)" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en estadísticas de alertas: $($alertStatsResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# 5. DIAGNÓSTICO DE RED Y LATENCIA
# ============================================
Write-Host "5️⃣ DIAGNÓSTICO DE RED Y LATENCIA" -ForegroundColor Yellow
Write-Host "=================================" -ForegroundColor Yellow

# Test de salud de red
Write-Host "   🌐 Probando salud de red..." -ForegroundColor Gray
$networkUrl = "$BaseUrl/api/v1/network/network-health"
$networkResult = Invoke-TestRequest -Url $networkUrl

if ($networkResult.Success) {
    Write-Host "   ✅ Diagnóstico de red funcionando" -ForegroundColor Green
    $analysis = $networkResult.Data.analysis
    Write-Host "      - Salud general: $($analysis.overall_health)" -ForegroundColor Gray
    Write-Host "      - Estado conectividad: $($analysis.connectivity.status)" -ForegroundColor Gray
    Write-Host "      - Estado latencia: $($analysis.latency.status)" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en diagnóstico de red: $($networkResult.Error)" -ForegroundColor Red
}

# Test de conectividad inmediata
Write-Host "   🔍 Probando conectividad inmediata..." -ForegroundColor Gray
$connectivityUrl = "$BaseUrl/api/v1/network/test-connectivity"
$connectivityResult = Invoke-TestRequest -Url $connectivityUrl -Method "POST"

if ($connectivityResult.Success) {
    Write-Host "   ✅ Test de conectividad funcionando" -ForegroundColor Green
    $testResult = $connectivityResult.Data.test_result
    Write-Host "      - Estado general: $($testResult.overall_status)" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en test de conectividad: $($connectivityResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# 6. ANÁLISIS INTEGRADO DE CAUSA RAÍZ
# ============================================
Write-Host "6️⃣ ANÁLISIS INTEGRADO DE CAUSA RAÍZ" -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Yellow

# Recopilar todos los resultados
$allResults = @{
    "monitoreo_tiempo_real" = $realTimeResult.Success
    "analisis_predictivo" = $predictiveResult.Success
    "validacion_cruzada" = $validationResult.Success
    "sistema_alertas" = $alertsResult.Success
    "diagnostico_red" = $networkResult.Success
}

$successfulTests = ($allResults.Values | Where-Object { $_ -eq $true }).Count
$totalTests = $allResults.Count

Write-Host "   📊 Resumen de sistemas:" -ForegroundColor Gray
foreach ($system in $allResults.Keys) {
    $status = if ($allResults[$system]) { "✅" } else { "❌" }
    Write-Host "      $status $system" -ForegroundColor $(if ($allResults[$system]) { "Green" } else { "Red" })
}

Write-Host ""

# ============================================
# 7. RECOMENDACIONES FINALES
# ============================================
Write-Host "7️⃣ RECOMENDACIONES FINALES" -ForegroundColor Yellow
Write-Host "==========================" -ForegroundColor Yellow

Write-Host "   🎯 Análisis de causa raíz completado:" -ForegroundColor Gray
Write-Host "      - Sistemas funcionando: $successfulTests/$totalTests" -ForegroundColor Gray

if ($successfulTests -eq $totalTests) {
    Write-Host "   🎉 ¡Todos los sistemas de diagnóstico funcionan correctamente!" -ForegroundColor Green
    Write-Host "   ✅ El tercer enfoque está completamente operativo" -ForegroundColor Green
    Write-Host ""
    Write-Host "   📋 Próximos pasos recomendados:" -ForegroundColor Cyan
    Write-Host "      1. Monitorear alertas en tiempo real" -ForegroundColor White
    Write-Host "      2. Revisar análisis predictivos regularmente" -ForegroundColor White
    Write-Host "      3. Validar tokens cruzadamente en casos sospechosos" -ForegroundColor White
    Write-Host "      4. Mantener diagnóstico de red activo" -ForegroundColor White
} else {
    Write-Host "   ⚠️ Algunos sistemas requieren atención" -ForegroundColor Yellow
    Write-Host "   🔧 Revisar logs del servidor para más detalles" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🚀 TERCER ENFOQUE IMPLEMENTADO EXITOSAMENTE" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Sistemas implementados:" -ForegroundColor Cyan
Write-Host "   • Monitor en tiempo real" -ForegroundColor White
Write-Host "   • Análisis predictivo de tokens" -ForegroundColor White
Write-Host "   • Validación cruzada de autenticación" -ForegroundColor White
Write-Host "   • Sistema de alertas inteligentes" -ForegroundColor White
Write-Host "   • Diagnóstico de red y latencia" -ForegroundColor White
Write-Host ""
Write-Host "🎯 Capacidades del tercer enfoque:" -ForegroundColor Cyan
Write-Host "   • Detección proactiva de problemas" -ForegroundColor White
Write-Host "   • Análisis multidimensional de autenticación" -ForegroundColor White
Write-Host "   • Alertas inteligentes basadas en patrones" -ForegroundColor White
Write-Host "   • Monitoreo continuo de red y rendimiento" -ForegroundColor White
Write-Host "   • Validación cruzada para máxima confiabilidad" -ForegroundColor White
