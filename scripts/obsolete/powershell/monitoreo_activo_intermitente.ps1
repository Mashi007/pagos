# scripts/powershell/monitoreo_activo_intermitente.ps1
# Script para monitoreo activo cuando ocurran fallos 401 intermitentes

param(
    [string]$BaseUrl = "https://pagos-f2qf.onrender.com",
    [int]$MonitoringDurationMinutes = 60,
    [string]$SessionId = $null
)

if (-not $SessionId) {
    $SessionId = "monitor_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
}

Write-Host "🔍 MONITOREO ACTIVO DE FALLOS INTERMITENTES" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Configuración:" -ForegroundColor Yellow
Write-Host "   - URL Base: $BaseUrl" -ForegroundColor Gray
Write-Host "   - Duración: $MonitoringDurationMinutes minutos" -ForegroundColor Gray
Write-Host "   - Sesión ID: $SessionId" -ForegroundColor Gray
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

# Función para registrar evento
function Register-AuthEvent {
    param(
        [string]$EventType,
        [hashtable]$EventDetails
    )
    
    $eventData = @{
        event_type = $EventType
        event_details = $EventDetails
    } | ConvertTo-Json
    
    $captureUrl = "$BaseUrl/api/v1/realtime/capture-auth-event"
    $result = Invoke-TestRequest -Url $captureUrl -Method "POST" -Body $eventData
    
    if ($result.Success) {
        Write-Host "   📡 Evento registrado: $EventType" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Error registrando evento: $($result.Error)" -ForegroundColor Red
    }
}

# Función para registrar request exitoso
function Register-SuccessfulRequest {
    param(
        [string]$Endpoint,
        [string]$Method = "GET",
        [int]$ResponseTimeMs = 0,
        [string]$UserId = $null
    )
    
    $requestData = @{
        endpoint = $Endpoint
        method = $Method
        response_time_ms = $ResponseTimeMs
        user_id = $UserId
        token_length = 209  # Basado en evidencia de logs
        client_ip = "127.0.0.1"
        user_agent = "PowerShell Monitor"
    } | ConvertTo-Json
    
    $logUrl = "$BaseUrl/api/v1/intermittent/log-successful-request"
    $result = Invoke-TestRequest -Url $logUrl -Method "POST" -Body $requestData
    
    if ($result.Success) {
        Write-Host "   ✅ Request exitoso registrado: $Endpoint" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Error registrando request exitoso: $($result.Error)" -ForegroundColor Red
    }
}

# Función para registrar request fallido
function Register-FailedRequest {
    param(
        [string]$Endpoint,
        [string]$Method = "GET",
        [string]$ErrorType = "401_unauthorized",
        [string]$ErrorMessage = "Unauthorized",
        [string]$UserId = $null
    )
    
    $requestData = @{
        endpoint = $Endpoint
        method = $Method
        error_type = $ErrorType
        error_message = $ErrorMessage
        user_id = $UserId
        token_length = 209
        client_ip = "127.0.0.1"
        user_agent = "PowerShell Monitor"
    } | ConvertTo-Json
    
    $logUrl = "$BaseUrl/api/v1/intermittent/log-failed-request"
    $result = Invoke-TestRequest -Url $logUrl -Method "POST" -Body $requestData
    
    if ($result.Success) {
        Write-Host "   ❌ Request fallido registrado: $Endpoint - $ErrorType" -ForegroundColor Red
    } else {
        Write-Host "   ❌ Error registrando request fallido: $($result.Error)" -ForegroundColor Red
    }
}

# ============================================
# INICIAR MONITOREO ACTIVO
# ============================================
Write-Host "🚀 INICIANDO MONITOREO ACTIVO" -ForegroundColor Yellow
Write-Host "============================" -ForegroundColor Yellow

# Iniciar sesión de monitoreo
Write-Host "   🔍 Iniciando sesión de monitoreo..." -ForegroundColor Gray
$startMonitoringData = @{
    session_id = $SessionId
    target_endpoints = @("/api/v1/auth/me", "/api/v1/usuarios/", "/api/v1/clientes/", "/api/v1/prestamos/")
} | ConvertTo-Json

