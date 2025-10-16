# ============================================================
# PASO 0: OBTENER TOKEN DE AUTENTICACION
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "OBTENER TOKEN DE AUTENTICACION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$loginBody = @{
    email = "itmaster@rapicreditca.com"
    password = "R@pi_2025**"
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

