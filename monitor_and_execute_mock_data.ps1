# ============================================================
# MONITOR DE DEPLOYMENT Y EJECUCION DE MOCK DATA
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "MONITOR DE DEPLOYMENT Y EJECUCION DE MOCK DATA" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Función para verificar si el deployment está listo
function Test-DeploymentReady {
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/" -Method Get -TimeoutSec 10
        if ($response.deploy_timestamp) {
            Write-Host "Deployment detectado con timestamp: $($response.deploy_timestamp)" -ForegroundColor Green
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

# Función para obtener token
function Get-AuthToken {
    try {
        $loginBody = @{
            email = "itmaster@rapicreditca.com"
            password = "R@pi_2025**"
        } | ConvertTo-Json
        
        $loginResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/json" -TimeoutSec 15
        return $loginResponse.access_token
    } catch {
        Write-Host "ERROR: No se pudo obtener token" -ForegroundColor Red
        return $null
    }
}

# Función para ejecutar mock data
function Invoke-MockDataCreation {
    param($token)
    
    $authHeaders = @{
        "Authorization" = "Bearer $token"
    }
    
    try {
        Write-Host "Ejecutando creacion de mock data..." -ForegroundColor Yellow
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
        
        return $true
    } catch {
        Write-Host "ERROR: No se pudo crear mock data" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        return $false
    }
}

# Función para probar endpoints
function Test-Endpoints {
    param($token)
    
    $authHeaders = @{
        "Authorization" = "Bearer $token"
    }
    
    $endpointsToTest = @(
        @{name="Clientes"; url="/api/v1/clientes/"},
        @{name="Pagos"; url="/api/v1/pagos/"},
        @{name="Prestamos"; url="/api/v1/prestamos/"},
        @{name="Reportes Cartera"; url="/api/v1/reportes/cartera"}
    )
    
    $successCount = 0
    $totalTests = $endpointsToTest.Count
    
    Write-Host "Probando endpoints que tenian problemas 503..." -ForegroundColor Yellow
    
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
    
    return $successCount, $totalTests
}

# ============================================================
# PROCESO PRINCIPAL
# ============================================================

Write-Host "Esperando deployment..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $attempt++
    Write-Host "Intento $attempt/$maxAttempts..." -ForegroundColor Gray
    
    if (Test-DeploymentReady) {
        Write-Host "Deployment detectado!" -ForegroundColor Green
        break
    }
    
    Write-Host "Esperando 10 segundos..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
}

if ($attempt -eq $maxAttempts) {
    Write-Host "TIMEOUT: Deployment no detectado en tiempo esperado" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Obtener token
Write-Host "Obteniendo token de autenticacion..." -ForegroundColor Yellow
$token = Get-AuthToken

if (-not $token) {
    Write-Host "ERROR: No se pudo obtener token" -ForegroundColor Red
    exit 1
}

Write-Host "OK: Token obtenido" -ForegroundColor Green
Write-Host ""

# Ejecutar mock data
$mockSuccess = Invoke-MockDataCreation -token $token

if (-not $mockSuccess) {
    Write-Host "ERROR: No se pudo crear mock data" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Probar endpoints
$successCount, $totalTests = Test-Endpoints -token $token

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
Write-Host "FIN DEL PROCESO" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

