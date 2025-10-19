# scripts/powershell/validacion_causa_raiz_completa.ps1
# Script para validar causa raíz usando los 5 enfoques distintos

param(
    [string]$BaseUrl = "https://pagos-f2qf.onrender.com",
    [string]$TestToken = $null
)

Write-Host "🔍 VALIDACIÓN COMPLETA DE CAUSA RAÍZ - 5 ENFOQUES DISTINTOS" -ForegroundColor Cyan
Write-Host "=============================================================" -ForegroundColor Cyan
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
# 1. ENFOQUE FORENSE: ANÁLISIS DE LOGS Y TRAZAS
# ============================================
Write-Host "1️⃣ ENFOQUE FORENSE: ANÁLISIS DE LOGS Y TRAZAS" -ForegroundColor Yellow
Write-Host "=============================================" -ForegroundColor Yellow

# Test de resumen forense
Write-Host "   🔍 Probando análisis forense..." -ForegroundColor Gray
$forensicUrl = "$BaseUrl/api/v1/forensic/forensic-summary"
$forensicResult = Invoke-TestRequest -Url $forensicUrl

if ($forensicResult.Success) {
    Write-Host "   ✅ Sistema forense funcionando" -ForegroundColor Green
    $summary = $forensicResult.Data.summary
    Write-Host "      - Eventos últimas 24h: $($summary.summary.total_events_24h)" -ForegroundColor Gray
    Write-Host "      - Fallos últimas 24h: $($summary.summary.total_failures_24h)" -ForegroundColor Gray
    Write-Host "      - Sesiones activas: $($summary.summary.active_trace_sessions)" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en análisis forense: $($forensicResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# 2. ENFOQUE EXPERIMENTAL: TESTS CONTROLADOS
# ============================================
Write-Host "2️⃣ ENFOQUE EXPERIMENTAL: TESTS CONTROLADOS" -ForegroundColor Yellow
Write-Host "===========================================" -ForegroundColor Yellow

# Test de resumen experimental
Write-Host "   🧪 Probando sistema experimental..." -ForegroundColor Gray
$experimentalUrl = "$BaseUrl/api/v1/experimental/experimental-summary"
$experimentalResult = Invoke-TestRequest -Url $experimentalUrl

if ($experimentalResult.Success) {
    Write-Host "   ✅ Sistema experimental funcionando" -ForegroundColor Green
    $summary = $experimentalResult.Data.summary
    Write-Host "      - Escenarios totales: $($summary.summary.total_scenarios)" -ForegroundColor Gray
    Write-Host "      - Escenarios completados: $($summary.summary.completed_scenarios)" -ForegroundColor Gray
    Write-Host "      - Tests totales: $($summary.summary.total_tests)" -ForegroundColor Gray
    Write-Host "      - Tasa de éxito: $($summary.summary.overall_success_rate)%" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en sistema experimental: $($experimentalResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# 3. ENFOQUE COMPARATIVO: ANÁLISIS DIFERENCIAL
# ============================================
Write-Host "3️⃣ ENFOQUE COMPARATIVO: ANÁLISIS DIFERENCIAL" -ForegroundColor Yellow
Write-Host "=============================================" -ForegroundColor Yellow

# Test de resumen comparativo
Write-Host "   📊 Probando análisis comparativo..." -ForegroundColor Gray
$comparativeUrl = "$BaseUrl/api/v1/comparative/comparative-summary"
$comparativeResult = Invoke-TestRequest -Url $comparativeUrl

if ($comparativeResult.Success) {
    Write-Host "   ✅ Sistema comparativo funcionando" -ForegroundColor Green
    $summary = $comparativeResult.Data.summary
    Write-Host "      - Casos exitosos: $($summary.summary.successful_cases_count)" -ForegroundColor Gray
    Write-Host "      - Casos fallidos: $($summary.summary.failed_cases_count)" -ForegroundColor Gray
    Write-Host "      - Análisis realizados: $($summary.summary.total_analyses_performed)" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en análisis comparativo: $($comparativeResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# 4. ENFOQUE TEMPORAL: ANÁLISIS DE TIMING
# ============================================
Write-Host "4️⃣ ENFOQUE TEMPORAL: ANÁLISIS DE TIMING" -ForegroundColor Yellow
Write-Host "=======================================" -ForegroundColor Yellow

# Test de resumen temporal
Write-Host "   ⏰ Probando análisis temporal..." -ForegroundColor Gray
$temporalUrl = "$BaseUrl/api/v1/temporal/temporal-summary"
$temporalResult = Invoke-TestRequest -Url $temporalUrl

if ($temporalResult.Success) {
    Write-Host "   ✅ Sistema temporal funcionando" -ForegroundColor Green
    $summary = $temporalResult.Data.summary
    Write-Host "      - Eventos últimas 24h: $($summary.summary.total_events_24h)" -ForegroundColor Gray
    Write-Host "      - Duración promedio: $($summary.summary.avg_event_duration_ms)ms" -ForegroundColor Gray
    Write-Host "      - Estado sincronización: $($summary.summary.clock_sync_status)" -ForegroundColor Gray
    Write-Host "      - Problemas de sync: $($summary.summary.sync_issues_count)" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en análisis temporal: $($temporalResult.Error)" -ForegroundColor Red
}

# Test de sincronización de reloj
Write-Host "   🕐 Probando sincronización de reloj..." -ForegroundColor Gray
$clockSyncUrl = "$BaseUrl/api/v1/temporal/clock-synchronization"
$clockSyncResult = Invoke-TestRequest -Url $clockSyncUrl

if ($clockSyncResult.Success) {
    Write-Host "   ✅ Sincronización de reloj funcionando" -ForegroundColor Green
    $analysis = $clockSyncResult.Data.analysis
    Write-Host "      - Estado: $($analysis.clock_sync_status)" -ForegroundColor Gray
    Write-Host "      - Diferencias promedio: $($analysis.avg_time_diff)s" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en sincronización de reloj: $($clockSyncResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# 5. ENFOQUE ARQUITECTURAL: ANÁLISIS DE COMPONENTES
# ============================================
Write-Host "5️⃣ ENFOQUE ARQUITECTURAL: ANÁLISIS DE COMPONENTES" -ForegroundColor Yellow
Write-Host "=================================================" -ForegroundColor Yellow

# Test de resumen arquitectural
Write-Host "   🏗️ Probando análisis arquitectural..." -ForegroundColor Gray
$architecturalUrl = "$BaseUrl/api/v1/architectural/architectural-summary"
$architecturalResult = Invoke-TestRequest -Url $architecturalUrl

if ($architecturalResult.Success) {
    Write-Host "   ✅ Sistema arquitectural funcionando" -ForegroundColor Green
    $summary = $architecturalResult.Data.summary
    Write-Host "      - Componentes totales: $($summary.summary.total_components)" -ForegroundColor Gray
    Write-Host "      - Componentes saludables: $($summary.summary.healthy_components)" -ForegroundColor Gray
    Write-Host "      - Componentes degradados: $($summary.summary.degraded_components)" -ForegroundColor Gray
    Write-Host "      - Componentes pobres: $($summary.summary.poor_components)" -ForegroundColor Gray
    Write-Host "      - Salud general: $($summary.summary.overall_health_percentage)%" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en análisis arquitectural: $($architecturalResult.Error)" -ForegroundColor Red
}

# Test de salud de componentes específicos
Write-Host "   🔍 Probando salud de componentes específicos..." -ForegroundColor Gray
$components = @("jwt_handler", "database_layer", "authentication_middleware", "user_model", "api_endpoints")

foreach ($component in $components) {
    $componentUrl = "$BaseUrl/api/v1/architectural/component-health/$component"
    $componentResult = Invoke-TestRequest -Url $componentUrl
    
    if ($componentResult.Success) {
        $health = $componentResult.Data.component_health
        $status = $health.status
        $score = [math]::Round($health.overall_health_score * 100, 1)
        
        $color = switch ($status) {
            "excellent" { "Green" }
            "good" { "Green" }
            "degraded" { "Yellow" }
            "poor" { "Red" }
            default { "Gray" }
        }
        
        Write-Host "      ✅ $component`: $status ($score%)" -ForegroundColor $color
    } else {
        Write-Host "      ❌ $component`: Error - $($componentResult.Error)" -ForegroundColor Red
    }
}

Write-Host ""

# ============================================
# ANÁLISIS INTEGRADO DE CAUSA RAÍZ
# ============================================
Write-Host "🔍 ANÁLISIS INTEGRADO DE CAUSA RAÍZ" -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Yellow

# Recopilar todos los resultados
$allResults = @{
    "forensic_analysis" = $forensicResult.Success
    "experimental_tests" = $experimentalResult.Success
    "comparative_analysis" = $comparativeResult.Success
    "temporal_analysis" = $temporalResult.Success
    "architectural_analysis" = $architecturalResult.Success
}

$successfulApproaches = ($allResults.Values | Where-Object { $_ -eq $true }).Count
$totalApproaches = $allResults.Count

Write-Host "   📊 Resumen de enfoques:" -ForegroundColor Gray
foreach ($approach in $allResults.Keys) {
    $status = if ($allResults[$approach]) { "✅" } else { "❌" }
    Write-Host "      $status $approach" -ForegroundColor $(if ($allResults[$approach]) { "Green" } else { "Red" })
}

Write-Host ""

# ============================================
# EVIDENCIA DE CAUSA RAÍZ
# ============================================
Write-Host "🎯 EVIDENCIA DE CAUSA RAÍZ" -ForegroundColor Yellow
Write-Host "==========================" -ForegroundColor Yellow

Write-Host "   🔍 Análisis de evidencia:" -ForegroundColor Gray

# Evidencia forense
if ($forensicResult.Success) {
    $forensicData = $forensicResult.Data.summary
    if ($forensicData.summary.total_failures_24h -gt 0) {
        Write-Host "      🔴 EVIDENCIA FORENSE: $($forensicData.summary.total_failures_24h) fallos en 24h" -ForegroundColor Red
        Write-Host "         Patrones de fallo más comunes:" -ForegroundColor Gray
        foreach ($pattern in $forensicData.summary.failure_pattern_distribution.PSObject.Properties) {
            Write-Host "         - $($pattern.Name): $($pattern.Value)" -ForegroundColor Gray
        }
    } else {
        Write-Host "      ✅ EVIDENCIA FORENSE: No hay fallos recientes" -ForegroundColor Green
    }
}

# Evidencia temporal
if ($temporalResult.Success) {
    $temporalData = $temporalResult.Data.summary
    if ($temporalData.summary.sync_issues_count -gt 0) {
        Write-Host "      🔴 EVIDENCIA TEMPORAL: $($temporalData.summary.sync_issues_count) problemas de sincronización" -ForegroundColor Red
    } else {
        Write-Host "      ✅ EVIDENCIA TEMPORAL: Sincronización correcta" -ForegroundColor Green
    }
}

# Evidencia arquitectural
if ($architecturalResult.Success) {
    $architecturalData = $architecturalResult.Data.summary
    if ($architecturalData.summary.poor_components -gt 0) {
        Write-Host "      🔴 EVIDENCIA ARQUITECTURAL: $($architecturalData.summary.poor_components) componentes en estado pobre" -ForegroundColor Red
    } elseif ($architecturalData.summary.degraded_components -gt 0) {
        Write-Host "      🟡 EVIDENCIA ARQUITECTURAL: $($architecturalData.summary.degraded_components) componentes degradados" -ForegroundColor Yellow
    } else {
        Write-Host "      ✅ EVIDENCIA ARQUITECTURAL: Todos los componentes saludables" -ForegroundColor Green
    }
}

Write-Host ""

# ============================================
# RECOMENDACIONES FINALES
# ============================================
Write-Host "📋 RECOMENDACIONES FINALES" -ForegroundColor Yellow
Write-Host "==========================" -ForegroundColor Yellow

Write-Host "   🎯 Estado de validación de causa raíz:" -ForegroundColor Gray
Write-Host "      - Enfoques funcionando: $successfulApproaches/$totalApproaches" -ForegroundColor Gray

if ($successfulApproaches -eq $totalApproaches) {
    Write-Host "   🎉 ¡TODOS LOS ENFOQUES FUNCIONAN CORRECTAMENTE!" -ForegroundColor Green
    Write-Host "   ✅ Sistema de validación de causa raíz completamente operativo" -ForegroundColor Green
    Write-Host ""
    Write-Host "   📋 Próximos pasos recomendados:" -ForegroundColor Cyan
    Write-Host "      1. Ejecutar análisis forense en casos reales de fallo" -ForegroundColor White
    Write-Host "      2. Crear escenarios experimentales para reproducir problemas" -ForegroundColor White
    Write-Host "      3. Comparar casos exitosos vs fallidos sistemáticamente" -ForegroundColor White
    Write-Host "      4. Monitorear timing y sincronización continuamente" -ForegroundColor White
    Write-Host "      5. Verificar salud de componentes arquitecturales" -ForegroundColor White
    Write-Host ""
    Write-Host "   🔍 Para identificar causa raíz específica:" -ForegroundColor Cyan
    Write-Host "      • Usar análisis forense cuando ocurra un fallo 401" -ForegroundColor White
    Write-Host "      • Crear tests experimentales con tokens específicos" -ForegroundColor White
    Write-Host "      • Comparar logs de casos exitosos vs fallidos" -ForegroundColor White
    Write-Host "      • Verificar sincronización de reloj en el momento del fallo" -ForegroundColor White
    Write-Host "      • Analizar salud de componentes JWT y autenticación" -ForegroundColor White
} else {
    Write-Host "   ⚠️ Algunos enfoques requieren atención" -ForegroundColor Yellow
    Write-Host "   🔧 Revisar logs del servidor para más detalles" -ForegroundColor Yellow
    Write-Host "   📊 Solo $successfulApproaches de $totalApproaches enfoques están operativos" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🚀 VALIDACIÓN DE CAUSA RAÍZ COMPLETADA" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Sistemas de validación implementados:" -ForegroundColor Cyan
Write-Host "   • Análisis forense de logs y trazas" -ForegroundColor White
Write-Host "   • Tests experimentales controlados" -ForegroundColor White
Write-Host "   • Análisis comparativo diferencial" -ForegroundColor White
Write-Host "   • Análisis temporal de timing" -ForegroundColor White
Write-Host "   • Análisis arquitectural de componentes" -ForegroundColor White
Write-Host ""
Write-Host "🎯 Capacidades de validación:" -ForegroundColor Cyan
Write-Host "   • Reconstrucción completa de secuencias de fallo" -ForegroundColor White
Write-Host "   • Reproducción controlada de problemas" -ForegroundColor White
Write-Host "   • Comparación sistemática de casos exitosos vs fallidos" -ForegroundColor White
Write-Host "   • Detección de problemas de sincronización temporal" -ForegroundColor White
Write-Host "   • Identificación de componentes específicos que fallan" -ForegroundColor White
Write-Host ""
Write-Host "⚠️ IMPORTANTE: No implementar soluciones hasta tener evidencia clara de causa raíz" -ForegroundColor Red
Write-Host "🔍 Usar estos sistemas para recopilar evidencia antes de aplicar fixes" -ForegroundColor Red
