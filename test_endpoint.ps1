# Test simple del endpoint raíz
try {
    $response = Invoke-RestMethod -Uri "https://pagos-f2qf.onrender.com/" -Method Get -TimeoutSec 10
    Write-Host "✅ App responde:" -ForegroundColor Green
    $response | ConvertTo-Json | Write-Host
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}

