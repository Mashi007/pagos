# ============================================================
# VERIFICACION COMPLETA POST-DEPLOYMENT
# Sistema con modelo Cliente corregido
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "VERIFICACION COMPLETA POST-DEPLOYMENT" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Paso 1: Verificar deployment
Write-Host "PASO 1: Verificando deployment..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/" -Method Get -TimeoutSec 10
    
    Write-Host "Respuesta del servidor:" -ForegroundColor Cyan
    Write-Host "  Message: $($response.message)" -ForegroundColor White
    Write-Host "  Timestamp: $($response.deploy_timestamp)" -ForegroundColor White
    Write-Host "  Real Data Ready: $($response.real_data_ready)" -ForegroundColor White
    Write-Host "  Status: $($response.status)" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host "ERROR: No se pudo conectar al servidor" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Paso 2: Obtener token
Write-Host "PASO 2: Obteniendo token de autenticacion..." -ForegroundColor Yellow
try {
    $loginBody = @{
        email = "itmaster@rapicreditca.com"
        password = "R@pi_2025**"
    } | ConvertTo-Json
    
    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/json" -TimeoutSec 15
    $token = $loginResponse.access_token
    Write-Host "OK: Token obtenido exitosamente" -ForegroundColor Green
    
    $authHeaders = @{
        "Authorization" = "Bearer $token"
    }
    
} catch {
    Write-Host "ERROR: No se pudo obtener token" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""

# Paso 3: Probar endpoints que tenian 503
Write-Host "PASO 3: Probando endpoints que tenian problemas 503..." -ForegroundColor Yellow
Write-Host ""

$endpointsToTest = @(
    @{name="Clientes (CRITICO)"; url="/api/v1/clientes/"; critical=$true},
    @{name="Pagos (CRITICO)"; url="/api/v1/pagos/"; critical=$true},
    @{name="Prestamos"; url="/api/v1/prestamos/"; critical=$false},
    @{name="Reportes Cartera (CRITICO)"; url="/api/v1/reportes/cartera"; critical=$true},
    @{name="Asesores"; url="/api/v1/asesores/"; critical=$false},
    @{name="Concesionarios"; url="/api/v1/concesionarios/"; critical=$false},
    @{name="Modelos Vehiculos"; url="/api/v1/modelos-vehiculos/"; critical=$false}
)

$successCount = 0
$totalTests = $endpointsToTest.Count
$criticalSuccess = 0
$criticalTotal = ($endpointsToTest | Where-Object { $_.critical }).Count

foreach ($endpoint in $endpointsToTest) {
    $priority = if ($endpoint.critical) { "[CRITICO]" } else { "[Normal]" }
    Write-Host "$priority Probando $($endpoint.name)..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl$($endpoint.url)" -Method Get -Headers $authHeaders -TimeoutSec 15
        
        $statusOk = $false
        $message = ""
        
        if ($response.total -ne $null) {
            $statusOk = $true
            $message = "$($response.total) registros"
        } elseif ($response.items -ne $null) {
            $statusOk = $true
            $message = "$($response.items.Count) registros"
        } elseif ($response.data -ne $null) {
            $statusOk = $true
            $message = "Data disponible"
        } else {
            $statusOk = $true
            $message = "Funcionando"
        }
        
        if ($statusOk) {
            Write-Host "  EXITO: $message" -ForegroundColor Green
            $successCount++
            if ($endpoint.critical) { $criticalSuccess++ }
        }
        
    } catch {
        $statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode.value__ } else { "N/A" }
        Write-Host "  FALLO: Status $statusCode" -ForegroundColor Red
        
        if ($endpoint.critical) {
            Write-Host "  ERROR CRITICO: Este endpoint es esencial para el sistema" -ForegroundColor Red
        }
    }
    
    Write-Host ""
}

# Paso 4: Resumen final
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RESUMEN FINAL" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$successRate = [math]::Round(($successCount / $totalTests) * 100, 2)
$criticalRate = if ($criticalTotal -gt 0) { [math]::Round(($criticalSuccess / $criticalTotal) * 100, 2) } else { 100 }

Write-Host "ENDPOINTS TOTALES:" -ForegroundColor White
Write-Host "  Total probados: $totalTests" -ForegroundColor White
Write-Host "  Funcionando: $successCount" -ForegroundColor $(if ($successCount -eq $totalTests) { "Green" } else { "Yellow" })
Write-Host "  Con problemas: $($totalTests - $successCount)" -ForegroundColor $(if ($successCount -eq $totalTests) { "Green" } else { "Red" })
Write-Host "  Tasa de exito: $successRate%" -ForegroundColor $(if ($successRate -eq 100) { "Green" } elseif ($successRate -ge 80) { "Yellow" } else { "Red" })
Write-Host ""

Write-Host "ENDPOINTS CRITICOS:" -ForegroundColor White
Write-Host "  Total criticos: $criticalTotal" -ForegroundColor White
Write-Host "  Funcionando: $criticalSuccess" -ForegroundColor $(if ($criticalSuccess -eq $criticalTotal) { "Green" } else { "Red" })
Write-Host "  Con problemas: $($criticalTotal - $criticalSuccess)" -ForegroundColor $(if ($criticalSuccess -eq $criticalTotal) { "Green" } else { "Red" })
Write-Host "  Tasa de exito: $criticalRate%" -ForegroundColor $(if ($criticalRate -eq 100) { "Green" } else { "Red" })
Write-Host ""

# Veredicto final
if ($criticalSuccess -eq $criticalTotal -and $successCount -eq $totalTests) {
    Write-Host "EXITO COMPLETO!" -ForegroundColor Green
    Write-Host "Todos los endpoints funcionando correctamente" -ForegroundColor Green
    Write-Host "El sistema esta 100% operativo" -ForegroundColor Green
    Write-Host ""
    Write-Host "PROXIMO PASO: Cargar datos reales" -ForegroundColor Cyan
    Write-Host "Ver guia en: SISTEMA_LISTO_DATOS_REALES.md" -ForegroundColor Cyan
} elseif ($criticalSuccess -eq $criticalTotal) {
    Write-Host "EXITO PARCIAL" -ForegroundColor Yellow
    Write-Host "Todos los endpoints criticos funcionando" -ForegroundColor Yellow
    Write-Host "Algunos endpoints secundarios tienen problemas" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "PROXIMO PASO: Cargar datos reales" -ForegroundColor Cyan
} else {
    Write-Host "PROBLEMA CRITICO" -ForegroundColor Red
    Write-Host "Algunos endpoints criticos NO funcionan" -ForegroundColor Red
    Write-Host "Se requiere revision adicional" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "FIN DE VERIFICACION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