$startUrl = "$BaseUrl/api/v1/realtime/start-monitoring"
$startResult = Invoke-TestRequest -Url $startUrl -Method "POST" -Body $startMonitoringData

if (-not $startResult.Success) {
    Write-Host "   ❌ Error iniciando monitoreo: $($startResult.Error)" -ForegroundColor Red
    Write-Host "   ⚠️ Continuando sin monitoreo activo..." -ForegroundColor Yellow
}

Write-Host ""

# ============================================
# MONITOREO CONTINUO
# ============================================
Write-Host "📡 MONITOREO CONTINUO ACTIVO" -ForegroundColor Yellow
Write-Host "============================" -ForegroundColor Yellow

$endTime = (Get-Date).AddMinutes($MonitoringDurationMinutes)
$checkInterval = 30  # segundos
$checkCount = 0

Write-Host "   ⏰ Monitoreo hasta: $($endTime.ToString('HH:mm:ss'))" -ForegroundColor Gray
Write-Host "   🔄 Intervalo de verificación: $checkInterval segundos" -ForegroundColor Gray
Write-Host ""

do {
    $checkCount++
    $currentTime = Get-Date
    $remainingTime = $endTime - $currentTime
    
    Write-Host "🔍 Verificación #$checkCount - $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Cyan
    Write-Host "   ⏰ Tiempo restante: $([math]::Round($remainingTime.TotalMinutes, 1)) minutos" -ForegroundColor Gray
    
    # Test de endpoints críticos
    $criticalEndpoints = @(
        @{ Name = "Auth Me"; Url = "/api/v1/auth/me" },
        @{ Name = "Usuarios"; Url = "/api/v1/usuarios/?page=1&page_size=10" },
        @{ Name = "Clientes"; Url = "/api/v1/clientes/?page=1&per_page=10" }
    )
    
    foreach ($endpoint in $criticalEndpoints) {
        $startTime = Get-Date
        $result = Invoke-TestRequest -Url "$BaseUrl$($endpoint.Url)"
        $responseTime = [math]::Round(((Get-Date) - $startTime).TotalMilliseconds)
        
        if ($result.Success) {
            Write-Host "   ✅ $($endpoint.Name): OK ($responseTime ms)" -ForegroundColor Green
            
            # Registrar request exitoso
            Register-SuccessfulRequest -Endpoint $endpoint.Url -ResponseTimeMs $responseTime -UserId "1"
            
            # Registrar evento de éxito
            Register-AuthEvent -EventType "auth_success" -EventDetails @{
                endpoint = $endpoint.Url
                response_time_ms = $responseTime
                user_id = "1"
            }
        } else {
            Write-Host "   ❌ $($endpoint.Name): ERROR - $($result.Error)" -ForegroundColor Red
            
            # Registrar request fallido
            Register-FailedRequest -Endpoint $endpoint.Url -ErrorType "request_failed" -ErrorMessage $result.Error -UserId "1"
            
            # Registrar evento de fallo
            Register-AuthEvent -EventType "auth_failure" -EventDetails @{
                endpoint = $endpoint.Url
                error_message = $result.Error
                user_id = "1"
            }
        }
    }
    
    # Análisis intermitente cada 5 verificaciones
    if ($checkCount % 5 -eq 0) {
        Write-Host "   📊 Realizando análisis intermitente..." -ForegroundColor Gray
        
        $intermittentUrl = "$BaseUrl/api/v1/intermittent/intermittent-patterns"
        $intermittentResult = Invoke-TestRequest -Url $intermittentUrl
        
        if ($intermittentResult.Success) {
            $analysis = $intermittentResult.Data.analysis
            Write-Host "      - Requests totales: $($analysis.summary.total_requests)" -ForegroundColor Gray
            Write-Host "      - Requests exitosos: $($analysis.summary.successful_requests)" -ForegroundColor Gray
            Write-Host "      - Requests fallidos: $($analysis.summary.failed_requests)" -ForegroundColor Gray
            Write-Host "      - Tasa de éxito: $($analysis.summary.success_rate)%" -ForegroundColor Gray
        }
    }
    
    Write-Host ""
    
    # Esperar antes de la siguiente verificación
    if ($currentTime -lt $endTime) {
        Write-Host "   ⏳ Esperando $checkInterval segundos..." -ForegroundColor Gray
        Start-Sleep -Seconds $checkInterval
    }
    
} while ($currentTime -lt $endTime)

