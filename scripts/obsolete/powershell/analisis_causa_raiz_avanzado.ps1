# 🔬 SCRIPT DE ANÁLISIS AVANZADO DE CAUSA RAÍZ
# Sistema completo de diagnóstico con múltiples mecanismos de validación

param(
    [string]$BackendUrl = "https://pagos-f2qf.onrender.com",
    [switch]$Verbose = $false,
    [switch]$FullAnalysis = $false
)

Write-Host "🔬 ANÁLISIS AVANZADO DE CAUSA RAÍZ - AUTENTICACIÓN" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "Backend URL: $BackendUrl" -ForegroundColor Yellow
Write-Host "Modo: $(if ($FullAnalysis) { 'Análisis Completo' } else { 'Análisis Rápido' })" -ForegroundColor Yellow
Write-Host ""

# Función para hacer requests con manejo de errores
function Invoke-SafeRequest {
    param(
        [string]$Uri,
        [string]$Method = "GET",
        [hashtable]$Headers = @{},
        [string]$Body = $null
    )
    
    try {
        $params = @{
            Uri = $Uri
            Method = $Method
            Headers = $Headers
            TimeoutSec = 30
        }
        
        if ($Body) {
            $params.Body = $Body
            $params.ContentType = "application/json"
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

# Función para mostrar resultados de manera estructurada
function Show-AnalysisResult {
    param(
        [string]$Title,
        [object]$Result,
        [string]$Status = "info"
    )
    
    $color = switch ($Status) {
        "success" { "Green" }
        "warning" { "Yellow" }
        "error" { "Red" }
        default { "White" }
    }
    
    Write-Host "`n$Title" -ForegroundColor $color
    Write-Host ("-" * $Title.Length) -ForegroundColor $color
    
    if ($Result.Success) {
        if ($Verbose) {
            $Result.Data | ConvertTo-Json -Depth 3 | Write-Host
        } else {
            # Mostrar solo información clave
            if ($Result.Data.status) {
                Write-Host "Estado: $($Result.Data.status)" -ForegroundColor Green
            }
            if ($Result.Data.summary) {
                Write-Host "Resumen: $($Result.Data.summary)" -ForegroundColor Green
            }
            if ($Result.Data.recommendations) {
                Write-Host "Recomendaciones:" -ForegroundColor Yellow
                foreach ($rec in $Result.Data.recommendations) {
                    Write-Host "  • $rec" -ForegroundColor Yellow
                }
            }
        }
    } else {
        Write-Host "❌ Error: $($Result.Error)" -ForegroundColor Red
    }
}

# =============================================================================
# FASE 1: DIAGNÓSTICO BÁSICO DEL SISTEMA
# =============================================================================

Write-Host "🔍 FASE 1: DIAGNÓSTICO BÁSICO DEL SISTEMA" -ForegroundColor Magenta
Write-Host "=========================================" -ForegroundColor Magenta

# 1.1 Health Check Detallado
$healthCheck = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/monitor/health-check"
Show-AnalysisResult -Title "1.1 Health Check Detallado" -Result $healthCheck -Status "success"

# 1.2 Diagnóstico General de Autenticación
$authDebug = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/auth-debug/auth-debug"
Show-AnalysisResult -Title "1.2 Diagnóstico General de Autenticación" -Result $authDebug -Status "success"

# 1.3 Dashboard de Diagnóstico
$dashboard = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/monitor/dashboard"
Show-AnalysisResult -Title "1.3 Dashboard de Diagnóstico" -Result $dashboard -Status "success"

# =============================================================================
# FASE 2: ANÁLISIS DE FLUJO DE AUTENTICACIÓN
# =============================================================================

Write-Host "`n🔬 FASE 2: ANÁLISIS DE FLUJO DE AUTENTICACIÓN" -ForegroundColor Magenta
Write-Host "=============================================" -ForegroundColor Magenta

# 2.1 Generar Token de Prueba
$tokenTest = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/token/generate-test-token" -Method "POST"
Show-AnalysisResult -Title "2.1 Generar Token de Prueba" -Result $tokenTest -Status "success"

if ($tokenTest.Success -and $tokenTest.Data.test_token) {
    $testToken = $tokenTest.Data.test_token
    Write-Host "✅ Token generado: $($testToken.Substring(0, 50))..." -ForegroundColor Green
    
    # 2.2 Trace Completo del Flujo de Autenticación
    $headers = @{
        "Authorization" = "Bearer $testToken"
    }
    
    $flowTrace = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/flow/trace-auth-flow" -Method "POST" -Headers $headers
    Show-AnalysisResult -Title "2.2 Trace Completo del Flujo de Autenticación" -Result $flowTrace -Status "success"
    
    # 2.3 Verificación Detallada del Token
    $tokenVerify = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/token/verify-token" -Method "POST" -Headers $headers
    Show-AnalysisResult -Title "2.3 Verificación Detallada del Token" -Result $tokenVerify -Status "success"
    
    # 2.4 Probar Endpoint Protegido
    $protectedTest = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/auth/me" -Headers $headers
    Show-AnalysisResult -Title "2.4 Probar Endpoint Protegido" -Result $protectedTest -Status "success"
} else {
    Write-Host "❌ No se pudo generar token de prueba" -ForegroundColor Red
}

# =============================================================================
# FASE 3: ANÁLISIS DE CORRELACIÓN Y PATRONES
# =============================================================================

Write-Host "`n🔗 FASE 3: ANÁLISIS DE CORRELACIÓN Y PATRONES" -ForegroundColor Magenta
Write-Host "==============================================" -ForegroundColor Magenta

# 3.1 Análisis de Correlación de Requests
$correlation = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/flow/analyze-correlation?minutes=60"
Show-AnalysisResult -Title "3.1 Análisis de Correlación de Requests" -Result $correlation -Status "success"

# 3.2 Detección de Anomalías
$anomalies = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/flow/detect-anomalies"
Show-AnalysisResult -Title "3.2 Detección de Anomalías" -Result $anomalies -Status "success"

# 3.3 Timeline de Flujos de Autenticación
$timeline = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/flow/flow-timeline?minutes=30&limit=20"
Show-AnalysisResult -Title "3.3 Timeline de Flujos de Autenticación" -Result $timeline -Status "success"

# =============================================================================
# FASE 4: ANÁLISIS PREDICTIVO (Solo si FullAnalysis está habilitado)
# =============================================================================

if ($FullAnalysis) {
    Write-Host "`n🔮 FASE 4: ANÁLISIS PREDICTIVO" -ForegroundColor Magenta
    Write-Host "===============================" -ForegroundColor Magenta
    
    # 4.1 Recolectar Métricas Actuales
    $metrics = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/predictive/collect-metrics" -Method "POST"
    Show-AnalysisResult -Title "4.1 Recolectar Métricas Actuales" -Result $metrics -Status "success"
    
    # 4.2 Análisis Predictivo
    $predictive = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/predictive/predictive-analysis"
    Show-AnalysisResult -Title "4.2 Análisis Predictivo" -Result $predictive -Status "success"
    
    # 4.3 Health Score del Sistema
    $healthScore = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/predictive/health-score"
    Show-AnalysisResult -Title "4.3 Health Score del Sistema" -Result $healthScore -Status "success"
    
    # 4.4 Historial de Métricas
    $metricsHistory = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/predictive/metrics-history?hours=24&limit=50"
    Show-AnalysisResult -Title "4.4 Historial de Métricas" -Result $metricsHistory -Status "success"
}

# =============================================================================
# FASE 5: SISTEMA DE ALERTAS INTELIGENTES
# =============================================================================

Write-Host "`n🚨 FASE 5: SISTEMA DE ALERTAS INTELIGENTES" -ForegroundColor Magenta
Write-Host "===========================================" -ForegroundColor Magenta

# 5.1 Evaluar Alertas
$alerts = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/alerts/evaluate-alerts" -Method "POST"
Show-AnalysisResult -Title "5.1 Evaluar Alertas" -Result $alerts -Status "success"

# 5.2 Alertas Activas
$activeAlerts = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/alerts/active-alerts"
Show-AnalysisResult -Title "5.2 Alertas Activas" -Result $activeAlerts -Status "success"

# 5.3 Resumen de Alertas
$alertSummary = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/alerts/alert-summary"
Show-AnalysisResult -Title "5.3 Resumen de Alertas" -Result $alertSummary -Status "success"

# 5.4 Reglas de Alerta Configuradas
$alertRules = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/alerts/alert-rules"
Show-AnalysisResult -Title "5.4 Reglas de Alerta Configuradas" -Result $alertRules -Status "success"

# =============================================================================
# RESUMEN FINAL Y RECOMENDACIONES
# =============================================================================

Write-Host "`n📊 RESUMEN FINAL Y RECOMENDACIONES" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

# Contar tests exitosos
$tests = @(
    @{Name="Health Check"; Result=$healthCheck.Success},
    @{Name="Diagnóstico Auth"; Result=$authDebug.Success},
    @{Name="Dashboard"; Result=$dashboard.Success},
    @{Name="Token de Prueba"; Result=$tokenTest.Success},
    @{Name="Trace de Flujo"; Result=$flowTrace.Success},
    @{Name="Verificación Token"; Result=$tokenVerify.Success},
    @{Name="Endpoint Protegido"; Result=$protectedTest.Success},
    @{Name="Análisis Correlación"; Result=$correlation.Success},
    @{Name="Detección Anomalías"; Result=$anomalies.Success},
    @{Name="Timeline"; Result=$timeline.Success},
    @{Name="Evaluar Alertas"; Result=$alerts.Success},
    @{Name="Alertas Activas"; Result=$activeAlerts.Success},
    @{Name="Resumen Alertas"; Result=$alertSummary.Success},
    @{Name="Reglas Alertas"; Result=$alertRules.Success}
)

if ($FullAnalysis) {
    $tests += @(
        @{Name="Recolectar Métricas"; Result=$metrics.Success},
        @{Name="Análisis Predictivo"; Result=$predictive.Success},
        @{Name="Health Score"; Result=$healthScore.Success},
        @{Name="Historial Métricas"; Result=$metricsHistory.Success}
    )
}

$passedTests = ($tests | Where-Object { $_.Result }).Count
$totalTests = $tests.Count

Write-Host "Tests Exitosos: $passedTests/$totalTests" -ForegroundColor $(if ($passedTests -eq $totalTests) { "Green" } else { "Yellow" })

# Mostrar estado de cada test
foreach ($test in $tests) {
    $status = if ($test.Result) { "✅" } else { "❌" }
    $color = if ($test.Result) { "Green" } else { "Red" }
    Write-Host "$status $($test.Name)" -ForegroundColor $color
}

# Generar recomendaciones finales
Write-Host "`n🎯 RECOMENDACIONES FINALES:" -ForegroundColor Cyan

if ($passedTests -eq $totalTests) {
    Write-Host "✅ Sistema funcionando correctamente" -ForegroundColor Green
    Write-Host "• Continuar monitoreo rutinario" -ForegroundColor White
    Write-Host "• Revisar alertas periódicamente" -ForegroundColor White
} elseif ($passedTests -gt $totalTests * 0.8) {
    Write-Host "⚠️ Sistema mayormente funcional con algunos problemas" -ForegroundColor Yellow
    Write-Host "• Revisar tests fallidos específicamente" -ForegroundColor White
    Write-Host "• Monitorear alertas activas" -ForegroundColor White
} else {
    Write-Host "🚨 Sistema con problemas significativos" -ForegroundColor Red
    Write-Host "• Investigar causas raíz inmediatamente" -ForegroundColor White
    Write-Host "• Revisar configuración de autenticación" -ForegroundColor White
    Write-Host "• Verificar conectividad de base de datos" -ForegroundColor White
}

Write-Host "`n🔗 ENDPOINTS DISPONIBLES PARA MONITOREO CONTINUO:" -ForegroundColor Cyan
Write-Host "- Health Check: $BackendUrl/api/v1/monitor/health-check" -ForegroundColor White
Write-Host "- Dashboard: $BackendUrl/api/v1/monitor/dashboard" -ForegroundColor White
Write-Host "- Alertas: $BackendUrl/api/v1/alerts/active-alerts" -ForegroundColor White
Write-Host "- Análisis Predictivo: $BackendUrl/api/v1/predictive/predictive-analysis" -ForegroundColor White
Write-Host "- Trace de Flujo: $BackendUrl/api/v1/flow/trace-auth-flow" -ForegroundColor White

Write-Host "`n📈 PRÓXIMOS PASOS:" -ForegroundColor Cyan
Write-Host "1. Revisar resultados detallados de cada fase" -ForegroundColor White
Write-Host "2. Implementar correcciones basadas en recomendaciones" -ForegroundColor White
Write-Host "3. Configurar monitoreo continuo usando los endpoints" -ForegroundColor White
Write-Host "4. Establecer alertas proactivas para prevenir problemas" -ForegroundColor White

Write-Host "`n🎉 ANÁLISIS COMPLETADO" -ForegroundColor Green
