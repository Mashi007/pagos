# Test de login directo
try {
    Write-Host "Probando login directo..." -ForegroundColor Yellow
    
    $loginBody = @{
        email = "itmaster@rapicreditca.com"
        password = "R@pi_2025**"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "https://pagos-f2qf.onrender.com/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/json" -TimeoutSec 15
    
    Write-Host "✅ LOGIN EXITOSO!" -ForegroundColor Green
    Write-Host "Usuario autenticado correctamente"
    Write-Host "Token recibido: $($response.access_token.Substring(0,20))..."
    
} catch {
    Write-Host "❌ Error en login:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode
        Write-Host "Status Code: $statusCode"
        
        if ($statusCode -eq 401) {
            Write-Host "⚠️ Credenciales incorrectas o usuario no existe" -ForegroundColor Yellow
        } elseif ($statusCode -eq 503) {
            Write-Host "⚠️ Servicio no disponible - problema de DB" -ForegroundColor Yellow
        }
    }
}

