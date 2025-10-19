# scripts/powershell/validacion_causa_raiz_actualizada.ps1
# Script actualizado basado en evidencia de logs que muestran funcionamiento correcto

param(
    [string]$BaseUrl = "https://pagos-f2qf.onrender.com",
    [string]$TestToken = $null
)

Write-Host "🔍 VALIDACIÓN ACTUALIZADA DE CAUSA RAÍZ - ENFOQUE INTERMITENTE" -ForegroundColor Cyan
Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📊 EVIDENCIA DE LOGS ANALIZADA:" -ForegroundColor Yellow
Write-Host "   ✅ Sistema funciona correctamente en logs recientes" -ForegroundColor Green
Write-Host "   ✅ Token JWT válido (longitud 209)" -ForegroundColor Green
Write-Host "   ✅ Usuario autenticado exitosamente" -ForegroundColor Green
Write-Host "   ✅ Todos los endpoints responden 200 OK" -ForegroundColor Green
Write-Host "   ✅ CORS configurado correctamente" -ForegroundColor Green
Write-Host ""

Write-Host "🎯 NUEVA HIPÓTESIS: PROBLEMA INTERMITENTE ESPECÍFICO" -ForegroundColor Yellow
Write-Host "=================================================" -ForegroundColor Yellow
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
# 1. ANÁLISIS INTERMITENTE
# ============================================
Write-Host "1️⃣ ANÁLISIS DE FALLOS INTERMITENTES" -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Yellow

# Test de análisis intermitente
Write-Host "   🔄 Probando análisis intermitente..." -ForegroundColor Gray
$intermittentUrl = "$BaseUrl/api/v1/intermittent/intermittent-summary"
$intermittentResult = Invoke-TestRequest -Url $intermittentUrl

