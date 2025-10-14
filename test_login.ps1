# Script para probar login y crear usuario
Write-Host "=== PRUEBA DE LOGIN RAPICREDIT ===" -ForegroundColor Green

# 1. Crear usuario de prueba
Write-Host "1. Creando usuario de prueba..." -ForegroundColor Yellow
try {
    $createResponse = Invoke-RestMethod -Uri "https://pagos-f2qf.onrender.com/api/v1/auth/create-test-user" -Method POST -ContentType "application/json" -TimeoutSec 15
    Write-Host "   ✅ Usuario creado exitosamente" -ForegroundColor Green
    Write-Host "   📧 Email: $($createResponse.credentials.email)" -ForegroundColor Cyan
    Write-Host "   🔑 Password: $($createResponse.credentials.password)" -ForegroundColor Cyan
} catch {
    Write-Host "   ❌ Error creando usuario: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 2. Probar login
Write-Host "`n2. Probando login..." -ForegroundColor Yellow
try {
    $loginData = @{
        email = "admin@rapicredit.com"
        password = "admin123"
        remember = $true
    } | ConvertTo-Json

    $loginResponse = Invoke-RestMethod -Uri "https://pagos-f2qf.onrender.com/api/v1/auth/login" -Method POST -Body $loginData -ContentType "application/json" -TimeoutSec 15
    
    Write-Host "   ✅ Login exitoso!" -ForegroundColor Green
    Write-Host "   🔑 Token recibido: $($loginResponse.access_token.Substring(0,20))..." -ForegroundColor Cyan
    Write-Host "   👤 Usuario: $($loginResponse.user.nombre)" -ForegroundColor Cyan
    Write-Host "   🎯 Rol: $($loginResponse.user.rol)" -ForegroundColor Cyan
    
} catch {
    Write-Host "   ❌ Error en login: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "   💡 Credenciales incorrectas - verificar usuario en BD" -ForegroundColor Yellow
    }
    exit 1
}

# 3. Probar endpoint protegido
Write-Host "`n3. Probando endpoint protegido..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $($loginResponse.access_token)"
        "Accept" = "application/json"
    }
    
    $protectedResponse = Invoke-RestMethod -Uri "https://pagos-f2qf.onrender.com/api/v1/clientes?page=1&per_page=5" -Method GET -Headers $headers -TimeoutSec 15
    
    Write-Host "   ✅ Endpoint protegido funciona!" -ForegroundColor Green
    Write-Host "   📊 Datos recibidos correctamente" -ForegroundColor Cyan
    
} catch {
    Write-Host "   ❌ Error en endpoint protegido: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== PRUEBA COMPLETADA EXITOSAMENTE ===" -ForegroundColor Green
Write-Host "🎯 Credenciales funcionando:" -ForegroundColor Cyan
Write-Host "   📧 Email: admin@rapicredit.com" -ForegroundColor White
Write-Host "   🔑 Password: admin123" -ForegroundColor White
Write-Host "`n🚀 Puedes usar estas credenciales en la aplicación web" -ForegroundColor Green
