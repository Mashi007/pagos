Write-Host "=== PRUEBA LOGIN RAPICREDIT ===" -ForegroundColor Green

# Crear usuario
Write-Host "1. Creando usuario..." -ForegroundColor Yellow
try {
    $createResponse = Invoke-RestMethod -Uri "https://pagos-f2qf.onrender.com/api/v1/auth/create-test-user" -Method POST -ContentType "application/json" -TimeoutSec 15
    Write-Host "Usuario creado: $($createResponse.credentials.email)" -ForegroundColor Green
} catch {
    Write-Host "Error creando usuario: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Probar login
Write-Host "2. Probando login..." -ForegroundColor Yellow
try {
    $loginData = @{
        email = "admin@rapicredit.com"
        password = "admin123"
        remember = $true
    } | ConvertTo-Json

    $loginResponse = Invoke-RestMethod -Uri "https://pagos-f2qf.onrender.com/api/v1/auth/login" -Method POST -Body $loginData -ContentType "application/json" -TimeoutSec 15
    
    Write-Host "Login exitoso!" -ForegroundColor Green
    Write-Host "Usuario: $($loginResponse.user.nombre)" -ForegroundColor Cyan
    Write-Host "Rol: $($loginResponse.user.rol)" -ForegroundColor Cyan
    
} catch {
    Write-Host "Error en login: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "=== PRUEBA COMPLETADA ===" -ForegroundColor Green
Write-Host "Credenciales: admin@rapicredit.com / admin123" -ForegroundColor White
