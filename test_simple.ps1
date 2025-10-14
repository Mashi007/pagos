Write-Host "=== PRUEBAS RAPICREDIT ===" -ForegroundColor Green

# Backend
try {
    $response = Invoke-WebRequest -Uri "https://pagos-f2qf.onrender.com/api/v1/health" -UseBasicParsing -TimeoutSec 10
    Write-Host "Backend: OK ($($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "Backend: ERROR" -ForegroundColor Red
}

# Frontend
try {
    $response = Invoke-WebRequest -Uri "https://rapicredit.onrender.com" -UseBasicParsing -TimeoutSec 10
    Write-Host "Frontend: OK ($($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "Frontend: ERROR" -ForegroundColor Red
}

# Clientes (sin token)
try {
    $response = Invoke-WebRequest -Uri "https://pagos-f2qf.onrender.com/api/v1/clientes" -UseBasicParsing -TimeoutSec 10
    Write-Host "Clientes: Status $($response.StatusCode)" -ForegroundColor Yellow
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "Clientes: OK (401 - Auth requerida)" -ForegroundColor Green
    } elseif ($_.Exception.Response.StatusCode -eq 403) {
        Write-Host "Clientes: OK (403 - Auth requerida)" -ForegroundColor Green
    } else {
        Write-Host "Clientes: ERROR" -ForegroundColor Red
    }
}

Write-Host "=== PRUEBAS COMPLETADAS ===" -ForegroundColor Green
