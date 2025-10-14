# Script de pruebas automáticas para RapiCredit
# Verifica el estado completo del sistema

Write-Host "🚀 INICIANDO PRUEBAS DEL SISTEMA RAPICREDIT" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green

# 1. Verificar Backend
Write-Host "`n1. 🔍 Verificando Backend..." -ForegroundColor Yellow
try {
    $backendResponse = Invoke-WebRequest -Uri "https://pagos-f2qf.onrender.com/api/v1/health" -Method GET -UseBasicParsing -TimeoutSec 30
    Write-Host "✅ Backend: OK (HTTP Status: $($backendResponse.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "❌ Backend: ERROR - $($_.Exception.Message)" -ForegroundColor Red
}

# 2. Verificar Frontend
Write-Host "`n2. 🔍 Verificando Frontend..." -ForegroundColor Yellow
try {
    $frontendResponse = Invoke-WebRequest -Uri "https://rapicredit.onrender.com" -Method GET -UseBasicParsing -TimeoutSec 30
    Write-Host "✅ Frontend: OK (HTTP Status: $($frontendResponse.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "❌ Frontend: ERROR - $($_.Exception.Message)" -ForegroundColor Red
}

# 3. Verificar Endpoint de Login
Write-Host "`n3. 🔍 Verificando Endpoint de Login..." -ForegroundColor Yellow
try {
    $loginResponse = Invoke-WebRequest -Uri "https://pagos-f2qf.onrender.com/api/v1/auth/login" -Method POST -UseBasicParsing -TimeoutSec 30 -Body '{"email":"test","password":"test"}' -ContentType "application/json"
    # Esperamos un 422 (datos inválidos) o 401 (credenciales incorrectas), no un 500
    if ($loginResponse.StatusCode -eq 422 -or $loginResponse.StatusCode -eq 401) {
        Write-Host "✅ Login Endpoint: OK (HTTP Status: $($loginResponse.StatusCode) - Respuesta esperada)" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Login Endpoint: Status inesperado $($loginResponse.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    if ($_.Exception.Response.StatusCode -eq 422 -or $_.Exception.Response.StatusCode -eq 401) {
        Write-Host "✅ Login Endpoint: OK (HTTP Status: $($_.Exception.Response.StatusCode) - Respuesta esperada)" -ForegroundColor Green
    } else {
        Write-Host "❌ Login Endpoint: ERROR - $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 4. Verificar Endpoint de Clientes (sin token - debe dar 401)
Write-Host "`n4. 🔍 Verificando Endpoint de Clientes..." -ForegroundColor Yellow
try {
    $clientesResponse = Invoke-WebRequest -Uri "https://pagos-f2qf.onrender.com/api/v1/clientes?page=1&per_page=10" -Method GET -UseBasicParsing -TimeoutSec 30
    Write-Host "⚠️ Clientes Endpoint: Status inesperado $($clientesResponse.StatusCode)" -ForegroundColor Yellow
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "✅ Clientes Endpoint: OK (HTTP Status: 401 - Autenticación requerida)" -ForegroundColor Green
    } else {
        Write-Host "❌ Clientes Endpoint: ERROR - $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 5. Verificar Endpoint de Dashboard (sin token - debe dar 401)
Write-Host "`n5. 🔍 Verificando Endpoint de Dashboard..." -ForegroundColor Yellow
try {
    $dashboardResponse = Invoke-WebRequest -Uri "https://pagos-f2qf.onrender.com/api/v1/dashboard/admin" -Method GET -UseBasicParsing -TimeoutSec 30
    Write-Host "⚠️ Dashboard Endpoint: Status inesperado $($dashboardResponse.StatusCode)" -ForegroundColor Yellow
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "✅ Dashboard Endpoint: OK (HTTP Status: 401 - Autenticación requerida)" -ForegroundColor Green
    } else {
        Write-Host "❌ Dashboard Endpoint: ERROR - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n🎊 PRUEBAS COMPLETADAS" -ForegroundColor Green
Write-Host "====================" -ForegroundColor Green
Write-Host "`n📋 INSTRUCCIONES PARA PRUEBAS MANUALES:" -ForegroundColor Cyan
Write-Host "1. Ve a: https://rapicredit.onrender.com/login" -ForegroundColor White
Write-Host "2. Usa credenciales de prueba (si las tienes)" -ForegroundColor White
Write-Host "3. Verifica que el checkbox 'Recordarme' esté marcado" -ForegroundColor White
Write-Host "4. Haz login y ve a /clientes" -ForegroundColor White
Write-Host "5. Refresca la página - NO debe redirigir al login" -ForegroundColor White
Write-Host "6. Verifica que los clientes se carguen correctamente" -ForegroundColor White
