# ============================================================
# VERIFICACION CON RUTAS CORRECTAS
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "VERIFICACION CON RUTAS CORRECTAS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Obtener token de autenticacion
Write-Host "Obteniendo token de autenticacion..." -ForegroundColor Yellow
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

# Verificar endpoints con rutas CORRECTAS
$endpointsCorrectos = @(
    @{name="Auth/Me"; url="/api/v1/auth/me"},
    @{name="Clientes"; url="/api/v1/clientes/"},
    @{name="Pagos"; url="/api/v1/pagos/"},
    @{name="Reportes Cartera"; url="/api/v1/reportes/cartera"}
)

Write-Host "Verificando endpoints con rutas CORRECTAS..." -ForegroundColor Yellow
Write-Host ""

$totalTests = 0
$passedTests = 0
$failedTests = 0

foreach ($endpoint in $endpointsCorrectos) {
    $totalTests++
    Write-Host "[$totalTests] $($endpoint.name)" -ForegroundColor Cyan
    Write-Host "    URL: $($endpoint.url)" -ForegroundColor Gray
    
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl$($endpoint.url)" -Method Get -Headers $authHeaders -TimeoutSec 15
        Write-Host "    OK: Endpoint funcionando" -ForegroundColor Green
        
        # Mostrar informacion adicional segun el endpoint
        if ($endpoint.name -eq "Auth/Me") {
            Write-Host "    Email: $($response.email)" -ForegroundColor Gray
            Write-Host "    Rol: $($response.rol)" -ForegroundColor Gray
            Write-Host "    Nombre: $($response.nombre) $($response.apellido)" -ForegroundColor Gray
        } elseif ($endpoint.name -eq "Clientes") {
            Write-Host "    Total clientes: $($response.total)" -ForegroundColor Gray
        } elseif ($endpoint.name -eq "Pagos") {
            Write-Host "    Pagos obtenidos correctamente" -ForegroundColor Gray
        } elseif ($endpoint.name -eq "Reportes Cartera") {
            Write-Host "    Reporte generado correctamente" -ForegroundColor Gray
        }
        
        $passedTests++
        
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "    ERROR: Status $statusCode" -ForegroundColor Red
        Write-Host "    Mensaje: $($_.Exception.Message)" -ForegroundColor Red
        $failedTests++
    }
    
    Write-Host ""
}

# Resumen
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RESUMEN DE VERIFICACION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$successRate = [math]::Round(($passedTests / $totalTests) * 100, 2)

Write-Host "Total endpoints verificados: $totalTests" -ForegroundColor White
Write-Host "Endpoints funcionando: $passedTests" -ForegroundColor Green
Write-Host "Endpoints con problemas: $failedTests" -ForegroundColor Red
Write-Host "Tasa de exito: $successRate%" -ForegroundColor $(if ($successRate -eq 100) { "Green" } elseif ($successRate -ge 75) { "Yellow" } else { "Red" })
Write-Host ""

if ($failedTests -eq 0) {
    Write-Host "EXITO: TODOS LOS ENDPOINTS FUNCIONAN!" -ForegroundColor Green
    Write-Host "El deployment fue completamente exitoso" -ForegroundColor Green
} elseif ($successRate -ge 75) {
    Write-Host "MEJORA: La mayoria de endpoints funcionan" -ForegroundColor Yellow
    Write-Host "Algunos endpoints pueden necesitar mas tiempo" -ForegroundColor Yellow
} else {
    Write-Host "PROBLEMA: Los endpoints siguen con errores" -ForegroundColor Red
    Write-Host "Revisar logs del deployment" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "FIN DE VERIFICACION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