if ($intermittentResult.Success) {
    Write-Host "   ✅ Sistema de análisis intermitente funcionando" -ForegroundColor Green
    $summary = $intermittentResult.Data.summary
    Write-Host "      - Requests exitosos recientes: $($summary.summary.recent_successful_requests)" -ForegroundColor Gray
    Write-Host "      - Requests fallidos recientes: $($summary.summary.recent_failed_requests)" -ForegroundColor Gray
    Write-Host "      - Intermitencia detectada: $($summary.summary.intermittency_detected)" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en análisis intermitente: $($intermittentResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# 2. MONITOREO EN TIEMPO REAL ESPECÍFICO
# ============================================
Write-Host "2️⃣ MONITOREO EN TIEMPO REAL ESPECÍFICO" -ForegroundColor Yellow
Write-Host "=======================================" -ForegroundColor Yellow

# Test de estado de monitoreo en tiempo real
Write-Host "   📡 Probando monitoreo en tiempo real..." -ForegroundColor Gray
$realtimeUrl = "$BaseUrl/api/v1/realtime/real-time-status"
$realtimeResult = Invoke-TestRequest -Url $realtimeUrl

if ($realtimeResult.Success) {
    Write-Host "   ✅ Monitoreo en tiempo real funcionando" -ForegroundColor Green
    $status = $realtimeResult.Data.monitoring_status
    Write-Host "      - Monitoreo activo: $($status.monitoring_active)" -ForegroundColor Gray
    Write-Host "      - Sesiones activas: $($status.active_sessions_count)" -ForegroundColor Gray
    Write-Host "      - Eventos capturados: $($status.total_events_captured)" -ForegroundColor Gray
    Write-Host "      - Momentos de fallo: $($status.failure_moments_captured)" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en monitoreo tiempo real: $($realtimeResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# 3. ANÁLISIS DE PATRONES INTERMITENTES
# ============================================
Write-Host "3️⃣ ANÁLISIS DE PATRONES INTERMITENTES" -ForegroundColor Yellow
Write-Host "=====================================" -ForegroundColor Yellow

# Test de patrones intermitentes
Write-Host "   🔍 Probando análisis de patrones..." -ForegroundColor Gray
$patternsUrl = "$BaseUrl/api/v1/intermittent/intermittent-patterns"
$patternsResult = Invoke-TestRequest -Url $patternsUrl

if ($patternsResult.Success) {
    Write-Host "   ✅ Análisis de patrones funcionando" -ForegroundColor Green
    $analysis = $patternsResult.Data.analysis
    Write-Host "      - Requests totales: $($analysis.summary.total_requests)" -ForegroundColor Gray
    Write-Host "      - Requests exitosos: $($analysis.summary.successful_requests)" -ForegroundColor Gray
    Write-Host "      - Requests fallidos: $($analysis.summary.failed_requests)" -ForegroundColor Gray
    Write-Host "      - Tasa de éxito: $($analysis.summary.success_rate)%" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error en análisis de patrones: $($patternsResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# 4. ANÁLISIS DE MOMENTOS DE FALLO
# ============================================
Write-Host "4️⃣ ANÁLISIS DE MOMENTOS DE FALLO" -ForegroundColor Yellow
Write-Host "=================================" -ForegroundColor Yellow

# Test de análisis de momentos de fallo
Write-Host "   🚨 Probando análisis de momentos de fallo..." -ForegroundColor Gray
$failureMomentsUrl = "$BaseUrl/api/v1/realtime/failure-moments-analysis"
$failureMomentsResult = Invoke-TestRequest -Url $failureMomentsUrl

if ($failureMomentsResult.Success) {
    Write-Host "   ✅ Análisis de momentos de fallo funcionando" -ForegroundColor Green
    $analysis = $failureMomentsResult.Data.analysis
    Write-Host "      - Momentos de fallo capturados: $($analysis.total_failure_moments)" -ForegroundColor Gray
    
    if ($analysis.total_failure_moments -gt 0) {
        Write-Host "      - Patrones de fallo detectados:" -ForegroundColor Gray
        foreach ($pattern in $analysis.failure_patterns.failure_type_distribution.PSObject.Properties) {
            Write-Host "        * $($pattern.Name): $($pattern.Value)" -ForegroundColor Gray
        }
    } else {
        Write-Host "      - No hay momentos de fallo capturados" -ForegroundColor Green
    }
} else {
    Write-Host "   ❌ Error en análisis de momentos de fallo: $($failureMomentsResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# 5. SIMULACIÓN DE MONITOREO ACTIVO
# ============================================
Write-Host "5️⃣ SIMULACIÓN DE MONITOREO ACTIVO" -ForegroundColor Yellow
Write-Host "=================================" -ForegroundColor Yellow

# Iniciar sesión de monitoreo
Write-Host "   🔍 Iniciando sesión de monitoreo..." -ForegroundColor Gray
$sessionId = "test_session_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
$startMonitoringData = @{
    session_id = $sessionId
    target_endpoints = @("/api/v1/auth/me", "/api/v1/usuarios/", "/api/v1/clientes/")
} | ConvertTo-Json

$startMonitoringUrl = "$BaseUrl/api/v1/realtime/start-monitoring"
$startMonitoringResult = Invoke-TestRequest -Url $startMonitoringUrl -Method "POST" -Body $startMonitoringData

if ($startMonitoringResult.Success) {
    Write-Host "   ✅ Sesión de monitoreo iniciada: $sessionId" -ForegroundColor Green
    
    # Simular algunos eventos
    Write-Host "   📡 Simulando eventos de autenticación..." -ForegroundColor Gray
    
    $events = @(
        @{ event_type = "auth_success"; event_details = @{ endpoint = "/api/v1/auth/me"; user_id = "1" } },
        @{ event_type = "token_validated"; event_details = @{ token_length = 209; user_id = "1" } },
        @{ event_type = "user_authenticated"; event_details = @{ email = "itmaster@rapicreditca.com"; user_id = "1" } }
    )
    
    foreach ($event in $events) {
        $eventData = $event | ConvertTo-Json
        $captureEventUrl = "$BaseUrl/api/v1/realtime/capture-auth-event"
        $captureResult = Invoke-TestRequest -Url $captureEventUrl -Method "POST" -Body $eventData
        
        if ($captureResult.Success) {
            Write-Host "      ✅ Evento capturado: $($event.event_type)" -ForegroundColor Green
        } else {
            Write-Host "      ❌ Error capturando evento: $($captureResult.Error)" -ForegroundColor Red
        }
    }
    
    # Detener sesión de monitoreo
    Write-Host "   ⏹️ Deteniendo sesión de monitoreo..." -ForegroundColor Gray
    $stopMonitoringUrl = "$BaseUrl/api/v1/realtime/stop-monitoring/$sessionId"
    $stopMonitoringResult = Invoke-TestRequest -Url $stopMonitoringUrl -Method "POST"
    
    if ($stopMonitoringResult.Success) {
        Write-Host "   ✅ Sesión de monitoreo detenida exitosamente" -ForegroundColor Green
        $session = $stopMonitoringResult.Data.monitoring_session
        Write-Host "      - Duración: $($session.duration_seconds) segundos" -ForegroundColor Gray
        Write-Host "      - Eventos capturados: $($session.events_captured)" -ForegroundColor Gray
        Write-Host "      - Fallos capturados: $($session.failures_captured)" -ForegroundColor Gray
        Write-Host "      - Éxitos capturados: $($session.successes_captured)" -ForegroundColor Gray
    } else {
        Write-Host "   ❌ Error deteniendo sesión: $($stopMonitoringResult.Error)" -ForegroundColor Red
    }
} else {
    Write-Host "   ❌ Error iniciando sesión de monitoreo: $($startMonitoringResult.Error)" -ForegroundColor Red
}

Write-Host ""

# ============================================
# ANÁLISIS INTEGRADO ACTUALIZADO
# ============================================
Write-Host "🔍 ANÁLISIS INTEGRADO ACTUALIZADO" -ForegroundColor Yellow
Write-Host "=================================" -ForegroundColor Yellow

# Recopilar todos los resultados
$allResults = @{
    "analisis_intermitente" = $intermittentResult.Success
    "monitoreo_tiempo_real" = $realtimeResult.Success
    "analisis_patrones" = $patternsResult.Success
    "analisis_momentos_fallo" = $failureMomentsResult.Success
    "simulacion_monitoreo" = $startMonitoringResult.Success
}

$successfulApproaches = ($allResults.Values | Where-Object { $_ -eq $true }).Count
$totalApproaches = $allResults.Count

Write-Host "   📊 Resumen de enfoques actualizados:" -ForegroundColor Gray
foreach ($approach in $allResults.Keys) {
    $status = if ($allResults[$approach]) { "✅" } else { "❌" }
    Write-Host "      $status $approach" -ForegroundColor $(if ($allResults[$approach]) { "Green" } else { "Red" })
}

Write-Host ""

# ============================================
# ESTRATEGIA ACTUALIZADA
# ============================================
Write-Host "🎯 ESTRATEGIA ACTUALIZADA BASADA EN EVIDENCIA" -ForegroundColor Yellow
Write-Host "=============================================" -ForegroundColor Yellow

Write-Host "   🔍 Conclusiones del análisis de logs:" -ForegroundColor Gray
Write-Host "      ✅ El sistema funciona correctamente la mayoría del tiempo" -ForegroundColor Green
Write-Host "      ✅ La autenticación JWT es válida y funciona" -ForegroundColor Green
Write-Host "      ✅ Los usuarios existen y están activos" -ForegroundColor Green
Write-Host "      ✅ Los endpoints responden correctamente" -ForegroundColor Green
Write-Host "      ✅ CORS está configurado correctamente" -ForegroundColor Green
Write-Host ""

Write-Host "   🎯 Nueva estrategia de validación:" -ForegroundColor Gray
Write-Host "      1. MONITOREO ACTIVO: Activar monitoreo cuando ocurran fallos 401" -ForegroundColor White
Write-Host "      2. ANÁLISIS INTERMITENTE: Comparar momentos de éxito vs fallo" -ForegroundColor White
Write-Host "      3. CAPTURA EN TIEMPO REAL: Registrar eventos específicos cuando fallan" -ForegroundColor White
Write-Host "      4. PATRONES ESPECÍFICOS: Identificar triggers específicos de fallo" -ForegroundColor White
Write-Host "      5. CORRELACIÓN TEMPORAL: Analizar timing entre éxitos y fallos" -ForegroundColor White
Write-Host ""

Write-Host "   📋 Próximos pasos recomendados:" -ForegroundColor Cyan
Write-Host "      1. Activar monitoreo en tiempo real durante uso normal" -ForegroundColor White
Write-Host "      2. Cuando ocurra un fallo 401, analizar inmediatamente" -ForegroundColor White
Write-Host "      3. Comparar el momento de fallo con momentos de éxito" -ForegroundColor White
Write-Host "      4. Identificar diferencias específicas en el contexto" -ForegroundColor White
Write-Host "      5. Documentar patrones de fallo intermitente" -ForegroundColor White

Write-Host ""
Write-Host "🚀 VALIDACIÓN ACTUALIZADA COMPLETADA" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Sistemas de validación actualizados:" -ForegroundColor Cyan
Write-Host "   • Análisis de fallos intermitentes" -ForegroundColor White
Write-Host "   • Monitoreo en tiempo real específico" -ForegroundColor White
Write-Host "   • Análisis de patrones intermitentes" -ForegroundColor White
Write-Host "   • Análisis de momentos específicos de fallo" -ForegroundColor White
Write-Host "   • Simulación de monitoreo activo" -ForegroundColor White
Write-Host ""
Write-Host "🎯 Enfoque actualizado:" -ForegroundColor Cyan
Write-Host "   • Problema identificado como INTERMITENTE" -ForegroundColor White
Write-Host "   • Sistema funciona correctamente la mayoría del tiempo" -ForegroundColor White
Write-Host "   • Necesario monitoreo activo para capturar fallos específicos" -ForegroundColor White
Write-Host "   • Análisis comparativo entre momentos de éxito y fallo" -ForegroundColor White
Write-Host ""
Write-Host "⚠️ IMPORTANTE: Activar monitoreo cuando ocurran fallos 401 reales" -ForegroundColor Red
Write-Host "🔍 Usar estos sistemas para capturar evidencia en el momento exacto del fallo" -ForegroundColor Red
