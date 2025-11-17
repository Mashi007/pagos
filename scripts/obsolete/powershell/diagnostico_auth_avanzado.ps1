# 🔍 Script de Diagnóstico Avanzado de Autenticación
# Sistema completo para encontrar causa raíz de problemas 401

param(
    [string]$BackendUrl = "https://pagos-f2qf.onrender.com",
    [switch]$Verbose = $false
)

Write-Host "🔍 DIAGNÓSTICO AVANZADO DE AUTENTICACIÓN" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Backend URL: $BackendUrl" -ForegroundColor Yellow
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

# 1. DIAGNÓSTICO GENERAL DEL SISTEMA
Write-Host "1️⃣ DIAGNÓSTICO GENERAL DEL SISTEMA" -ForegroundColor Green
Write-Host "-----------------------------------" -ForegroundColor Green

$diagnostico = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/auth-debug/auth-debug"
if ($diagnostico.Success) {
    Write-Host "✅ Diagnóstico general completado" -ForegroundColor Green
    $diagnostico.Data | ConvertTo-Json -Depth 3 | Write-Host
} else {
    Write-Host "❌ Error en diagnóstico general: $($diagnostico.Error)" -ForegroundColor Red
}
Write-Host ""

# 2. HEALTH CHECK DETALLADO
Write-Host "2️⃣ HEALTH CHECK DETALLADO" -ForegroundColor Green
Write-Host "-------------------------" -ForegroundColor Green

$healthCheck = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/monitor/health-check"
if ($healthCheck.Success) {
    Write-Host "✅ Health check completado" -ForegroundColor Green
    $healthCheck.Data | ConvertTo-Json -Depth 3 | Write-Host
} else {
    Write-Host "❌ Error en health check: $($healthCheck.Error)" -ForegroundColor Red
}
Write-Host ""

# 3. GENERAR TOKEN DE PRUEBA
Write-Host "3️⃣ GENERAR TOKEN DE PRUEBA" -ForegroundColor Green
Write-Host "---------------------------" -ForegroundColor Green

$tokenTest = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/token/generate-test-token" -Method "POST"
if ($tokenTest.Success) {
    Write-Host "✅ Token de prueba generado" -ForegroundColor Green
    $testToken = $tokenTest.Data.test_token
    Write-Host "Token: $($testToken.Substring(0, 50))..." -ForegroundColor Yellow
    
    # 4. VERIFICAR TOKEN GENERADO
    Write-Host ""
    Write-Host "4️⃣ VERIFICAR TOKEN GENERADO" -ForegroundColor Green
    Write-Host "----------------------------" -ForegroundColor Green
    
    $headers = @{
        "Authorization" = "Bearer $testToken"
    }
    
    $tokenVerify = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/token/verify-token" -Method "POST" -Headers $headers
    if ($tokenVerify.Success) {
        Write-Host "✅ Verificación de token completada" -ForegroundColor Green
        $tokenVerify.Data | ConvertTo-Json -Depth 3 | Write-Host
    } else {
        Write-Host "❌ Error verificando token: $($tokenVerify.Error)" -ForegroundColor Red
    }
    
    # 5. PROBAR ENDPOINT PROTEGIDO CON TOKEN
    Write-Host ""
    Write-Host "5️⃣ PROBAR ENDPOINT PROTEGIDO" -ForegroundColor Green
    Write-Host "-----------------------------" -ForegroundColor Green
    
    $protectedTest = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/auth/me" -Headers $headers
    if ($protectedTest.Success) {
        Write-Host "✅ Endpoint protegido funcionando" -ForegroundColor Green
        $protectedTest.Data | ConvertTo-Json -Depth 2 | Write-Host
    } else {
        Write-Host "❌ Error en endpoint protegido: $($protectedTest.Error)" -ForegroundColor Red
        Write-Host "Status Code: $($protectedTest.StatusCode)" -ForegroundColor Red
    }
    
} else {
    Write-Host "❌ Error generando token de prueba: $($tokenTest.Error)" -ForegroundColor Red
}
Write-Host ""

# 6. DASHBOARD DE DIAGNÓSTICO
Write-Host "6️⃣ DASHBOARD DE DIAGNÓSTICO" -ForegroundColor Green
Write-Host "----------------------------" -ForegroundColor Green

