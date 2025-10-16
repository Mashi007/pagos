# ============================================================
# DIAGNOSTICO DETALLADO DEL ENDPOINT CLIENTES
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "DIAGNOSTICO DETALLADO ENDPOINT CLIENTES" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Obtener token
Write-Host "1. Obteniendo token..." -ForegroundColor Yellow
$loginBody = '{"email":"itmaster@rapicreditca.com","password":"R@pi_2025**"}'
try {
    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
    $token = $loginResponse.access_token
    Write-Host "   OK: Token obtenido" -ForegroundColor Green
} catch {
    Write-Host "   ERROR: No se pudo obtener token" -ForegroundColor Red
    exit 1
}

$authHeaders = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

Write-Host ""

# Verificar endpoint GET
Write-Host "2. Verificando endpoint GET clientes..." -ForegroundColor Yellow
try {
    $clientes = Invoke-RestMethod -Uri "$baseUrl/api/v1/clientes/" -Method Get -Headers $authHeaders
    Write-Host "   OK: GET funciona - Total: $($clientes.total)" -ForegroundColor Green
} catch {
    Write-Host "   ERROR: GET falla" -ForegroundColor Red
    Write-Host "   Detalle: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Verificar endpoint POST con datos mínimos
Write-Host "3. Probando POST con datos mínimos..." -ForegroundColor Yellow
$clienteMinimo = @{
    cedula = "999-9999999-9"
    nombres = "Test"
    apellidos = "Minimo"
    asesor_config_id = 1
    estado = "ACTIVO"
    activo = $true
} | ConvertTo-Json

Write-Host "   Datos enviados:" -ForegroundColor Gray
Write-Host "   $clienteMinimo" -ForegroundColor Gray
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/clientes" -Method Post -Headers $authHeaders -Body $clienteMinimo
    Write-Host "   EXITO: Cliente creado con ID $($response.id)" -ForegroundColor Green
} catch {
    Write-Host "   ERROR: POST falla" -ForegroundColor Red
    Write-Host "   Detalle: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "   Status Code: $statusCode" -ForegroundColor Red
        
        # Intentar obtener más detalles del error
        try {
            $errorStream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($errorStream)
            $errorBody = $reader.ReadToEnd()
            Write-Host "   Error Body: $errorBody" -ForegroundColor Red
        } catch {
            Write-Host "   No se pudo obtener detalles adicionales" -ForegroundColor Yellow
        }
    }
}

Write-Host ""

# Verificar si el problema es con el asesor
Write-Host "4. Verificando que el asesor existe..." -ForegroundColor Yellow
try {
    $asesores = Invoke-RestMethod -Uri "$baseUrl/api/v1/asesores/" -Method Get -Headers $authHeaders
    Write-Host "   OK: Asesores disponibles: $($asesores.total)" -ForegroundColor Green
    if ($asesores.total -gt 0) {
        Write-Host "   Primer asesor ID: $($asesores.items[0].id)" -ForegroundColor Green
    }
} catch {
    Write-Host "   ERROR: No se pueden obtener asesores" -ForegroundColor Red
}

Write-Host ""

# Verificar documentación de la API
Write-Host "5. Verificando documentación de la API..." -ForegroundColor Yellow
try {
    $docs = Invoke-RestMethod -Uri "$baseUrl/docs" -Method Get
    Write-Host "   OK: Documentación disponible" -ForegroundColor Green
    Write-Host "   URL: $baseUrl/docs" -ForegroundColor Cyan
} catch {
    Write-Host "   ADVERTENCIA: No se puede acceder a la documentación" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "FIN DEL DIAGNOSTICO" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

