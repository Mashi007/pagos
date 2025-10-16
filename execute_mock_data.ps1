# ============================================================
# EJECUTAR MOCK DATA EN PRODUCCION
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "EJECUTANDO MOCK DATA EN PRODUCCION" -ForegroundColor Cyan
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
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""

# Verificar estado actual antes de crear mock data
Write-Host "Verificando estado actual de datos..." -ForegroundColor Yellow
try {
    $statusResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/mock/check-data-status" -Method Get -Headers $authHeaders -TimeoutSec 15
    
    Write-Host "Estado actual:" -ForegroundColor Cyan
    Write-Host "  Status: $($statusResponse.status)" -ForegroundColor Gray
    Write-Host "  Tablas con datos: $($statusResponse.tables_with_data)/$($statusResponse.total_tables)" -ForegroundColor Gray
    Write-Host "  Porcentaje de completitud: $($statusResponse.completion_percentage)%" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "Conteos actuales:" -ForegroundColor Cyan
    foreach ($table in $statusResponse.counts.PSObject.Properties) {
        Write-Host "  $($table.Name): $($table.Value)" -ForegroundColor Gray
    }
    
} catch {
    Write-Host "ADVERTENCIA: No se pudo verificar estado actual" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Yellow
}

Write-Host ""

# Ejecutar creacion de mock data
Write-Host "Ejecutando creacion de mock data..." -ForegroundColor Yellow
try {
    $mockResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/mock/create-mock-data" -Method Post -Headers $authHeaders -TimeoutSec 30
    
    Write-Host "EXITO: Mock data creado exitosamente!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Detalles:" -ForegroundColor Cyan
    Write-Host "  Asesores: $($mockResponse.details.asesores)" -ForegroundColor Gray
    Write-Host "  Concesionarios: $($mockResponse.details.concesionarios)" -ForegroundColor Gray
    Write-Host "  Modelos de vehiculos: $($mockResponse.details.modelos_vehiculos)" -ForegroundColor Gray
    Write-Host "  Clientes: $($mockResponse.details.clientes)" -ForegroundColor Gray
    Write-Host "  Prestamos: $($mockResponse.details.prestamos)" -ForegroundColor Gray
    Write-Host "  Pagos: $($mockResponse.details.pagos)" -ForegroundColor Gray
    
} catch {
    Write-Host "ERROR: No se pudo crear mock data" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "Status Code: $statusCode" -ForegroundColor Red
    }
    exit 1
}

Write-Host ""

# Verificar estado despues de crear mock data
Write-Host "Verificando estado despues de crear mock data..." -ForegroundColor Yellow
try {
    $statusResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/mock/check-data-status" -Method Get -Headers $authHeaders -TimeoutSec 15
    
    Write-Host "Estado final:" -ForegroundColor Cyan
    Write-Host "  Status: $($statusResponse.status)" -ForegroundColor $(if ($statusResponse.status -eq "COMPLETO") { "Green" } else { "Yellow" })
    Write-Host "  Tablas con datos: $($statusResponse.tables_with_data)/$($statusResponse.total_tables)" -ForegroundColor Gray
    Write-Host "  Porcentaje de completitud: $($statusResponse.completion_percentage)%" -ForegroundColor $(if ($statusResponse.completion_percentage -eq 100) { "Green" } else { "Yellow" })
    Write-Host ""
    
    Write-Host "Conteos finales:" -ForegroundColor Cyan
    foreach ($table in $statusResponse.counts.PSObject.Properties) {
        $color = if ($table.Value -gt 0) { "Green" } else { "Red" }
        Write-Host "  $($table.Name): $($table.Value)" -ForegroundColor $color
    }
    
} catch {
    Write-Host "ADVERTENCIA: No se pudo verificar estado final" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Yellow
}

Write-Host ""

# Probar endpoints que tenian problemas 503
Write-Host "Probando endpoints que tenian problemas 503..." -ForegroundColor Yellow

$endpointsToTest = @(
    @{name="Clientes"; url="/api/v1/clientes/"},
    @{name="Pagos"; url="/api/v1/pagos/"},
    @{name="Prestamos"; url="/api/v1/prestamos/"},
    @{name="Reportes Cartera"; url="/api/v1/reportes/cartera"}
)

$successCount = 0
$totalTests = $endpointsToTest.Count

foreach ($endpoint in $endpointsToTest) {
    Write-Host "Probando $($endpoint.name)..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl$($endpoint.url)" -Method Get -Headers $authHeaders -TimeoutSec 15
        
        if ($response.total -and $response.total -gt 0) {
            Write-Host "  OK: $($response.total) registros" -ForegroundColor Green
            $successCount++
        } elseif ($response.items -and $response.items.Count -gt 0) {
            Write-Host "  OK: $($response.items.Count) registros" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "  OK: Endpoint funcionando" -ForegroundColor Green
            $successCount++
        }
        
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "  ERROR: Status $statusCode" -ForegroundColor Red
        Write-Host "  Mensaje: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
}

# Resumen final
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RESUMEN FINAL" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$successRate = [math]::Round(($successCount / $totalTests) * 100, 2)

Write-Host "Endpoints probados: $totalTests" -ForegroundColor White
Write-Host "Endpoints funcionando: $successCount" -ForegroundColor Green
Write-Host "Endpoints con problemas: $($totalTests - $successCount)" -ForegroundColor Red
Write-Host "Tasa de exito: $successRate%" -ForegroundColor $(if ($successRate -eq 100) { "Green" } elseif ($successRate -ge 75) { "Yellow" } else { "Red" })
Write-Host ""

if ($successCount -eq $totalTests) {
    Write-Host "EXITO: TODOS LOS ENDPOINTS 503 CORREGIDOS!" -ForegroundColor Green
    Write-Host "El sistema esta completamente funcional" -ForegroundColor Green
} elseif ($successRate -ge 75) {
    Write-Host "MEJORA: La mayoria de endpoints funcionan" -ForegroundColor Yellow
    Write-Host "Algunos endpoints pueden necesitar mas tiempo" -ForegroundColor Yellow
} else {
    Write-Host "PROBLEMA: Los endpoints siguen con errores" -ForegroundColor Red
    Write-Host "Revisar logs del sistema" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "FIN DE EJECUCION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

