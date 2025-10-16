# Test del endpoint de migración
try {
    Write-Host "Probando endpoint de migración..." -ForegroundColor Yellow
    $response = Invoke-RestMethod -Uri "https://pagos-f2qf.onrender.com/api/v1/emergency/check-roles" -Method Get -TimeoutSec 15
    Write-Host "✅ Endpoint responde correctamente" -ForegroundColor Green
    Write-Host "Respuesta:"
    $response | ConvertTo-Json -Depth 3
} catch {
    Write-Host "❌ Error:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host ""
    Write-Host "Probando endpoint raíz..." -ForegroundColor Yellow
    try {
        $root = Invoke-RestMethod -Uri "https://pagos-f2qf.onrender.com/" -Method Get -TimeoutSec 10
        Write-Host "✅ App responde en endpoint raíz" -ForegroundColor Green
        $root | ConvertTo-Json
    } catch {
        Write-Host "❌ App no responde" -ForegroundColor Red
        Write-Host $_.Exception.Message
    }
}

