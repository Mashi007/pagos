# ============================================================
# PASO 0: OBTENER TOKEN DE AUTENTICACION
# ============================================================

# ============================================================
# CONFIGURACION - Cambiar estas variables según tu entorno
# ============================================================
$baseUrl = $env:API_BASE_URL
if (-not $baseUrl) {
    $baseUrl = "https://pagos-f2qf.onrender.com"
}

$adminEmail = $env:ADMIN_EMAIL
if (-not $adminEmail) {
    $adminEmail = "itmaster@rapicreditca.com"
}

$adminPassword = $env:ADMIN_PASSWORD
if (-not $adminPassword) {
    Write-Host "ERROR: Variable ADMIN_PASSWORD no configurada" -ForegroundColor Red
    Write-Host "Configura la variable de entorno o ingresa la contraseña:" -ForegroundColor Yellow
    $adminPassword = Read-Host "Contraseña del administrador" -AsSecureString
    $adminPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminPassword))
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "OBTENER TOKEN DE AUTENTICACION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$loginBody = @{
    email = $adminEmail
    password = $adminPassword
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/json" -TimeoutSec 15
    $token = $loginResponse.access_token
    
    Write-Host "TOKEN OBTENIDO EXITOSAMENTE!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Tu token de autenticacion es:" -ForegroundColor Yellow
    Write-Host $token -ForegroundColor White
    Write-Host ""
    Write-Host "IMPORTANTE: Copia este token para usarlo en los siguientes pasos" -ForegroundColor Cyan
    Write-Host ""
    
    # Guardar token en variable de entorno para los siguientes scripts
    $env:AUTH_TOKEN = $token
    Write-Host "Token guardado en variable de entorno: `$env:AUTH_TOKEN" -ForegroundColor Green
    
} catch {
    Write-Host "ERROR: No se pudo obtener token" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

