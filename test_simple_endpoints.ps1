# ============================================================
# TEST SIMPLE DE ENDPOINTS PROBLEMATICOS
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "TEST SIMPLE DE ENDPOINTS PROBLEMATICOS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Obtener token
Write-Host "Obteniendo token..." -ForegroundColor Yellow
try {
    $loginBody = @{
        email = "itmaster@rapicreditca.com"
        password = "R@pi_2025**"
    } | ConvertTo-Json
    
    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/json" -TimeoutSec 15
    $token = $loginResponse.access_token
    Write-Host "OK: Token obtenido" -ForegroundColor Green
    
    $authHeaders = @{
        "Authorization" = "Bearer $token"
    }
    
} catch {
    Write-Host "ERROR: No se pudo obtener token" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test con parametros minimos para evitar queries complejas
Write-Host "Probando endpoints con parametros minimos..." -ForegroundColor Yellow
Write-Host ""

# Test 1: Clientes con paginacion minima
Write-Host "[1] Clientes - Pagina 1, 5 elementos" -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/clientes/?page=1&per_page=5" -Method Get -Headers $authHeaders -TimeoutSec 20
    Write-Host "    OK: Clientes obtenidos" -ForegroundColor Green
    Write-Host "    Total: $($response.total)" -ForegroundColor Gray
    Write-Host "    Elementos en pagina: $($response.items.Count)" -ForegroundColor Gray
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "    ERROR: Status $statusCode" -ForegroundColor Red
    Write-Host "    Mensaje: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 2: Pagos con paginacion minima
Write-Host "[2] Pagos - Pagina 1, 5 elementos" -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/pagos/?page=1&per_page=5" -Method Get -Headers $authHeaders -TimeoutSec 20
    Write-Host "    OK: Pagos obtenidos" -ForegroundColor Green
    Write-Host "    Total: $($response.total)" -ForegroundColor Gray
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "    ERROR: Status $statusCode" -ForegroundColor Red
    Write-Host "    Mensaje: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 3: Reportes con parametros simples
Write-Host "[3] Reportes - Cartera basica" -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/reportes/cartera" -Method Get -Headers $authHeaders -TimeoutSec 20
    Write-Host "    OK: Reporte obtenido" -ForegroundColor Green
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "    ERROR: Status $statusCode" -ForegroundColor Red
    Write-Host "    Mensaje: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 4: Verificar si hay datos en la base de datos
Write-Host "[4] Verificando datos basicos..." -ForegroundColor Cyan

# Test de usuarios (que sabemos que funciona)
try {
    $usersResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/users/" -Method Get -Headers $authHeaders -TimeoutSec 10
    Write-Host "    Usuarios: $($usersResponse.total)" -ForegroundColor Gray
} catch {
    Write-Host "    ERROR en usuarios" -ForegroundColor Red
}

# Test de prestamos (que sabemos que funciona)
try {
    $prestamosResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/prestamos/" -Method Get -Headers $authHeaders -TimeoutSec 10
    Write-Host "    Prestamos: $($prestamosResponse.total)" -ForegroundColor Gray
} catch {
    Write-Host "    ERROR en prestamos" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "FIN DEL TEST SIMPLE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

