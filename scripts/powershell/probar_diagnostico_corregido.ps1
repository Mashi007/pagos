# scripts/powershell/probar_diagnostico_corregido.ps1
# Script para probar endpoints de diagnóstico después de las correcciones

param(
    [string]$BaseUrl = "https://pagos-f2qf.onrender.com"
)

Write-Host "🔍 PROBANDO ENDPOINTS DE DIAGNÓSTICO CORREGIDOS" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
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

# 1. Probar endpoint de diagnóstico de autenticación
Write-Host "1️⃣ Probando diagnóstico de autenticación..." -ForegroundColor Yellow
$authDebugUrl = "$BaseUrl/api/v1/auth-debug/auth-debug"
$authDebugResult = Invoke-TestRequest -Url $authDebugUrl

if ($authDebugResult.Success) {
    Write-Host "✅ Diagnóstico de autenticación funcionando" -ForegroundColor Green
    Write-Host "   - JWT Config: $($authDebugResult.Data.analysis.jwt_config)" -ForegroundColor Gray
    Write-Host "   - Users Status: $($authDebugResult.Data.analysis.users.status)" -ForegroundColor Gray
} else {
    Write-Host "❌ Error en diagnóstico de autenticación: $($authDebugResult.Error)" -ForegroundColor Red
}

Write-Host ""

# 2. Probar endpoint de test de autenticación
Write-Host "2️⃣ Probando test de autenticación..." -ForegroundColor Yellow
$authTestUrl = "$BaseUrl/api/v1/auth-debug/auth-test"
$authTestResult = Invoke-TestRequest -Url $authTestUrl -Method "POST"

if ($authTestResult.Success) {
    Write-Host "✅ Test de autenticación funcionando" -ForegroundColor Green
    Write-Host "   - Overall Status: $($authTestResult.Data.overall_status)" -ForegroundColor Gray
    Write-Host "   - Login Test: $($authTestResult.Data.tests.login.status)" -ForegroundColor Gray
    Write-Host "   - Validation Test: $($authTestResult.Data.tests.validation.status)" -ForegroundColor Gray
} else {
    Write-Host "❌ Error en test de autenticación: $($authTestResult.Error)" -ForegroundColor Red
}

Write-Host ""

# 3. Probar endpoint de verificación de tokens
Write-Host "3️⃣ Probando verificación de tokens..." -ForegroundColor Yellow
$tokenVerifyUrl = "$BaseUrl/api/v1/token/verify-token"
$tokenVerifyResult = Invoke-TestRequest -Url $tokenVerifyUrl -Method "POST" -Body '{"token": "test"}'

if ($tokenVerifyResult.Success) {
    Write-Host "✅ Verificación de tokens funcionando" -ForegroundColor Green
    Write-Host "   - Status: $($tokenVerifyResult.Data.status)" -ForegroundColor Gray
} else {
    Write-Host "❌ Error en verificación de tokens: $($tokenVerifyResult.Error)" -ForegroundColor Red
}

Write-Host ""

# 4. Probar endpoint de health check
Write-Host "4️⃣ Probando health check..." -ForegroundColor Yellow
$healthUrl = "$BaseUrl/api/v1/monitor/health-check"
$healthResult = Invoke-TestRequest -Url $healthUrl

if ($healthResult.Success) {
    Write-Host "✅ Health check funcionando" -ForegroundColor Green
    Write-Host "   - Status: $($healthResult.Data.status)" -ForegroundColor Gray
    Write-Host "   - Database: $($healthResult.Data.database.status)" -ForegroundColor Gray
} else {
    Write-Host "❌ Error en health check: $($healthResult.Error)" -ForegroundColor Red
}

Write-Host ""

# 5. Probar endpoint de dashboard de diagnóstico
Write-Host "5️⃣ Probando dashboard de diagnóstico..." -ForegroundColor Yellow
$dashboardUrl = "$BaseUrl/api/v1/monitor/dashboard"
$dashboardResult = Invoke-TestRequest -Url $dashboardUrl

if ($dashboardResult.Success) {
    Write-Host "✅ Dashboard de diagnóstico funcionando" -ForegroundColor Green
    Write-Host "   - Status: $($dashboardResult.Data.status)" -ForegroundColor Gray
    Write-Host "   - Timestamp: $($dashboardResult.Data.timestamp)" -ForegroundColor Gray
} else {
    Write-Host "❌ Error en dashboard de diagnóstico: $($dashboardResult.Error)" -ForegroundColor Red
}

Write-Host ""

# Resumen final
Write-Host "📊 RESUMEN DE PRUEBAS" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan

$totalTests = 5
$successfulTests = 0

if ($authDebugResult.Success) { $successfulTests++ }
if ($authTestResult.Success) { $successfulTests++ }
if ($tokenVerifyResult.Success) { $successfulTests++ }
if ($healthResult.Success) { $successfulTests++ }
if ($dashboardResult.Success) { $successfulTests++ }

Write-Host "Tests exitosos: $successfulTests/$totalTests" -ForegroundColor $(if ($successfulTests -eq $totalTests) { "Green" } else { "Yellow" })

if ($successfulTests -eq $totalTests) {
    Write-Host "🎉 ¡Todos los endpoints de diagnóstico funcionan correctamente!" -ForegroundColor Green
    Write-Host "✅ Las correcciones aplicadas han resuelto los problemas" -ForegroundColor Green
} else {
    Write-Host "⚠️ Algunos endpoints aún tienen problemas" -ForegroundColor Yellow
    Write-Host "🔍 Revisar logs del servidor para más detalles" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🚀 Próximos pasos:" -ForegroundColor Cyan
Write-Host "1. Probar login en el frontend" -ForegroundColor White
Write-Host "2. Verificar que el auto-refresh funcione" -ForegroundColor White
Write-Host "3. Monitorear logs para confirmar que no hay más errores 401" -ForegroundColor White
