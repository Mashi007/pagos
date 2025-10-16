# Verificar si el nuevo deployment esta activo
$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "Verificando deployment..." -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/" -Method Get -TimeoutSec 10
    
    Write-Host "Respuesta del servidor:" -ForegroundColor Cyan
    Write-Host "  Message: $($response.message)" -ForegroundColor White
    Write-Host "  Timestamp: $($response.deploy_timestamp)" -ForegroundColor White
    Write-Host "  Real Data Ready: $($response.real_data_ready)" -ForegroundColor White
    Write-Host ""
    
    if ($response.deploy_timestamp -eq "2025-10-16T10:30:00Z") {
        Write-Host "DEPLOYMENT NUEVO DETECTADO!" -ForegroundColor Green
        Write-Host "El sistema esta actualizado con los ultimos cambios" -ForegroundColor Green
    } else {
        Write-Host "Deployment anterior detectado: $($response.deploy_timestamp)" -ForegroundColor Yellow
        Write-Host "Esperando nuevo deployment..." -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "ERROR: No se pudo conectar al servidor" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