$dashboard = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/monitor/dashboard"
if ($dashboard.Success) {
    Write-Host "✅ Dashboard de diagnóstico obtenido" -ForegroundColor Green
    $dashboard.Data | ConvertTo-Json -Depth 3 | Write-Host
} else {
    Write-Host "❌ Error obteniendo dashboard: $($dashboard.Error)" -ForegroundColor Red
}
Write-Host ""

# 7. LOGS DE AUDITORÍA
Write-Host "7️⃣ LOGS DE AUDITORÍA" -ForegroundColor Green
Write-Host "--------------------" -ForegroundColor Green

$logs = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/monitor/logs?minutes=60&limit=20"
if ($logs.Success) {
    Write-Host "✅ Logs de auditoría obtenidos" -ForegroundColor Green
    $logs.Data | ConvertTo-Json -Depth 3 | Write-Host
} else {
    Write-Host "❌ Error obteniendo logs: $($logs.Error)" -ForegroundColor Red
}
Write-Host ""

# 8. TEST DE AUTENTICACIÓN COMPLETO
Write-Host "8️⃣ TEST DE AUTENTICACIÓN COMPLETO" -ForegroundColor Green
Write-Host "----------------------------------" -ForegroundColor Green

$authTest = Invoke-SafeRequest -Uri "$BackendUrl/api/v1/auth-debug/auth-test" -Method "POST"
if ($authTest.Success) {
    Write-Host "✅ Test de autenticación completado" -ForegroundColor Green
    $authTest.Data | ConvertTo-Json -Depth 3 | Write-Host
} else {
    Write-Host "❌ Error en test de autenticación: $($authTest.Error)" -ForegroundColor Red
}
Write-Host ""

# RESUMEN FINAL
Write-Host "📊 RESUMEN DEL DIAGNÓSTICO" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

$tests = @(
    @{Name="Diagnóstico General"; Result=$diagnostico.Success},
    @{Name="Health Check"; Result=$healthCheck.Success},
    @{Name="Token de Prueba"; Result=$tokenTest.Success},
    @{Name="Verificación Token"; Result=$tokenVerify.Success},
    @{Name="Endpoint Protegido"; Result=$protectedTest.Success},
    @{Name="Dashboard"; Result=$dashboard.Success},
    @{Name="Logs Auditoría"; Result=$logs.Success},
    @{Name="Test Autenticación"; Result=$authTest.Success}
)

$passedTests = ($tests | Where-Object { $_.Result }).Count
$totalTests = $tests.Count

Write-Host "Tests Exitosos: $passedTests/$totalTests" -ForegroundColor $(if ($passedTests -eq $totalTests) { "Green" } else { "Yellow" })

foreach ($test in $tests) {
    $status = if ($test.Result) { "✅" } else { "❌" }
    Write-Host "$status $($test.Name)" -ForegroundColor $(if ($test.Result) { "Green" } else { "Red" })
}

Write-Host ""
Write-Host "🎯 PRÓXIMOS PASOS:" -ForegroundColor Cyan
Write-Host "1. Revisar los resultados de cada test" -ForegroundColor White
Write-Host "2. Si hay errores, revisar los logs detallados" -ForegroundColor White
Write-Host "3. Usar el dashboard para monitoreo continuo" -ForegroundColor White
Write-Host "4. Aplicar fixes automáticos si están disponibles" -ForegroundColor White

Write-Host ""
Write-Host "🔗 ENDPOINTS DISPONIBLES:" -ForegroundColor Cyan
Write-Host "- Diagnóstico: $BackendUrl/api/v1/auth-debug/auth-debug" -ForegroundColor White
Write-Host "- Health Check: $BackendUrl/api/v1/monitor/health-check" -ForegroundColor White
Write-Host "- Dashboard: $BackendUrl/api/v1/monitor/dashboard" -ForegroundColor White
Write-Host "- Logs: $BackendUrl/api/v1/monitor/logs" -ForegroundColor White
Write-Host "- Verificar Token: $BackendUrl/api/v1/token/verify-token" -ForegroundColor White