# ============================================
# FINALIZAR MONITOREO
# ============================================
Write-Host "⏹️ FINALIZANDO MONITOREO" -ForegroundColor Yellow
Write-Host "=======================" -ForegroundColor Yellow

# Detener sesión de monitoreo
Write-Host "   🔍 Deteniendo sesión de monitoreo..." -ForegroundColor Gray
$stopUrl = "$BaseUrl/api/v1/realtime/stop-monitoring/$SessionId"
$stopResult = Invoke-TestRequest -Url $stopUrl -Method "POST"

if ($stopResult.Success) {
    $session = $stopResult.Data.monitoring_session
    Write-Host "   ✅ Sesión detenida exitosamente" -ForegroundColor Green
    Write-Host "      - Duración: $([math]::Round($session.duration_seconds, 1)) segundos" -ForegroundColor Gray
    Write-Host "      - Eventos capturados: $($session.events_captured)" -ForegroundColor Gray
    Write-Host "      - Fallos capturados: $($session.failures_captured)" -ForegroundColor Gray
    Write-Host "      - Éxitos capturados: $($session.successes_captured)" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Error deteniendo sesión: $($stopResult.Error)" -ForegroundColor Red
}

# Análisis final
Write-Host ""
Write-Host "📊 ANÁLISIS FINAL" -ForegroundColor Yellow
Write-Host "=================" -ForegroundColor Yellow

$finalAnalysisUrl = "$BaseUrl/api/v1/intermittent/intermittent-patterns"
$finalAnalysisResult = Invoke-TestRequest -Url $finalAnalysisUrl

if ($finalAnalysisResult.Success) {
    $analysis = $finalAnalysisResult.Data.analysis
    Write-Host "   🎯 Resultados del monitoreo:" -ForegroundColor Gray
    Write-Host "      - Verificaciones realizadas: $checkCount" -ForegroundColor Gray
    Write-Host "      - Requests totales: $($analysis.summary.total_requests)" -ForegroundColor Gray
    Write-Host "      - Requests exitosos: $($analysis.summary.successful_requests)" -ForegroundColor Gray
    Write-Host "      - Requests fallidos: $($analysis.summary.failed_requests)" -ForegroundColor Gray
    Write-Host "      - Tasa de éxito: $($analysis.summary.success_rate)%" -ForegroundColor Gray
    
    if ($analysis.summary.failed_requests -gt 0) {
        Write-Host "   🚨 FALLOS DETECTADOS DURANTE EL MONITOREO" -ForegroundColor Red
        Write-Host "   📋 Revisar análisis de patrones intermitentes" -ForegroundColor Yellow
    } else {
        Write-Host "   ✅ NO SE DETECTARON FALLOS DURANTE EL MONITOREO" -ForegroundColor Green
        Write-Host "   📋 El sistema funcionó correctamente durante $MonitoringDurationMinutes minutos" -ForegroundColor Green
    }
} else {
    Write-Host "   ❌ Error obteniendo análisis final: $($finalAnalysisResult.Error)" -ForegroundColor Red
}

Write-Host ""
Write-Host "🚀 MONITOREO ACTIVO COMPLETADO" -ForegroundColor Green
Write-Host "=============================" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Próximos pasos:" -ForegroundColor Cyan
Write-Host "   1. Revisar análisis de patrones intermitentes" -ForegroundColor White
Write-Host "   2. Si se detectaron fallos, analizar momentos específicos" -ForegroundColor White
Write-Host "   3. Comparar con análisis forense si es necesario" -ForegroundColor White
Write-Host "   4. Documentar patrones encontrados" -ForegroundColor White
